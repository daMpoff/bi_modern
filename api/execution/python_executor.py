"""Клиент изолированного исполнителя. Локального exec и небезопасного резерва нет."""
import io
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

import polars as pl
from django.conf import settings

from ...sandbox.protocol import LimitedBuffer, MAX_CODE, MAX_MESSAGE, pack, unpack


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def execute_isolated(frame, code, mode):
    if not isinstance(code, str) or len(code.encode('utf-8')) > MAX_CODE:
        raise ValueError('Python-код должен быть строкой размером не более 64 КиБ.')
    url = getattr(settings, 'BI_PYTHON_EXECUTOR_URL', os.environ.get('BI_PYTHON_EXECUTOR_URL', ''))
    token = getattr(settings, 'BI_PYTHON_EXECUTOR_TOKEN', os.environ.get('BI_PYTHON_EXECUTOR_TOKEN', ''))
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.query or parts.fragment or len(token) < 32:
        raise ValueError('Изолированный исполнитель Python не настроен. Настройте BI_PYTHON_EXECUTOR_URL и BI_PYTHON_EXECUTOR_TOKEN.')
    buffer = LimitedBuffer()
    frame.write_ipc(buffer)
    payload = pack({'code': code, 'mode': mode}, buffer.getvalue())
    request = Request(url.rstrip('/') + '/execute', data=payload, method='POST', headers={
        'Authorization': 'Bearer ' + token, 'Content-Type': 'application/octet-stream',
    })
    # Не передаём внутренний токен прокси из окружения или на адрес из HTTP redirect.
    opener = build_opener(ProxyHandler({}), NoRedirects())
    try:
        try:
            response = opener.open(request, timeout=40)
        except HTTPError as exc:
            if exc.code not in (422, 503):
                exc.close()
                raise ValueError('Исполнитель Python отклонил запрос.') from None
            response = exc
        with response:
            message = response.read(MAX_MESSAGE + 1)
        header, data = unpack(message)
        if header.get('ok') is not True:
            raise ValueError('Ошибка Python-блока: ' + str(header.get('error', 'неверный ответ'))[:1000])
        return pl.read_ipc(io.BytesIO(data), memory_map=False)
    except (URLError, TimeoutError, OSError) as exc:
        raise ValueError('Изолированный исполнитель Python недоступен.') from exc
