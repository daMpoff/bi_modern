# -*- coding: utf-8 -*-
"""
Получение колонок из inline-источников и предложение пар полей для соединения.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from .bi_connections.connection_runner import get_columns
from .bi_connections.models import Connection
from .bi_datasets.models import FileUpload

logger = logging.getLogger(__name__)


def get_source_columns(config: Dict, user) -> List[str]:
    """
    Получить список имён колонок из источника данных.

    Args:
        config: конфигурация узла dataSource (sourceMode='inline': connection_id, main_table)
        user: пользователь Django

    Returns:
        Список имён колонок
    """
    if config.get('sourceMode') != 'inline':
        return []
    return _get_inline_columns(config, user)


def _get_inline_columns(config: Dict, user) -> List[str]:
    connection_id = config.get('connection_id')
    main_table = config.get('main_table') or {}
    if not connection_id or not main_table:
        return []

    try:
        conn = Connection.objects.get(pk=connection_id, owner=user)
    except Connection.DoesNotExist:
        return []

    conn_type = (conn.connector_type or '').lower().strip()
    file_id = main_table.get('file_id')

    if file_id or conn_type in ('file', 'files', 'файл', 'файлы') or 'file' in conn_type:
        return _get_file_columns(file_id, user)
    return _get_db_table_columns(conn, main_table)


def _get_file_columns(file_id: Optional[int], user) -> List[str]:
    if not file_id:
        return []
    try:
        fu = FileUpload.objects.get(pk=file_id, owner=user)
        info = fu.columns_info or {}
        cols = info.get('columns')
        return list(cols) if isinstance(cols, list) else []
    except FileUpload.DoesNotExist:
        return []


def _get_db_table_columns(conn: Connection, main_table: Dict) -> List[str]:
    table_name = main_table.get('name') or main_table.get('table')
    schema = main_table.get('schema') or 'public'
    if not table_name:
        return []
    try:
        cols = get_columns(conn, table_name, schema)
        return [c["name"] for c in cols]
    except Exception as e:
        logger.warning('Failed to get DB columns: %s', e)
        return []


def suggest_join_keys(
    left_config: Dict,
    right_config: Dict,
    user
) -> Dict[str, Any]:
    """
    Найти пары колонок с совпадающими именами для соединения.

    Returns:
        {
            suggestions: [{ leftKey, rightKey }, ...],
            leftColumns: [...],
            rightColumns: [...]
        }
    """
    left_cols = get_source_columns(left_config, user)
    right_cols = get_source_columns(right_config, user)
    left_set = {c.lower(): c for c in left_cols}
    right_set = {c.lower(): c for c in right_cols}
    suggestions = []
    for lower_name, orig_name in left_set.items():
        if lower_name in right_set:
            suggestions.append({
                'leftKey': orig_name,
                'rightKey': right_set[lower_name]
            })
    return {
        'suggestions': suggestions,
        'leftColumns': left_cols,
        'rightColumns': right_cols
    }
