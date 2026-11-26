"""Временные загрузки. Клиент пересылает подписанное имя без пути на сервере."""
import os
import tempfile

from django.core import signing


def _signer(user):
    return signing.Signer(salt=f'bi_analysis_modern.temp-upload.{user.pk}')


def save_upload(upload, user):
    suffix = os.path.splitext(upload.name)[1]
    tmp = tempfile.NamedTemporaryFile(prefix='bi-modern-upload-', suffix=suffix, delete=False)
    try:
        with tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
        return _signer(user).sign(os.path.basename(tmp.name))
    except Exception:
        os.unlink(tmp.name)
        raise


def resolve_upload(reference, user):
    if not isinstance(reference, str):
        return None
    try:
        name = _signer(user).unsign(reference)
    except signing.BadSignature:
        return None
    if name != os.path.basename(name) or not name.startswith('bi-modern-upload-'):
        return None
    path = os.path.join(tempfile.gettempdir(), name)
    return path if os.path.isfile(path) else None
