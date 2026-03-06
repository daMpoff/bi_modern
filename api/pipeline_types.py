# -*- coding: utf-8 -*-
"""
Унифицированный тип данных пайплайна BI.
PipelineData — pl.LazyFrame | pl.DataFrame | List[Dict]; конвертация только при необходимости.
Lazy-режим: данные проходят через пайплайн как LazyFrame, collect() только в терминалах.
"""
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

PipelineData = Union["pl.LazyFrame", "pl.DataFrame", List[Dict[str, Any]]]

try:
    import polars as pl
    _POLARS_AVAILABLE = True
except ImportError:
    pl = None
    _POLARS_AVAILABLE = False


def is_lazy(data: Any) -> bool:
    """Проверяет, является ли data Polars LazyFrame."""
    if not _POLARS_AVAILABLE or data is None:
        return False
    return isinstance(data, pl.LazyFrame)


def to_lazy(data: Any) -> Any:
    """
    Конвертирует данные в Polars LazyFrame для ленивого выполнения.
    DataFrame -> .lazy(), LazyFrame -> as-is, List[Dict] -> DataFrame -> .lazy().
    Если Polars недоступен, возвращает данные как есть.
    """
    if not _POLARS_AVAILABLE:
        return data
    if data is None:
        return pl.LazyFrame()
    if isinstance(data, pl.LazyFrame):
        return data
    if isinstance(data, pl.DataFrame):
        return data.lazy()
    if isinstance(data, list):
        if not data:
            return pl.LazyFrame()
        if isinstance(data[0], dict):
            return pl.DataFrame(data).lazy()
        return pl.LazyFrame()
    if isinstance(data, dict):
        columns = data.get('columns')
        rows = data.get('rows')
        if columns and rows and isinstance(columns, list) and isinstance(rows, list):
            col_data = {}
            for col_idx, col in enumerate(columns):
                col_data[col] = [
                    row[col_idx] if col_idx < len(row) else None
                    for row in rows
                ]
            return pl.DataFrame(col_data).lazy()
        return pl.LazyFrame()
    return pl.LazyFrame()


def collect_result(data: Any, streaming: bool = True) -> Any:
    """
    Материализует LazyFrame в DataFrame. DataFrame и List[Dict] возвращает как есть.
    Вызывать только в терминальных узлах (Output, Chart) или перед PythonScript.
    """
    if not _POLARS_AVAILABLE:
        return data
    if isinstance(data, pl.LazyFrame):
        try:
            return data.collect(streaming=streaming)
        except Exception:
            return data.collect()
    return data


def get_schema_names(data: Any) -> List[str]:
    """Возвращает имена колонок для DataFrame или LazyFrame."""
    if not _POLARS_AVAILABLE or data is None:
        return []
    if isinstance(data, pl.LazyFrame):
        try:
            return data.collect_schema().names()
        except Exception:
            return []
    if isinstance(data, pl.DataFrame):
        return data.columns
    return []


def to_dataframe(data: Any) -> Any:
    """
    Приводит данные к polars DataFrame (column-oriented construction).
    Поддерживает: pl.LazyFrame, pl.DataFrame, List[Dict], dict с columns/rows, None.
    При отсутствии polars возвращает данные как есть (List[Dict]) для fallback.
    """
    if data is None:
        return pl.DataFrame() if _POLARS_AVAILABLE else []

    if _POLARS_AVAILABLE:
        if isinstance(data, pl.DataFrame):
            return data
        if isinstance(data, pl.LazyFrame):
            return collect_result(data)

    if isinstance(data, list):
        if not data:
            return pl.DataFrame() if _POLARS_AVAILABLE else []
        if isinstance(data[0], dict):
            return pl.DataFrame(data) if _POLARS_AVAILABLE else data
        return pl.DataFrame() if _POLARS_AVAILABLE else []

    if isinstance(data, dict):
        columns = data.get('columns')
        rows = data.get('rows')
        if columns and rows and isinstance(columns, list) and isinstance(rows, list):
            if _POLARS_AVAILABLE:
                col_data = {}
                for col_idx, col in enumerate(columns):
                    col_data[col] = [
                        row[col_idx] if col_idx < len(row) else None
                        for row in rows
                    ]
                return pl.DataFrame(col_data)
            return [dict(zip(columns, row)) for row in rows]
        return pl.DataFrame() if _POLARS_AVAILABLE else []

    return pl.DataFrame() if _POLARS_AVAILABLE else []


