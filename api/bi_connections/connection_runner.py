# -*- coding: utf-8 -*-
"""
Единый слой доступа к БД по пользовательскому Connection.
Строит engine/client из connection.config, предоставляет get_tables, get_columns, execute_sql.
Кэширование движков для повторного использования соединений.
"""
import logging
import threading
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text

from .models import Connection

logger = logging.getLogger(__name__)

_engine_cache: Dict[str, Any] = {}
_engine_lock = threading.Lock()
_ENGINE_POOL_SIZE = 5
_ENGINE_POOL_RECYCLE = 300


def _get_cached_engine(url: str):
    """Возвращает кэшированный SQLAlchemy engine или создаёт новый."""
    if url in _engine_cache:
        return _engine_cache[url]
    with _engine_lock:
        if url in _engine_cache:
            return _engine_cache[url]
        engine = create_engine(
            url,
            pool_size=_ENGINE_POOL_SIZE,
            pool_recycle=_ENGINE_POOL_RECYCLE,
            pool_pre_ping=True,
        )
        _engine_cache[url] = engine
        return engine


def get_connection_db_type(connection: Connection) -> str:
    """Нормализованный тип СУБД: postgresql, mssql, clickhouse."""
    raw = (connection.connector_type or "").lower().strip()
    if raw in ("postgresql", "postgres"):
        return "postgresql"
    if raw in ("mssql", "sql server"):
        return "mssql"
    if raw == "clickhouse":
        return "clickhouse"
    return raw


def _cfg(connection: Connection) -> Dict[str, Any]:
    return connection.config or {}


def _pg_url(connection: Connection) -> str:
    c = _cfg(connection)
    user = c.get("user") or c.get("username")
    password = c.get("password")
    host = c.get("host")
    port = c.get("port", 5432)
    db = c.get("database")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _mssql_url(connection: Connection) -> str:
    c = _cfg(connection)
    user = c.get("user") or c.get("username")
    password = c.get("password")
    host = c.get("host")
    port = c.get("port", 1433)
    db = c.get("database")
    return f"mssql+pyodbc://{user}:{password}@{host},{port}/{db}?driver=ODBC+Driver+17+for+SQL+Server"


def _pg_engine(connection: Connection):
    return _get_cached_engine(_pg_url(connection))


def _mssql_engine(connection: Connection):
    return _get_cached_engine(_mssql_url(connection))


def get_tables(connection: Connection) -> List[Dict[str, str]]:
    """Список таблиц: [{ name, schema }, ...]."""
    db_type = get_connection_db_type(connection)
    if db_type == "postgresql":
        return _get_postgresql_tables(connection)
    if db_type == "mssql":
        return _get_mssql_tables(connection)
    if db_type == "clickhouse":
        return _get_clickhouse_tables(connection)
    return []


def _get_postgresql_tables(connection: Connection) -> List[Dict[str, str]]:
    engine = _pg_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')"
        ))
        return [{"name": row.table_name, "schema": row.table_schema} for row in result]


def _get_mssql_tables(connection: Connection) -> List[Dict[str, str]]:
    engine = _mssql_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        ))
        return [{"name": row.TABLE_NAME, "schema": row.TABLE_SCHEMA} for row in result]


def _get_clickhouse_tables(connection: Connection) -> List[Dict[str, str]]:
    import clickhouse_connect
    c = _cfg(connection)
    client = clickhouse_connect.get_client(
        host=c.get("host"),
        port=int(c.get("port", 8443)),
        username=c.get("user") or c.get("username"),
        password=c.get("password"),
        database=c.get("database"),
    )
    result = client.query("SHOW TABLES")
    db_name = c.get("database") or ""
    return [{"name": row[0], "schema": db_name} for row in result.result_rows]


def get_columns(
    connection: Connection,
    table_name: str,
    schema: str = "public",
) -> List[Dict[str, Any]]:
    """Метаданные колонок таблицы: [{ name, type, nullable, default }, ...]."""
    db_type = get_connection_db_type(connection)
    if db_type == "postgresql":
        return _get_postgresql_columns(connection, table_name, schema)
    if db_type == "mssql":
        return _get_mssql_columns(connection, table_name, schema)
    if db_type == "clickhouse":
        return _get_clickhouse_columns(connection, table_name)
    return []


