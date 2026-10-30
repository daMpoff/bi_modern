"""Этот файл выполняется ТОЛЬКО в одноразовом контейнере без секретов и сети."""
import io
import os
import sys

import polars as pl

from .protocol import LimitedBuffer, MAX_MESSAGE, pack, unpack, validate_request


class LazyRows:
    def __init__(self, frame):
        self.frame = frame
        self.rows = None

    def materialize(self):
        if self.rows is None:
            self.rows = self.frame.to_dicts()
        return self.rows

    def __iter__(self):
        return iter(self.materialize())

    def __len__(self):
        return self.frame.height if self.rows is None else len(self.rows)

    def __getitem__(self, key):
        return self.materialize()[key]

    def __setitem__(self, key, value):
        self.materialize()[key] = value

    def append(self, value):
        self.materialize().append(value)

    def extend(self, values):
        self.materialize().extend(values)


def execute(frame, code, mode):
    rows = LazyRows(frame) if mode == 'polars' else frame.to_dicts()
    # Совместимость прежних скриптов. Это НЕ граница безопасности: её задаёт Docker.
    names = ('len range enumerate zip map filter sorted reversed min max sum abs round '
             'int float str bool list dict tuple set isinstance type').split()
    import builtins
    namespace = {'__builtins__': {name: getattr(builtins, name) for name in names},
                 'rows': rows, 'df': frame, 'pl': pl}
    namespace['__builtins__']['print'] = lambda *args, **kwargs: None
    exec(compile(code, '<pipeline_script>', 'exec'), namespace, namespace)
    if 'result' in namespace:
        result = namespace['result']
    elif mode == 'polars' and namespace.get('df') is not frame:
        result = namespace['df']
    else:
        result = namespace['rows']
    if isinstance(result, LazyRows):
        if result.rows is None:
            return frame
        result = result.rows
    if isinstance(result, pl.LazyFrame):
        result = result.collect()
    if isinstance(result, list) and all(isinstance(row, dict) for row in result):
        result = pl.DataFrame(result)
    if not isinstance(result, pl.DataFrame):
        raise ValueError('result должен быть DataFrame или списком словарей.')
    return result


def main():
    import resource
    # Дополнительные жёсткие лимиты ядра внутри cgroup. Код не может поднять hard limit.
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    output = sys.stdout.buffer
    sys.stdout = open(os.devnull, 'w')
    try:
        header, data = unpack(sys.stdin.buffer.read(MAX_MESSAGE + 1))
        validate_request(header)
        frame = pl.read_ipc(io.BytesIO(data), memory_map=False)
        result = execute(frame, header['code'], header['mode'])
        buffer = LimitedBuffer()
        result.write_ipc(buffer)
        response = pack({'ok': True}, buffer.getvalue())
    except Exception as exc:
        response = pack({'ok': False, 'error': str(exc)[:1000]})
    output.write(response)
    output.flush()


if __name__ == '__main__':
    main()
