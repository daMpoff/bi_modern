# -*- coding: utf-8 -*-
"""Обработчик узла «Источник данных» (dataSource)."""
import logging
from typing import Any, Dict, List, Optional

from ..inline_source_executor import execute_inline_source

logger = logging.getLogger(__name__)


def get_source_data(
    config: Dict[str, Any],
    user,
    limit: Optional[int] = None,
    return_dataframe: bool = False,
    pushdown_filter: Optional[Dict[str, Any]] = None,
    pushdown_aggregation: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Получить данные из inline-источника (подключение + таблица/файл).
    limit: None — без ограничений; число — макс. строк (для preview).
    """
    if config.get('sourceMode') != 'inline':
        logger.error('Источник данных: поддерживается только sourceMode=inline')
        return None

    connection_id = config.get('connection_id')
    main_table = config.get('main_table')
    if not connection_id or not main_table:
        logger.error('Inline source: connection_id или main_table не указаны')
        return None

    return execute_inline_source(
        connection_id, main_table, [], user,
        limit=limit,
        return_dataframe=return_dataframe,
        pushdown_filter=pushdown_filter,
        pushdown_aggregation=pushdown_aggregation,
        params=params or {}
    )