def _get_postgresql_columns(
    connection: Connection,
    table_name: str,
    schema: str,
) -> List[Dict[str, Any]]:
    engine = _pg_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table_name "
            "ORDER BY ordinal_position"
        ), {"schema": schema, "table_name": table_name})
        return [{
            "name": row.column_name,
            "type": row.data_type,
            "nullable": row.is_nullable == "YES",
            "default": row.column_default,
        } for row in result]


def _get_mssql_columns(
    connection: Connection,
    table_name: str,
    schema: str,
) -> List[Dict[str, Any]]:
    engine = _mssql_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table_name "
            "ORDER BY ORDINAL_POSITION"
        ), {"schema": schema, "table_name": table_name})
        return [{
            "name": row.COLUMN_NAME,
            "type": row.DATA_TYPE,
            "nullable": row.IS_NULLABLE == "YES",
            "default": row.COLUMN_DEFAULT,
        } for row in result]


def _get_clickhouse_columns(connection: Connection, table_name: str) -> List[Dict[str, Any]]:
    import clickhouse_connect
    c = _cfg(connection)
    client = clickhouse_connect.get_client(
        host=c.get("host"),
        port=int(c.get("port", 8443)),
        username=c.get("user") or c.get("username"),
        password=c.get("password"),
        database=c.get("database"),
    )
    result = client.query(f"DESCRIBE TABLE {table_name}")
    return [{
        "name": row[0],
        "type": row[1],
        "nullable": "Nullable" in row[1] if len(row) > 1 else False,
        "default": row[2] if len(row) > 2 else None,
    } for row in result.result_rows]


def _rows_to_column_dict(columns: List[str], raw_rows: list) -> Dict[str, list]:
    """Column-oriented construction: транспонирует строки в словарь колонок."""
    col_data: Dict[str, list] = {col: [] for col in columns}
    for row in raw_rows:
        for i, col in enumerate(columns):
            col_data[col].append(row[i] if i < len(row) else None)
    return col_data


