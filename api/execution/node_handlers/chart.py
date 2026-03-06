# -*- coding: utf-8 -*-
"""Обработчик узла «График»: фильтрация полей по настройкам графика."""
from typing import Any, Dict, List


def filter_chart_data_by_config(data: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Оставляет в каждой строке только поля, указанные в настройках графика
    (xField, yFields, colorField).
    """
    if not data:
        return data
    x_field = (config.get('xField') or '').strip()
    y_fields = config.get('yFields') or []
    if isinstance(y_fields, str):
        y_fields = [y_fields] if y_fields else []
    y_fields = [f for f in y_fields if (f or '').strip()]
    color_field = (config.get('colorField') or '').strip()
    keys_order = []
    if x_field:
        keys_order.append(x_field)
    keys_order.extend(y_fields)
    if color_field and color_field not in keys_order:
        keys_order.append(color_field)
    if not keys_order:
        return data
    result = []
    for row in data:
        if not isinstance(row, dict):
            result.append(row)
            continue
        filtered = {k: row[k] for k in keys_order if k in row}
        result.append(filtered)
    return result
