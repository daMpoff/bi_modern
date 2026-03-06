# -*- coding: utf-8 -*-
"""Обработчик узла «Фильтр»."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def coerce_for_compare(val: Any) -> Tuple[Any, str]:
    """
    Приводит значение к числу или дате для сравнения.
    Возвращает (приведённое_значение, 'number'|'date'|'string').
    """
    if val is None:
        return None, 'string'
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return val, 'number'
    if isinstance(val, datetime):
        return val, 'date'
    try:
        if isinstance(val, str) and val.strip() == '':
            return val, 'string'
        try:
            s = str(val).strip().replace(',', '.')
            if '.' in s or 'e' in s.lower():
                return float(s), 'number'
            n = int(s)
            return n, 'number'
        except (TypeError, ValueError):
            pass
        for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d.%m.%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(str(val).strip()[:19], fmt), 'date'
            except (TypeError, ValueError):
                continue
    except (TypeError, ValueError):
        pass
    return str(val), 'string'


def _resolve_value(value: Any, params: Dict[str, Any]) -> Any:
    """Подставляет значение параметра, если value — строка вида $param_name."""
    if isinstance(value, str) and value.strip().startswith('$'):
        param_name = value.strip()[1:].strip()
        if param_name:
            return params.get(param_name)
    return value


def apply_filter(
    data: List[Dict[str, Any]],
    config: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Применить фильтр к данным.
    config.conditions: [{ field, operator, value }]
    value для between: { min, max } или [min, max].
    Если value — строка вида $param_name, подставляется значение из params.
    """
    params = params or {}
    conditions = config.get('conditions') or []
    if not conditions or not data:
        return data

    result = []
    for row in data:
        match = True
        for cond in conditions:
            field = cond.get('field')
            operator = cond.get('operator', '=')
            raw_value = cond.get('value')
            value = _resolve_value(raw_value, params)
            if isinstance(raw_value, str) and raw_value.strip().startswith('$'):
                if value is None or value == '':
                    continue
            if field not in row:
                continue

            row_value = row[field]

            try:
                if operator == 'isnull':
                    match = row_value is None
                elif operator == 'notnull':
                    match = row_value is not None
                elif operator == 'contains':
                    match = str(value).lower() in str(row_value).lower()
                elif operator == 'startswith':
                    match = str(row_value).lower().startswith(str(value).lower())
                elif operator == 'endswith':
                    match = str(row_value).lower().endswith(str(value).lower())
                elif operator == 'between':
                    if value is None:
                        match = False
                    else:
                        if isinstance(value, dict):
                            min_val = _resolve_value(value.get('min'), params)
                            max_val = _resolve_value(value.get('max'), params)
                        elif isinstance(value, (list, tuple)) and len(value) >= 2:
                            min_val = _resolve_value(value[0], params)
                            max_val = _resolve_value(value[1], params)
                        else:
                            min_val = max_val = None
                        rv, rk = coerce_for_compare(row_value)
                        mn, mk = coerce_for_compare(min_val)
                        mx, _ = coerce_for_compare(max_val)
                        if rk == 'number' and mk == 'number':
                            try:
                                rv_n = float(rv) if rv is not None else None
                                mn_n = float(mn) if mn is not None else None
                                mx_n = float(mx) if mx is not None else None
                                match = (mn_n is not None and mx_n is not None and rv_n is not None and
                                         mn_n <= rv_n <= mx_n)
                            except (TypeError, ValueError):
                                match = False
                        elif rk == 'date':
                            match = (mn is not None and mx is not None and rv is not None and
                                     mn <= rv <= mx)
                        else:
                            match = (mn is not None and mx is not None and
                                     str(mn) <= str(row_value) <= str(mx))
                else:
                    rv, rk = coerce_for_compare(row_value)
                    cv, ck = coerce_for_compare(value)
                    if rk == 'number' and ck == 'number':
                        rv = float(rv) if rv is not None else None
                        cv = float(cv) if cv is not None else None
                    if operator == '=' or operator == '==':
                        match = rv == cv
                    elif operator == '!=' or operator == '<>':
                        match = rv != cv
                    elif operator == '>':
                        match = rv is not None and cv is not None and rv > cv
                    elif operator == '>=':
                        match = rv is not None and cv is not None and rv >= cv
                    elif operator == '<':
                        match = rv is not None and cv is not None and rv < cv
                    elif operator == '<=':
                        match = rv is not None and cv is not None and rv <= cv
                    else:
                        match = rv == cv
            except (TypeError, ValueError):
                match = False

            if not match:
                break

        if match:
            result.append(row)

    return result


