"""Управление контейнерами. Никогда не исполняет пользовательский код в сервисе."""
import json
import subprocess
import threading
import time
import uuid

from .protocol import MAX_MESSAGE, unpack, validate_request

LABEL = 'bi-modern.python-job=true'
TIMEOUT_SECONDS = 20
MEMORY_BYTES = 512 * 1024 * 1024


class ExecutionError(ValueError):
    pass


class DockerExecutor:
    def __init__(self, image='bi-modern-python-worker:local', timeout=TIMEOUT_SECONDS):
        self.image = image
        self.timeout = timeout

    def _command(self, *args, timeout=10):
        try:
            result = subprocess.run(['docker', *args], capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ExecutionError('Docker-исполнитель недоступен.') from exc
        if result.returncode:
            raise ExecutionError('Docker не смог выполнить операцию исполнителя.')
        return result.stdout

    def check_runtime(self):
        info = json.loads(self._command('info', '--format', '{{json .}}'))
        if (info.get('OSType') != 'linux' or info.get('CgroupVersion') != '2'
                or not all(info.get(key) for key in ('MemoryLimit', 'SwapLimit', 'PidsLimit', 'CpuCfsQuota'))
                or not any('seccomp' in option for option in info.get('SecurityOptions', []))):
            raise ExecutionError('Нужен Linux Docker с cgroup v2, seccomp и лимитами CPU, памяти и процессов.')
        self._command('image', 'inspect', self.image)

    def cleanup_abandoned(self):
        identifiers = self._command('ps', '-aq', '--filter', f'label={LABEL}').decode().split()
        for identifier in identifiers:
            self._command('rm', '-f', identifier)

    def create_arguments(self, name):
        return ['create', '--name', name, '--label', LABEL, '--pull=never', '--rm',
                '--network=none', '--read-only', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--user=65534:65534',
                f'--memory={MEMORY_BYTES}', f'--memory-swap={MEMORY_BYTES}', '--cpus=1',
                '--pids-limit=32', '--ulimit=nofile=128:128', '--ulimit=core=0:0',
                '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16777216,mode=1777',
                '--shm-size=8m', '--log-driver=none', '--interactive', self.image]

    def execute(self, payload):
        header, _ = unpack(payload)
        validate_request(header)
        name = 'bi-modern-python-' + uuid.uuid4().hex
        process = None
        threads = []
        output = bytearray()
        exceeded = threading.Event()
        deadline = time.monotonic() + self.timeout
        try:
            self._command(*self.create_arguments(name), timeout=min(10, self.timeout))
            process = subprocess.Popen(['docker', 'start', '--attach', '--interactive', name],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            def write_input():
                try:
                    process.stdin.write(payload)
                    process.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            def read_output(stream, store, limit):
                total = 0
                try:
                    while chunk := stream.read(65536):
                        total += len(chunk)
                        if total > limit:
                            exceeded.set()
                            return
                        if store is not None:
                            store.extend(chunk)
                except OSError:
                    pass

            for target, args in ((write_input, ()),
                                 (read_output, (process.stdout, output, MAX_MESSAGE)),
                                 (read_output, (process.stderr, None, 65536))):
                thread = threading.Thread(target=target, args=args, daemon=True)
                thread.start()
                threads.append(thread)
            while process.poll() is None:
                if exceeded.wait(0.02):
                    raise ExecutionError('Превышен размер вывода Python-блока.')
                if time.monotonic() >= deadline:
                    raise ExecutionError(f'Python-блок превысил лимит времени ({self.timeout:g} с).')
            for thread in threads:
                thread.join(timeout=max(0, deadline - time.monotonic()))
            if exceeded.is_set():
                raise ExecutionError('Превышен размер вывода Python-блока.')
            if process.returncode:
                if process.returncode == 124:
                    raise ExecutionError('Python-блок превысил лимит времени (20 с).')
                raise ExecutionError('Python-блок остановлен: ошибка процесса или превышен лимит ресурсов.')
            response, _ = unpack(output)
            if not isinstance(response.get('ok'), bool):
                raise ExecutionError('Некорректный ответ Python-блока.')
            return bytes(output)
        finally:
            # Завершаем именно контейнер, а не только клиент docker (его смерть не убивает код).
            try:
                self._command('rm', '-f', name, timeout=5)
            except ExecutionError:
                # При --rm завершённый контейнер уже удалён. Оставшиеся убираются при старте сервиса.
                pass
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                for thread in threads:
                    thread.join(timeout=1)
                for stream in (process.stdin, process.stdout, process.stderr):
                    stream.close()
