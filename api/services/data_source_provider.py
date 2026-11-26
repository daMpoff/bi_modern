# -*- coding: utf-8 -*-
"""
Единый провайдер метаданных для источников данных BI (таблица БД или файл).
Возвращает колонки в едином формате [{ "name", "type" }, ...].
"""
import logging
from typing import Any, Dict, List

from ..bi_connections.models import Connection
from ..bi_datasets.models import FileUpload

logger = logging.getLogger(__name__)


def get_columns_meta(
    connection_id: int,
    main_table: Dict[str, Any],
    user,
) -> List[Dict[str, str]]:
    """
    Возвращает список колонок источника в формате [{ "name": str, "type": str }, ...].
    Источник определяется по main_table: при наличии file_id — файл, иначе таблица БД.
    """
    main_table = main_table or {}
    file_id = main_table.get("file_id") or main_table.get("file_upload_id")
    if file_id is not None:
        return _get_file_columns_meta(file_id, user)
    return _get_table_columns_meta(connection_id, main_table, user)


def _get_file_columns_meta(file_id: int, user) -> List[Dict[str, str]]:
    try:
        fu = FileUpload.objects.get(pk=file_id, owner=user)
    except FileUpload.DoesNotExist:
        logger.warning("FileUpload %s not found for user", file_id)
        return []
    info = fu.columns_info or {}
    columns = info.get("columns")
    if not columns or not isinstance(columns, list):
        return []
    types = info.get("types")
    if not isinstance(types, list):
        types = []
    return [
        {"name": str(c), "type": types[i] if i < len(types) else "string"}
        for i, c in enumerate(columns)
    ]


def _get_table_columns_meta(
    connection_id: int,
    main_table: Dict[str, Any],
    user,
) -> List[Dict[str, str]]:
    try:
        conn = Connection.objects.get(pk=connection_id, owner=user)
    except Connection.DoesNotExist:
        logger.warning("Connection %s not found for user", connection_id)
        return []
    table_name = main_table.get("name") or main_table.get("table")
    if not table_name:
        return []
    schema = main_table.get("schema") or "public"
    from ..bi_connections.meta import get_connection_table_columns_meta
    rows = get_connection_table_columns_meta(conn, table_name, schema)
    return [{"name": r["name"], "type": r.get("type") or "string"} for r in rows]
