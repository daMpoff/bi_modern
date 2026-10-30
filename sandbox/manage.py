"""Локальная установка: python modules/bi_analysis_modern/sandbox/manage.py up|down."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, build_opener, ProxyHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('up', 'down'))
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    config = root / 'env' / 'bi-python.env'
    if args.command == 'up' and not config.exists():
        config.parent.mkdir(exist_ok=True)
        descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write('BI_PYTHON_EXECUTOR_URL=http://127.0.0.1:8766\n')
            stream.write('BI_PYTHON_EXECUTOR_TOKEN=' + secrets.token_urlsafe(48) + '\n')
    command = ['docker', 'compose', '--env-file', str(config), '-f', str(here / 'compose.yaml')]
    if args.command == 'down':
        subprocess.run([*command, 'down'], check=True)
        return
    subprocess.run([*command, 'build', 'worker-image', 'broker'], check=True)
    subprocess.run([*command, 'up', '-d', '--no-build', 'broker'], check=True)
    values = dict(line.split('=', 1) for line in config.read_text(encoding='utf-8').splitlines()
                  if line.strip() and not line.startswith('#') and '=' in line)
    opener = build_opener(ProxyHandler({}))
    for _ in range(30):
        try:
            request = Request(values['BI_PYTHON_EXECUTOR_URL'].rstrip('/') + '/health',
                              headers={'Authorization': 'Bearer ' + values['BI_PYTHON_EXECUTOR_TOKEN']})
            with opener.open(request, timeout=2) as response:
                if response.status == 200:
                    print('BI Python executor ready. Restart API and Celery to load env/bi-python.env.')
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(1)
    raise SystemExit('Executor did not become healthy. Check docker compose logs broker.')


if __name__ == '__main__':
    main()
