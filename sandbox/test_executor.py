"""Unit: python -m unittest modules.bi_analysis_modern.sandbox.test_executor.

Реальный Docker: дополнительно BI_PYTHON_INTEGRATION=1 и запущенный manage.py up.
"""
import io
import os
from pathlib import Path
import subprocess
import threading
import time
import unittest
import uuid
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

import polars as pl

from .broker import ExecutorServer
from .protocol import MAX_DATA, LimitedBuffer, pack, unpack
from .runtime import DockerExecutor


class ProtocolTests(unittest.TestCase):
    def test_protocol_rejects_truncated_header(self):
        with self.assertRaises(ValueError):
            unpack(b'\x00\x00\x00\x10{}')

    def test_serialization_stops_at_the_size_limit(self):
        buffer = LimitedBuffer()
        buffer.seek(MAX_DATA)
        with self.assertRaises(ValueError):
            buffer.write(b'x')

    def test_runtime_does_not_mount_project_or_forward_secrets(self):
        args = DockerExecutor().create_arguments('test')
        for required in ('--network=none', '--read-only', '--cap-drop=ALL',
                         '--security-opt=no-new-privileges', '--pids-limit=32',
                         '--memory=536870912', '--memory-swap=536870912', '--log-driver=none'):
            self.assertIn(required, args)
        self.assertFalse(any(arg.startswith(('--mount', '--volume', '--env', '--privileged')) for arg in args))


class BrokerTests(unittest.TestCase):
    def setUp(self):
        class NeverExecute:
            def execute(self, payload):
                raise AssertionError('Unauthenticated/oversized requests must not reach Docker')
        self.server = ExecutorServer(('127.0.0.1', 0), NeverExecute(), 'x' * 40)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.server.server_port) + '/execute'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_missing_token_is_rejected_before_reading_code(self):
        with self.assertRaises(HTTPError) as error:
            build_opener(ProxyHandler({})).open(Request(self.url, data=b'{}'), timeout=2)
        self.assertEqual(error.exception.code, 401)
        error.exception.close()

    def test_exhausted_slots_return_busy(self):
        self.server.slots.acquire()
        self.server.slots.acquire()
        try:
            with self.assertRaises(HTTPError) as error:
                build_opener(ProxyHandler({})).open(Request(self.url, data=b'{}',
                    headers={'Authorization': 'Bearer ' + 'x' * 40}), timeout=2)
            self.assertEqual(error.exception.code, 503)
            error.exception.close()
        finally:
            self.server.slots.release()
            self.server.slots.release()


