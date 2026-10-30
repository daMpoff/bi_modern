"""Результаты исполнения с TTL и отдельным ключом для каждого запуска."""
from functools import lru_cache

from django.core.cache import caches
from django.core.cache.backends.dummy import DummyCache
from django.core.cache.backends.filebased import FileBasedCache
from django.core.cache.backends.locmem import LocMemCache
from src.config.paths import CACHE_DIR

EXECUTION_RESULT_TTL = 600
ASYNC_RESULT_TTL = 3600


@lru_cache(maxsize=1)
def _local_cache():
    return FileBasedCache(str(CACHE_DIR / 'bi_modern_execution'), {'OPTIONS': {'MAX_ENTRIES': 1000}})


def execution_cache():
    backend = caches['default']
    # LocMem не виден соседнему API-воркеру и процессу Celery.
    return _local_cache() if isinstance(backend, (LocMemCache, DummyCache)) else backend


def _key(result_set_id, user_id, pipeline_id):
    return f'bi_modern:execution:{user_id}:{pipeline_id}:{result_set_id}'


def put_result(result_set_id, raw_df, columns, total_rows, user_id, pipeline_id):
    execution_cache().set(_key(result_set_id, user_id, pipeline_id), {
        'raw_df': raw_df, 'columns': columns, 'total_rows': total_rows,
    }, timeout=EXECUTION_RESULT_TTL)


def get_result(result_set_id, user_id, pipeline_id):
    return execution_cache().get(_key(result_set_id, user_id, pipeline_id))


def task_key(task_id):
    return f'bi_modern:task:{task_id}'


def task_owner_key(task_id):
    return f'bi_modern:task-owner:{task_id}'
