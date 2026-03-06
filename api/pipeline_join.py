# -*- coding: utf-8 -*-
"""
Общая логика соединения (join) для пайплайна BI.
Один источник правды для типов join и преобразования в Polars/Python.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def apply_join(
    left_data: List[Dict[str, Any]],
    right_data: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Соединить два набора данных по ключам.
    config.joinType: INNER JOIN | LEFT JOIN | RIGHT JOIN | FULL JOIN
    config.leftKey: поле из левой таблицы
    config.rightKey: поле из правой таблицы
    """
    left_key = (config.get('leftKey') or '').strip()
    right_key = (config.get('rightKey') or '').strip()
    if not left_key or not right_key:
        return left_data if left_data else right_data

    join_type = (config.get('joinType') or 'LEFT JOIN').upper()
    try:
        import polars as pl
    except ImportError:
        return _apply_join_python(left_data, right_data, left_key, right_key, join_type)

    left_df = pl.DataFrame(left_data)
    right_df = pl.DataFrame(right_data)
    if left_df.is_empty() and right_df.is_empty():
        return []
    if left_df.is_empty():
        return right_data if 'RIGHT' in join_type or 'FULL' in join_type else []
    if right_df.is_empty():
        return left_data if 'LEFT' in join_type or 'FULL' in join_type else []

    how = 'inner' if 'INNER' in join_type else 'outer' if 'FULL' in join_type else 'left'
    if 'RIGHT' in join_type:
        left_df, right_df = right_df, left_df
        left_key, right_key = right_key, left_key
        how = 'left'

    try:
        result = left_df.join(
            right_df,
            left_on=left_key,
            right_on=right_key,
            how=how,
            suffix='_right',
        )
        return result.to_dicts()
    except Exception as e:
        logger.warning('Polars join failed, fallback to python: %s', e)
        return _apply_join_python(left_data, right_data, left_key, right_key, join_type)


def apply_join_polars(
    left_df: Any,
    right_df: Any,
    config: Dict[str, Any],
) -> Any:
    """
    Join для Polars DataFrame/LazyFrame. Принимает и возвращает DataFrame или LazyFrame.
    LazyFrame: join добавляется в план (оптимизация при collect).
    """
    try:
        import polars as pl
    except ImportError:
        return left_df

    left_key = (config.get('leftKey') or '').strip()
    right_key = (config.get('rightKey') or '').strip()

    left_is_lazy = isinstance(left_df, pl.LazyFrame)
    right_is_lazy = isinstance(right_df, pl.LazyFrame)
    if left_is_lazy and not right_is_lazy:
        if isinstance(right_df, pl.DataFrame):
            right_df = right_df.lazy()
            right_is_lazy = True
    elif right_is_lazy and not left_is_lazy:
        if isinstance(left_df, pl.DataFrame):
            left_df = left_df.lazy()
            left_is_lazy = True

    if not left_key or not right_key:
        return left_df

    if not left_is_lazy:
        if left_df.is_empty() and right_df.is_empty():
            return pl.DataFrame()
        if left_df.is_empty():
            join_type = (config.get('joinType') or 'LEFT JOIN').upper()
            return right_df if 'RIGHT' in join_type or 'FULL' in join_type else pl.DataFrame()
        if right_df.is_empty():
            join_type = (config.get('joinType') or 'LEFT JOIN').upper()
            return left_df if 'LEFT' in join_type or 'FULL' in join_type else pl.DataFrame()

    join_type = (config.get('joinType') or 'LEFT JOIN').upper()
    how = 'inner' if 'INNER' in join_type else 'outer' if 'FULL' in join_type else 'left'
    if 'RIGHT' in join_type:
        left_df, right_df = right_df, left_df
        left_key, right_key = right_key, left_key
        how = 'left'

    return left_df.join(
        right_df,
        left_on=left_key,
        right_on=right_key,
        how=how,
        suffix='_right',
    )


def _apply_join_python(
    left_data: List[Dict],
    right_data: List[Dict],
    left_key: str,
    right_key: str,
    join_type: str,
) -> List[Dict]:
    """Join без Polars (fallback)."""
    right_by_key = {}
    for row in right_data:
        k = row.get(right_key)
        if k not in right_by_key:
            right_by_key[k] = []
        right_by_key[k].append(row)

    result = []
    matched_right_keys = set()
    for lrow in left_data:
        lk = lrow.get(left_key)
        rrows = right_by_key.get(lk, [])
        matched_right_keys.add(lk)
        if rrows:
            for rrow in rrows:
                merged = {**lrow}
                for k, v in rrow.items():
                    if k != right_key and k not in merged:
                        merged[k] = v
                    elif k in merged and k != right_key:
                        merged[f'{k}_right'] = v
                result.append(merged)
        elif 'LEFT' in join_type or 'FULL' in join_type:
            result.append(dict(lrow))

    if 'RIGHT' in join_type or 'FULL' in join_type:
        for rrow in right_data:
            rk = rrow.get(right_key)
            if rk not in matched_right_keys:
                result.append(dict(rrow))

    return result