def to_rows(data: Any) -> List[Dict[str, Any]]:
    """Приводит данные к List[Dict]."""
    if data is None:
        return []

    if _POLARS_AVAILABLE and isinstance(data, pl.LazyFrame):
        try:
            return collect_result(data).to_dicts()
        except Exception:
            return []

    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            return data
        return []

    if _POLARS_AVAILABLE and hasattr(data, 'to_dicts') and callable(getattr(data, 'to_dicts')):
        return data.to_dicts()

    if isinstance(data, dict):
        columns = data.get('columns')
        rows = data.get('rows')
        if columns and rows and isinstance(columns, list) and isinstance(rows, list):
            return [dict(zip(columns, row)) for row in rows]
        return []

    return []


def to_rows_slice(data: Any, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Конвертирует данные в List[Dict], но только первые limit строк.
    Если limit=None, конвертирует все (аналог to_rows).
    """
    if data is None:
        return []

    if _POLARS_AVAILABLE and isinstance(data, pl.LazyFrame):
        try:
            sliced = data.head(limit) if (limit is not None and limit > 0) else data
            return collect_result(sliced).to_dicts()
        except Exception:
            return []

    if _POLARS_AVAILABLE and hasattr(data, 'head') and hasattr(data, 'to_dicts'):
        if limit is not None and limit > 0:
            return data.head(limit).to_dicts()
        return data.to_dicts()

    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            return data[:limit] if limit else data
        return []

    if isinstance(data, dict):
        columns = data.get('columns')
        rows = data.get('rows')
        if columns and rows and isinstance(columns, list) and isinstance(rows, list):
            subset = rows[:limit] if limit else rows
            return [dict(zip(columns, row)) for row in subset]
        return []

    return []


def to_json_bytes(data: Any, limit: Optional[int] = None) -> bytes:
    """
    Сериализует DataFrame-slice напрямую в JSON-массив (bytes).
    Обходит создание Python-словарей — Polars генерирует JSON на Rust-уровне.
    """
    import io

    if data is None:
        return b'[]'

    if _POLARS_AVAILABLE and isinstance(data, pl.LazyFrame):
        try:
            sliced = data.head(limit) if (limit is not None and limit > 0) else data
            data = collect_result(sliced)
        except Exception:
            return _fallback_json_bytes(data, limit)

    if _POLARS_AVAILABLE and hasattr(data, 'head') and hasattr(data, 'write_ndjson'):
        sliced = data.head(limit) if (limit is not None and limit > 0) else data
        buf = io.BytesIO()
        try:
            sliced.write_ndjson(buf)
        except Exception:
            return _fallback_json_bytes(sliced)
        raw = buf.getvalue()
        if not raw:
            return b'[]'
        return b'[' + raw.rstrip(b'\n').replace(b'\n', b',') + b']'

    return _fallback_json_bytes(data, limit)


def _fallback_json_bytes(data: Any, limit: Optional[int] = None) -> bytes:
    """Фоллбек: to_rows_slice -> json.dumps."""
    import json
    rows = to_rows_slice(data, limit)
    return json.dumps(rows, ensure_ascii=False, default=str).encode('utf-8')


def is_polars_available() -> bool:
    return _POLARS_AVAILABLE


def row_count(data: Any) -> int:
    """Количество строк без конвертации в rows."""
    if data is None:
        return 0
    if isinstance(data, list):
        return len(data)
    if _POLARS_AVAILABLE:
        if isinstance(data, pl.LazyFrame):
            try:
                return data.select(pl.len()).collect().item()
            except Exception:
                return 0
        if isinstance(data, pl.DataFrame):
            return data.height
    if isinstance(data, dict):
        rows = data.get('rows')
        return len(rows) if rows else 0
    return 0
