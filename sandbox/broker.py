"""Внутренний HTTP-сервис. Только доверенная сеть; токен не попадает в контейнеры задач."""
import hmac
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .protocol import MAX_MESSAGE, pack
from .runtime import DockerExecutor, ExecutionError


class ExecutorServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8

    def __init__(self, address, executor, token, max_jobs=2):
        if len(token) < 32:
            raise ValueError('Токен исполнителя должен содержать не менее 32 символов.')
        self.executor = executor
        self.token = token
        self.slots = threading.BoundedSemaphore(max_jobs)
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *args):
        # Код, строки данных, токены и ответы не записываются в журнал HTTP.
        pass

    def reply(self, status, body=b''):
        self.send_response(status)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def authorized(self):
        supplied = self.headers.get('Authorization', '').encode('utf-8')
        expected = ('Bearer ' + self.server.token).encode('utf-8')
        return hmac.compare_digest(supplied, expected)

    def do_GET(self):
        if not self.authorized():
            self.reply(401)
        else:
            self.reply(200 if self.path == '/health' else 404)

    def do_POST(self):
        if not self.authorized():
            self.reply(401)
            return
        if self.path != '/execute':
            self.reply(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_MESSAGE or self.headers.get('Transfer-Encoding'):
            self.reply(413)
            return
        if not self.server.slots.acquire(blocking=False):
            self.reply(503, pack({'ok': False, 'error': 'Все исполнители Python заняты. Повторите запуск.'}))
            return
        try:
            payload = self.rfile.read(length)
            if len(payload) != length:
                self.reply(400)
                return
            self.reply(200, self.server.executor.execute(payload))
        except (ExecutionError, ValueError) as exc:
            self.reply(422, pack({'ok': False, 'error': str(exc)[:1000]}))
        except (OSError, TimeoutError):
            self.close_connection = True
        finally:
            self.server.slots.release()


def main():
    executor = DockerExecutor(os.environ.get('BI_PYTHON_WORKER_IMAGE', 'bi-modern-python-worker:local'))
    executor.check_runtime()
    executor.cleanup_abandoned()
    server = ExecutorServer(('0.0.0.0', 8766), executor, os.environ.get('BI_PYTHON_EXECUTOR_TOKEN', ''))
    print('BI Python executor ready on :8766', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
