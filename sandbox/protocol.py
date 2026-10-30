"""Ограниченный бинарный протокол: JSON-заголовок + Arrow IPC, без pickle."""
import io
import json
import struct

MAX_HEADER = 128 * 1024
MAX_DATA = 32 * 1024 * 1024
MAX_MESSAGE = 4 + MAX_HEADER + MAX_DATA
MAX_CODE = 64 * 1024


class LimitExceeded(ValueError):
    pass


class LimitedBuffer(io.BytesIO):
    def write(self, value):
        if self.tell() + len(value) > MAX_DATA:
            raise LimitExceeded('Данные Python-блока превышают 32 МиБ.')
        return super().write(value)


def pack(header, data=b''):
    encoded = json.dumps(header, ensure_ascii=False).encode('utf-8')
    if len(encoded) > MAX_HEADER or len(data) > MAX_DATA:
        raise LimitExceeded('Превышен размер сообщения Python-блока.')
    return struct.pack('!I', len(encoded)) + encoded + data


def unpack(message):
    if len(message) < 4 or len(message) > MAX_MESSAGE:
        raise ValueError('Неверный размер сообщения исполнителя.')
    size = struct.unpack('!I', message[:4])[0]
    if size > MAX_HEADER or len(message) < 4 + size or len(message) - 4 - size > MAX_DATA:
        raise ValueError('Неверный заголовок исполнителя.')
    header = json.loads(message[4:4 + size])
    if not isinstance(header, dict):
        raise ValueError('Заголовок исполнителя должен быть объектом.')
    return header, message[4 + size:]


def validate_request(header):
    code = header.get('code')
    if not isinstance(code, str) or len(code.encode('utf-8')) > MAX_CODE:
        raise ValueError('Python-код должен быть строкой размером не более 64 КиБ.')
    if header.get('mode') not in ('rows', 'polars'):
        raise ValueError('Неизвестный формат Python-блока.')
