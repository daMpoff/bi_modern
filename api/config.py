"""
Конфигурация для модуля bi_analysis.
Содержит настройки для обработки данных, включая переключение CPU/GPU.
"""

import os
from typing import Literal

ComputeDevice = Literal['cpu', 'gpu']

USE_GPU = os.getenv('BI_ANALYSIS_USE_GPU', 'true').lower() == 'true'


def get_compute_device() -> ComputeDevice:
    """
    Определяет устройство для вычислений.
    По умолчанию использует GPU, если доступен.
    """
    if USE_GPU:
        try:
            import polars as pl
            return 'gpu'
        except:
            return 'cpu'
    return 'cpu'


CHUNK_SIZE = int(os.getenv('BI_ANALYSIS_CHUNK_SIZE', '100000'))
MAX_WORKERS = int(os.getenv('BI_ANALYSIS_MAX_WORKERS', '4'))
PREVIEW_LIMIT = int(os.getenv('BI_ANALYSIS_PREVIEW_LIMIT', '1000000000'))
_PREVIEW_ROW_LIMIT_ENV = os.getenv('BI_ANALYSIS_PREVIEW_ROW_LIMIT', 'none')
PREVIEW_ROW_LIMIT = int(_PREVIEW_ROW_LIMIT_ENV) if _PREVIEW_ROW_LIMIT_ENV not in (None, '', 'none') else None

SOURCE_LIMIT = os.getenv('BI_ANALYSIS_SOURCE_LIMIT')
SOURCE_LIMIT = int(SOURCE_LIMIT) if SOURCE_LIMIT not in (None, '', 'none') else None

ASYNC_THRESHOLD = int(os.getenv('BI_ANALYSIS_ASYNC_THRESHOLD', '100000'))

_env_preview = (os.getenv('BI_ANALYSIS_EXECUTE_PREVIEW_ROWS') or '').strip().lower()
EXECUTE_PREVIEW_ROWS = int(_env_preview) if _env_preview and _env_preview != 'none' else None

EXECUTE_CHUNK_SIZE = int(os.getenv('BI_ANALYSIS_EXECUTE_CHUNK_SIZE', '5000'))

USE_SQL_PUSHDOWN = os.getenv('BI_ANALYSIS_USE_SQL_PUSHDOWN', 'true').lower() == 'true'

CHART_MAX_POINTS = int(os.getenv('BI_CHART_MAX_POINTS', '50000'))

CELERY_TASK_TIMEOUT = int(os.getenv('BI_ANALYSIS_CELERY_TIMEOUT', '300'))
CELERY_SOFT_TIMEOUT = int(os.getenv('BI_ANALYSIS_CELERY_SOFT_TIMEOUT', '270'))