@unittest.skipUnless(os.environ.get('BI_PYTHON_INTEGRATION') == '1', 'Docker integration disabled')
class DockerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = Path(__file__).resolve().parents[3] / 'env' / 'bi-python.env'
        values = dict(line.split('=', 1) for line in config.read_text().splitlines() if '=' in line)
        cls.url = values['BI_PYTHON_EXECUTOR_URL'] + '/execute'
        cls.token = values['BI_PYTHON_EXECUTOR_TOKEN']

    def execute(self, code, frame=None, mode='polars'):
        frame = pl.DataFrame({'x': [1, 2]}) if frame is None else frame
        buffer = io.BytesIO()
        frame.write_ipc(buffer)
        request = Request(self.url, data=pack({'code': code, 'mode': mode}, buffer.getvalue()),
                          headers={'Authorization': 'Bearer ' + self.token})
        opener = build_opener(ProxyHandler({}))
        try:
            response = opener.open(request, timeout=40)
        except HTTPError as exc:
            response = exc
        with response:
            header, data = unpack(response.read())
        if header.get('ok') is not True:
            raise ValueError(header.get('error', 'no error'))
        return pl.read_ipc(io.BytesIO(data), memory_map=False)

    def test_polars_and_rows_and_schema(self):
        from datetime import date
        frame = pl.DataFrame({'date': [date(2026, 10, 30)], 'x': [2]}, schema={'date': pl.Date, 'x': pl.Int32})
        actual = self.execute('result = df.with_columns((pl.col("x") * 3).alias("x"))', frame)
        self.assertEqual(actual.schema, frame.schema)
        self.assertEqual(actual['x'].to_list(), [6])
        self.assertEqual(self.execute('factor = 3\nresult = [{"x": r["x"] * factor} for r in rows]', mode='rows')['x'].to_list(), [3, 6])

    def test_memory_bomb_is_killed_and_service_recovers(self):
        with self.assertRaises(ValueError):
            self.execute('result = ["x" * 1024 * 1024 * 1024]')
        self.assertEqual(self.execute('result = df.head(1)').height, 1)

    def test_infinite_loop_is_killed_and_service_recovers(self):
        started = time.monotonic()
        with self.assertRaises(ValueError):
            # CPU hard limit stops this before the wall deadline.
            self.execute('while True: pass')
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(self.execute('result = df.head(1)').height, 1)

    def test_host_file_access_is_denied(self):
        with self.assertRaises(ValueError):
            self.execute('result = pl.read_csv("/app/.env")')
        with self.assertRaises(ValueError):
            self.execute('df.write_csv("/worker/leak.csv")')

    def test_network_is_unavailable(self):
        with self.assertRaises(ValueError):
            self.execute('result = pl.read_csv("http://1.1.1.1:80/private.csv")')

    def test_oversized_result_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '32 МиБ'):
            self.execute('result = [{"x": "a" * 1024 * 1024} for i in range(40)]')

    def test_even_python_introspection_cannot_reach_host_secrets(self):
        # Намеренно обходим ограничение builtins: граница безопасности находится в ОС.
        actual = self.execute('''imp = pl.__builtins__["__import__"]
os = imp("os")
result = [{"uid": os.getuid(), "token": os.environ.get("BI_PYTHON_EXECUTOR_TOKEN"),
           "project": os.path.exists("/app/.env"), "socket": os.path.exists("/var/run/docker.sock")}]
''')
        self.assertEqual(actual.to_dicts(), [{'uid': 65534, 'token': None, 'project': False, 'socket': False}])

    def test_kernel_enforces_declared_limits(self):
        actual = self.execute('''read = pl.__builtins__["open"]
status = dict(line.split(":", 1) for line in read("/proc/self/status") if ":" in line)
result = [{"memory": read("/sys/fs/cgroup/memory.max").read().strip(),
           "swap": read("/sys/fs/cgroup/memory.swap.max").read().strip(),
           "pids": read("/sys/fs/cgroup/pids.max").read().strip(),
           "caps": status["CapEff"].strip(), "seccomp": status["Seccomp"].strip(),
           "no_new_privs": status["NoNewPrivs"].strip()}]
''')
        self.assertEqual(actual.to_dicts(), [{'memory': '536870912', 'swap': '0', 'pids': '32',
                                            'caps': '0000000000000000', 'seccomp': '2', 'no_new_privs': '1'}])

    def test_sleep_is_stopped_by_wall_clock_limit(self):
        started = time.monotonic()
        with self.assertRaisesRegex(ValueError, 'лимит времени'):
            self.execute('pl.__builtins__["__import__"]("time").sleep(60)')
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(self.execute('result = df.head(1)').height, 1)

    def test_supervisor_stops_job_even_after_docker_client_dies(self):
        runtime = DockerExecutor()
        name = 'bi-modern-python-supervisor-test-' + uuid.uuid4().hex
        buffer = io.BytesIO()
        pl.DataFrame({'x': [1]}).write_ipc(buffer)
        code = '''imp = pl.__builtins__["__import__"]
imp("os").kill(1, 9)
imp("time").sleep(60)
'''
        payload = pack({'code': code, 'mode': 'polars'}, buffer.getvalue())
        client = None
        try:
            runtime._command(*runtime.create_arguments(name))
            client = subprocess.Popen(['docker', 'start', '-ai', name], stdin=subprocess.PIPE,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            client.stdin.write(payload)
            client.stdin.close()
            time.sleep(2)
            self.assertIsNone(client.poll(), 'Рабочий процесс должен исполняться перед обрывом клиента.')
            self.assertEqual(runtime._command('inspect', '--format', '{{.State.Running}}', name).strip(), b'true')
            client.kill()
            client.wait(timeout=5)
            deadline = time.monotonic() + 25
            while runtime._command('ps', '-aq', '--filter', 'name=' + name).strip():
                if time.monotonic() >= deadline:
                    self.fail('Контейнер пережил независимый таймер после смерти клиента Docker.')
                time.sleep(0.5)
        finally:
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if client is not None and client.poll() is None:
                client.kill()
                client.wait(timeout=5)

    def test_worker_cannot_change_supervisor_memory(self):
        with self.assertRaisesRegex(ValueError, 'Permission denied'):
            self.execute('result = pl.__builtins__["open"]("/proc/1/mem", "r+b")')
