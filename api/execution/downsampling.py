# -*- coding: utf-8 -*-
"""
Server-side downsampling for chart data.

Reduces large datasets to a manageable number of points for chart rendering
while preserving the visual shape of the data.

Algorithms:
- LTTB (Largest Triangle Three Buckets) — for time-series (line, area)
- Uniform sampling — for scatter, bar, and generic charts
- Top-N with "Other" — for pie, doughnut, funnel
"""
import logging
import math
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

try:
    import polars as pl
    _POLARS = True
except ImportError:
    pl = None
    _POLARS = False


def _lttb_downsample_lists(x_vals: list, y_vals: list, target: int) -> list:
    """
    Pure-Python LTTB implementation.
    Returns list of indices to keep.
    """
    n = len(x_vals)
    if n <= target or target < 3:
        return list(range(n))

    selected = [0]
    bucket_size = (n - 2) / (target - 2)

    a_idx = 0

    for i in range(1, target - 1):
        bucket_start = int(math.floor(1 + (i - 1) * bucket_size))
        bucket_end = int(math.floor(1 + i * bucket_size))
        bucket_end = min(bucket_end, n - 1)

        next_start = int(math.floor(1 + i * bucket_size))
        next_end = int(math.floor(1 + (i + 1) * bucket_size))
        next_end = min(next_end, n)

        avg_x = sum(x_vals[j] for j in range(next_start, next_end)) / max(1, next_end - next_start)
        avg_y = sum(y_vals[j] for j in range(next_start, next_end)) / max(1, next_end - next_start)

        max_area = -1.0
        max_idx = bucket_start

        ax = x_vals[a_idx]
        ay = y_vals[a_idx]

        for j in range(bucket_start, bucket_end + 1):
            if j >= n:
                break
            area = abs(
                (x_vals[j] - ax) * (avg_y - ay) -
                (avg_x - ax) * (y_vals[j] - ay)
            )
            if area > max_area:
                max_area = area
                max_idx = j

        selected.append(max_idx)
        a_idx = max_idx

    selected.append(n - 1)
    return selected


def lttb_downsample(df, x_field: str, y_field: str, target: int):
    """
    LTTB downsample a Polars DataFrame.
    Falls back to uniform if fields are non-numeric.
    """
    if not _POLARS or df is None:
        return df

    n = len(df) if hasattr(df, '__len__') else df.height if hasattr(df, 'height') else 0
    if n <= target:
        return df

    try:
        x_series = df[x_field]
        y_series = df[y_field]

        try:
            x_vals = x_series.cast(pl.Float64).to_list()
        except Exception:
            x_vals = list(range(n))

        try:
            y_vals = y_series.cast(pl.Float64).fill_null(0.0).to_list()
        except Exception:
            return uniform_sample(df, target)

        indices = _lttb_downsample_lists(x_vals, y_vals, target)
        return df[indices]
    except Exception as e:
        logger.debug('LTTB downsample failed: %s, falling back to uniform', e)
        return uniform_sample(df, target)


def uniform_sample(df, target: int):
    """
    Take every Nth row to reach ~target rows.
    Always includes first and last rows.
    """
    if not _POLARS or df is None:
        return df

    n = len(df) if hasattr(df, '__len__') else df.height if hasattr(df, 'height') else 0
    if n <= target:
        return df

    step = max(1, n // target)
    return df.gather_every(step)


def top_n_aggregate(df, name_field: str, value_field: str, top_n: int = 20):
    """
    Keep top N categories by value, aggregate rest into "Другое".
    """
    if not _POLARS or df is None:
        return df

    n = len(df) if hasattr(df, '__len__') else df.height if hasattr(df, 'height') else 0
    if n <= top_n:
        return df

    try:
        sorted_df = df.sort(value_field, descending=True)
        top = sorted_df.head(top_n)
        rest = sorted_df.slice(top_n)

        if rest.height == 0:
            return top

        rest_sum = rest[value_field].sum()
        other_row = {name_field: 'Другое', value_field: rest_sum}
        other_df = pl.DataFrame(other_row)

        return pl.concat([top, other_df], how='diagonal_relaxed')
    except Exception as e:
        logger.debug('Top-N aggregation failed: %s, returning head', e)
        return df.head(top_n)


_LTTB_TYPES = {'line', 'area', 'candlestick'}
_TOPN_TYPES = {'pie', 'doughnut', 'funnel'}


def downsample_for_chart(
    df,
    chart_type: str = 'bar',
    x_field: str = '',
    y_fields: Optional[List[str]] = None,
    max_points: int = 50000,
) -> Any:
    """
    Smart downsampling dispatcher based on chart type.

    Args:
        df: Polars DataFrame
        chart_type: ECharts chart type string
        x_field: X-axis field name
        y_fields: Y-axis field names
        max_points: Maximum data points to return

    Returns:
        Downsampled Polars DataFrame
    """
    if df is None:
        return df

    n = len(df) if hasattr(df, '__len__') else getattr(df, 'height', 0)
    if n <= max_points:
        return df

    logger.debug(
        'Downsampling %d rows to %d for chart_type=%s',
        n, max_points, chart_type,
    )

    y_fields = y_fields or []

    if chart_type in _LTTB_TYPES and x_field and y_fields:
        return lttb_downsample(df, x_field, y_fields[0], max_points)

    if chart_type in _TOPN_TYPES and x_field and y_fields:
        return top_n_aggregate(df, x_field, y_fields[0], min(max_points, 100))

    return uniform_sample(df, max_points)
