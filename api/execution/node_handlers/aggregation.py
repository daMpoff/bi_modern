# -*- coding: utf-8 -*-
"""Обработчик узла «Агрегация»."""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def apply_aggregation(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Применить агрегацию к данным.
    config.groupBy: [field1, field2, ...]
    config.aggregations: [{ field, agg: 'sum'|'count'|'avg'|'min'|'max' }]
    """
    group_by = config.get('groupBy') or []
    aggregations = config.get('aggregations') or []

    if not aggregations or not data:
        return data

    groups = {}
    for row in data:
        if group_by:
            key = tuple(row.get(f) for f in group_by)
        else:
            key = ('__all__',)

        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    result = []
    for key, rows in groups.items():
        agg_row = {}

        if group_by:
            for i, field in enumerate(group_by):
                agg_row[field] = key[i]

        for agg in aggregations:
            field = agg.get('field')
            agg_func = (agg.get('agg') or 'count').lower()
            output_name = agg.get('outputName') or f'{field}_{agg_func}'

            values = [r.get(field) for r in rows if r.get(field) is not None]
            numeric_values = []
            for v in values:
                try:
                    numeric_values.append(float(v))
                except (TypeError, ValueError):
                    pass

            if agg_func == 'count':
                agg_row[output_name] = len(rows)
            elif agg_func == 'sum':
                agg_row[output_name] = sum(numeric_values) if numeric_values else 0
            elif agg_func == 'avg':
                agg_row[output_name] = sum(numeric_values) / len(numeric_values) if numeric_values else 0
            elif agg_func == 'min':
                agg_row[output_name] = min(numeric_values) if numeric_values else None
            elif agg_func == 'max':
                agg_row[output_name] = max(numeric_values) if numeric_values else None
            elif agg_func == 'ucount':
                agg_row[output_name] = len(set(values))
            else:
                agg_row[output_name] = len(rows)

        result.append(agg_row)

    return result


def apply_aggregation_polars(df: Any, config: Dict[str, Any]) -> Any:
    """
    Векторизованная агрегация через Polars. Работает и с DataFrame, и с LazyFrame.
    config.groupBy: [field1, field2, ...]
    config.aggregations: [{ field, agg: 'sum'|'count'|'avg'|'min'|'max'|'ucount', outputName }]
    LazyFrame: group_by/agg добавляются в план (query reordering при collect).
    """
    try:
        import polars as pl
    except ImportError:
        return df

    group_by = config.get('groupBy') or []
    aggregations = config.get('aggregations') or []
    if not aggregations:
        return df
    if not isinstance(df, pl.LazyFrame) and hasattr(df, 'is_empty') and df.is_empty():
        return df

    agg_exprs = []
    for agg in aggregations:
        field = agg.get('field')
        agg_func = (agg.get('agg') or 'count').lower()
        output_name = (agg.get('outputName') or (f'{field}_{agg_func}' if field else f'count_{agg_func}')).strip()
        col = pl.col(field) if field else pl.lit(1)
        if agg_func == 'count':
            agg_exprs.append(pl.len().alias(output_name))
        elif agg_func == 'sum':
            agg_exprs.append(col.sum().alias(output_name))
        elif agg_func == 'avg':
            agg_exprs.append(col.mean().alias(output_name))
        elif agg_func == 'min':
            agg_exprs.append(col.min().alias(output_name))
        elif agg_func == 'max':
            agg_exprs.append(col.max().alias(output_name))
        elif agg_func == 'ucount':
            agg_exprs.append(col.n_unique().alias(output_name))
        else:
            agg_exprs.append(pl.len().alias(output_name))

    try:
        if group_by:
            return df.group_by(group_by).agg(agg_exprs)
        return df.select(agg_exprs)
    except Exception as e:
        logger.warning('Polars aggregation failed, fallback to Python: %s', e)
        from ...pipeline_types import collect_result
        eager_df = collect_result(df) if isinstance(df, pl.LazyFrame) else df
        try:
            rows = eager_df.to_dicts()
        except Exception:
            rows = []
        return apply_aggregation(rows, config)