def execute_sql(
    connection: Connection,
    query: str,
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Выполнить SQL и вернуть строки как list of dict.
    params -- для биндинга (postgres/mssql); clickhouse не поддерживает params в query().
    """
    db_type = get_connection_db_type(connection)
    params = params or {}
    if db_type == "postgresql":
        return _execute_postgresql(connection, query, params)
    if db_type == "mssql":
        return _execute_mssql(connection, query, params)
    if db_type == "clickhouse":
        return _execute_clickhouse(connection, query)
    return []


def execute_sql_columnar(
    connection: Connection,
    query: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, list]:
    """
    Выполнить SQL и вернуть результат в column-oriented формате.
    Возвращает { col_name: [values...], ... }.
    """
    db_type = get_connection_db_type(connection)
    params = params or {}
    if db_type == "postgresql":
        return _execute_postgresql_columnar(connection, query, params)
    if db_type == "mssql":
        return _execute_mssql_columnar(connection, query, params)
    if db_type == "clickhouse":
        return _execute_clickhouse_columnar(connection, query)
    return {}


def _execute_postgresql(
    connection: Connection,
    query: str,
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    engine = _pg_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


def _execute_postgresql_columnar(
    connection: Connection,
    query: str,
    params: Dict[str, Any],
) -> Dict[str, list]:
    engine = _pg_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        columns = list(result.keys())
        raw_rows = result.fetchall()
        return _rows_to_column_dict(columns, raw_rows)


def _execute_mssql(
    connection: Connection,
    query: str,
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    engine = _mssql_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


def _execute_mssql_columnar(
    connection: Connection,
    query: str,
    params: Dict[str, Any],
) -> Dict[str, list]:
    engine = _mssql_engine(connection)
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        columns = list(result.keys())
        raw_rows = result.fetchall()
        return _rows_to_column_dict(columns, raw_rows)


def _execute_clickhouse(connection: Connection, query: str) -> List[Dict[str, Any]]:
    import clickhouse_connect
    c = _cfg(connection)
    client = clickhouse_connect.get_client(
        host=c.get("host"),
        port=int(c.get("port", 8443)),
        username=c.get("user") or c.get("username"),
        password=c.get("password"),
        database=c.get("database"),
    )
    result = client.query(query)
    columns = result.column_names
    return [dict(zip(columns, row)) for row in result.result_rows]


def _execute_clickhouse_columnar(connection: Connection, query: str) -> Dict[str, list]:
    import clickhouse_connect
    c = _cfg(connection)
    client = clickhouse_connect.get_client(
        host=c.get("host"),
        port=int(c.get("port", 8443)),
        username=c.get("user") or c.get("username"),
        password=c.get("password"),
        database=c.get("database"),
    )
    result = client.query(query)
    columns = result.column_names
    return _rows_to_column_dict(columns, result.result_rows)


def get_table_preview(
    connection: Connection,
    table_name: str,
    schema: str = "public",
    limit: int = 200,
    offset: int = 0,
) -> Dict[str, Any]:
    """Возвращает { columns, rows, has_more, total_count }."""
    db_type = get_connection_db_type(connection)
    if db_type == "postgresql":
        return _get_postgresql_table_preview(connection, table_name, schema, limit, offset)
    if db_type == "mssql":
        return _get_mssql_table_preview(connection, table_name, schema, limit, offset)
    if db_type == "clickhouse":
        return _get_clickhouse_table_preview(connection, table_name, limit, offset)
    return {"columns": [], "rows": [], "has_more": False, "total_count": 0}


def _get_postgresql_table_preview(
    connection: Connection,
    table_name: str,
    schema: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    cols = get_columns(connection, table_name, schema)
    columns = [c["name"] for c in cols]
    if not columns:
        return {"columns": [], "rows": [], "has_more": False, "total_count": 0}
    q_count = f'SELECT COUNT(*) FROM "{schema}"."{table_name}"'
    count_rows = execute_sql(connection, q_count)
    total_count = list(count_rows[0].values())[0] if count_rows else 0
    quoted = ", ".join(f'"{c}"' for c in columns)
    q_data = f'SELECT {quoted} FROM "{schema}"."{table_name}" LIMIT :limit OFFSET :offset'
    rows_dicts = execute_sql(connection, q_data, {"limit": limit, "offset": offset})
    rows = [[r.get(col) for col in columns] for r in rows_dicts]
    return {
        "columns": columns,
        "rows": rows,
        "has_more": offset + len(rows) < total_count,
        "total_count": total_count,
    }


def _get_mssql_table_preview(
    connection: Connection,
    table_name: str,
    schema: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    cols = get_columns(connection, table_name, schema)
    columns = [c["name"] for c in cols]
    if not columns:
        return {"columns": [], "rows": [], "has_more": False, "total_count": 0}
    q_count = f"SELECT COUNT(*) FROM [{schema}].[{table_name}]"
    count_rows = execute_sql(connection, q_count)
    total_count = list(count_rows[0].values())[0] if count_rows else 0
    quoted = ", ".join(f"[{c}]" for c in columns)
    q_data = (
        f"SELECT {quoted} FROM [{schema}].[{table_name}] "
        "ORDER BY (SELECT NULL) OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
    )
    rows_dicts = execute_sql(connection, q_data, {"limit": limit, "offset": offset})
    rows = [[r.get(col) for col in columns] for r in rows_dicts]
    return {
        "columns": columns,
        "rows": rows,
        "has_more": offset + len(rows) < total_count,
        "total_count": total_count,
    }


def _get_clickhouse_table_preview(
    connection: Connection,
    table_name: str,
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    cols = get_columns(connection, table_name, "")
    columns = [c["name"] for c in cols]
    if not columns:
        return {"columns": [], "rows": [], "has_more": False, "total_count": 0}
    count_rows = execute_sql(connection, f"SELECT COUNT(*) FROM `{table_name}`")
    total_count = list(count_rows[0].values())[0] if count_rows else 0
    rows_dicts = execute_sql(
        connection,
        f"SELECT * FROM `{table_name}` LIMIT {limit} OFFSET {offset}",
    )
    rows = [[r.get(col) for col in columns] for r in rows_dicts]
    return {
        "columns": columns,
        "rows": rows,
        "has_more": offset + len(rows) < total_count,
        "total_count": total_count,
    }
