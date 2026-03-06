# -*- coding: utf-8 -*-
"""
Метаданные таблиц БД по Connection.
"""
from .connection_runner import get_columns
from .models import Connection


def get_connection_table_columns_meta(
    connection: Connection,
    table_name: str,
    schema: str = "public",
):
    """Возвращает список колонок таблицы БД в формате [{ "name", "type", "nullable", "default" }]."""
    return get_columns(connection, table_name, schema)