def _get_col_dtype(col_name: str, df: Any) -> Any:
    """Получает тип колонки из DataFrame или LazyFrame."""
    try:
        import polars as pl
    except ImportError:
        return None
    try:
        if isinstance(df, pl.LazyFrame):
            schema = df.collect_schema()
            return schema.get(col_name)
        return df[col_name].dtype
    except Exception:
        return None


def _get_columns(df: Any) -> list:
    """Получает список колонок из DataFrame или LazyFrame."""
    try:
        import polars as pl
    except ImportError:
        return []
    if isinstance(df, pl.LazyFrame):
        try:
            return df.collect_schema().names()
        except Exception:
            return []
    if hasattr(df, 'columns'):
        return df.columns
    return []


def _cast_value_for_col(value: Any, col_name: str, df: Any) -> Any:
    """Приводит значение фильтра к типу колонки DataFrame/LazyFrame для корректного сравнения в Polars."""
    try:
        import polars as pl
    except ImportError:
        return value
    if value is None:
        return value
    dtype = _get_col_dtype(col_name, df)
    if dtype is None:
        return value
    try:
        if dtype in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                     pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
            s = str(value).strip().replace(',', '.')
            return int(float(s))
        if dtype in (pl.Float32, pl.Float64):
            return float(str(value).strip().replace(',', '.'))
        if dtype == pl.Boolean:
            return str(value).strip().lower() in ('true', '1', 'yes')
        if dtype in (pl.Utf8, pl.String):
            return str(value)
    except (TypeError, ValueError):
        pass
    return value


def apply_filter_polars(
    df: Any,
    config: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Векторизованный фильтр через Polars. Работает и с DataFrame, и с LazyFrame.
    config.conditions: [{ field, operator, value }]
    LazyFrame: предикаты добавляются в план (predicate pushdown при collect).
    """
    try:
        import polars as pl
    except ImportError:
        return df

    params = params or {}
    conditions = config.get('conditions') or []
    if not conditions:
        return df
    if not isinstance(df, pl.LazyFrame) and hasattr(df, 'is_empty') and df.is_empty():
        return df

    columns = _get_columns(df)
    predicates = []
    for cond in conditions:
        field = cond.get('field')
        operator = (cond.get('operator') or '=').lower()
        raw_value = cond.get('value')
        value = _resolve_value(raw_value, params)
        if isinstance(raw_value, str) and raw_value.strip().startswith('$'):
            if value is None or value == '':
                continue
        if not field or field not in columns:
            continue

        col = pl.col(field)
        try:
            if operator == 'isnull':
                predicates.append(col.is_null())
            elif operator == 'notnull':
                predicates.append(col.is_not_null())
            elif operator == 'contains':
                pattern = str(value).lower()
                predicates.append(col.cast(pl.Utf8).str.to_lowercase().str.contains(pattern, literal=True))
            elif operator == 'startswith':
                prefix = str(value).lower()
                predicates.append(col.cast(pl.Utf8).str.to_lowercase().str.starts_with(prefix))
            elif operator == 'endswith':
                suffix = str(value).lower()
                predicates.append(col.cast(pl.Utf8).str.to_lowercase().str.ends_with(suffix))
            elif operator == 'between':
                if value is None:
                    continue
                if isinstance(value, dict):
                    min_val = _resolve_value(value.get('min'), params)
                    max_val = _resolve_value(value.get('max'), params)
                elif isinstance(value, (list, tuple)) and len(value) >= 2:
                    min_val = _resolve_value(value[0], params)
                    max_val = _resolve_value(value[1], params)
                else:
                    continue
                min_val = _cast_value_for_col(min_val, field, df)
                max_val = _cast_value_for_col(max_val, field, df)
                try:
                    predicates.append(col.is_between(min_val, max_val))
                except Exception:
                    predicates.append((col >= min_val) & (col <= max_val))
            else:
                value = _cast_value_for_col(value, field, df)
                if operator in ('=', '=='):
                    predicates.append(col == value)
                elif operator in ('!=', '<>'):
                    predicates.append(col != value)
                elif operator == '>':
                    predicates.append(col > value)
                elif operator == '>=':
                    predicates.append(col >= value)
                elif operator == '<':
                    predicates.append(col < value)
                elif operator == '<=':
                    predicates.append(col <= value)
                else:
                    predicates.append(col == value)
        except Exception as e:
            logger.debug('Polars filter predicate failed for %s %s: %s', field, operator, e)

    if not predicates:
        return df
    combined = predicates[0]
    for p in predicates[1:]:
        combined = combined & p
    return df.filter(combined)
