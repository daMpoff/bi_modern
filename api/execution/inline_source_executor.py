# -*- coding: utf-8 -*-
"""
Выполнение inline-источника данных (без создания Dataset).
Поддерживает:
- БД подключения (PostgreSQL, MSSQL, ClickHouse)
- Файловые источники (CSV, XLSX)
Источник возвращает только одну таблицу/файл. Связи — через блок «Соединение» в пайплайне.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from ..bi_connections.models import Connection

try:
    import polars as pl
except ImportError:
    pl = None
from ..bi_connections.connection_runner import (
    execute_sql,
    execute_sql_columnar,
    get_connection_db_type,
)
from ..bi_datasets.models import FileUpload

logger = logging.getLogger(__name__)


def execute_inline_source(
    connection_id: int,
    main_table: Dict[str, Any],
    relations: List[Dict[str, Any]] = None,
    user=None,
    limit: Optional[int] = None,
    return_dataframe: bool = False,
    pushdown_filter: Optional[Dict[str, Any]] = None,
    pushdown_aggregation: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Выполняет запрос к inline-источнику данных (одна таблица/файл)."""
    try:
        conn = Connection.objects.get(pk=connection_id, owner=user)
    except Connection.DoesNotExist:
        raise ValueError(f"Подключение {connection_id} не найдено для пользователя {user}")

    conn_type = get_connection_db_type(conn)

    if conn_type in ('file', 'files', 'файл', 'файлы') or 'file' in conn_type:
        return _execute_file_source(conn, main_table, [], user, limit, return_dataframe)
    if conn_type not in ('postgresql', 'mssql', 'clickhouse'):
        raise ValueError(f"Неподдерживаемый тип подключения: {conn_type}")
    return _execute_db_source(
        conn, main_table, [], limit, return_dataframe,
        pushdown_filter, pushdown_aggregation, params or {}, conn_type,
    )


def _read_file_direct_polars(file_upload_id: int) -> Any:
    """
    Читает файл в Polars LazyFrame для ленивого выполнения.
    Polars сам применит predicate/projection pushdown при collect().
    Для .bin (Arrow IPC) — scan_ipc (lazy).
    Для CSV/TXT — scan_csv (lazy).
    Для XLSX — read_excel (eager) -> .lazy().
    """
    from ..bi_datasets.binary_storage import is_binary_file

    try:
        upload = FileUpload.objects.get(pk=file_upload_id)
    except FileUpload.DoesNotExist:
        raise ValueError(f"FileUpload с id={file_upload_id} не найден")

    if not upload.file:
        raise ValueError(f"FileUpload {file_upload_id} не имеет файла")

    path = upload.file.path

    if is_binary_file(path) or upload.file_type == 'bin':
        return _read_ipc_native_lazy(path)

    if upload.file_type == 'xlsx':
        df = pl.read_excel(path, sheet_index=0)
        return df.lazy()

    if upload.file_type in ('csv', 'txt'):
        try:
            return pl.scan_csv(path, encoding='utf8', try_parse_dates=True)
        except Exception:
            return pl.scan_csv(path, encoding='cp1251', try_parse_dates=True)

    from ..services.services import read_file_to_dataframe
    table_data = read_file_to_dataframe(file_upload_id, row_limit=None)
    df = _table_data_to_dataframe(table_data)
    if df is not None and hasattr(df, 'lazy'):
        return df.lazy()
    return df


def _read_ipc_native_lazy(path: str) -> Any:
    """Читает Arrow IPC (.bin) в Polars LazyFrame."""
    try:
        lf = pl.scan_ipc(path)
        return _clean_nan_lazy(lf)
    except (AttributeError, Exception):
        try:
            df = pl.read_ipc(path, memory_map=False)
        except Exception:
            df = pl.read_ipc(path)
        return _clean_nan_lazy(df.lazy())


def _read_ipc_native(path: str) -> Any:
    """Читает Arrow IPC (.bin) в Polars DataFrame (обратная совместимость)."""
    lf = _read_ipc_native_lazy(path)
    if isinstance(lf, pl.LazyFrame):
        return lf.collect()
    return lf


def _clean_nan_lazy(lf: Any) -> Any:
    """Заменяет NaN/Inf на null в float-колонках. Работает и с LazyFrame, и с DataFrame."""
    if lf is None:
        return pl.LazyFrame()
    try:
        schema = lf.collect_schema() if isinstance(lf, pl.LazyFrame) else lf.schema
        float_cols = [c for c, dt in schema.items() if dt in (pl.Float32, pl.Float64)]
    except Exception:
        return lf
    if not float_cols:
        return lf
    return lf.with_columns([
        pl.when(pl.col(c).is_nan() | pl.col(c).is_infinite())
        .then(None)
        .otherwise(pl.col(c))
        .alias(c)
        for c in float_cols
    ])


def _clean_nan_polars(df: Any) -> Any:
    """Заменяет NaN/Inf на null в float-колонках — обратная совместимость (eager)."""
    if df is None:
        return pl.DataFrame()
    if isinstance(df, pl.LazyFrame):
        return _clean_nan_lazy(df).collect()
    if hasattr(df, 'is_empty') and df.is_empty():
        return df
    float_cols = [c for c in df.columns if df[c].dtype in (pl.Float32, pl.Float64)]
    if not float_cols:
        return df
    return df.with_columns([
        pl.when(pl.col(c).is_nan() | pl.col(c).is_infinite())
        .then(None)
        .otherwise(pl.col(c))
        .alias(c)
        for c in float_cols
    ])


def _table_data_to_dataframe(table: Any) -> Any:
    """Конвертирует TableData в polars DataFrame (column-oriented)."""
    if pl is None:
        return None
    from ..services.services import TableData
    if isinstance(table, TableData):
        if not table.columns or not table.rows:
            return pl.DataFrame()
        col_data = {}
        for col_idx, col in enumerate(table.columns):
            col_data[col] = [
                row[col_idx] if col_idx < len(row) else None
                for row in table.rows
            ]
        return pl.DataFrame(col_data)
    if hasattr(table, 'to_dicts') and callable(getattr(table, 'head', None)):
        return table
    return None


def _execute_file_source(
    conn: Connection,
    main_table: Dict[str, Any],
    relations: List[Dict[str, Any]],
    user,
    limit: Optional[int],
    return_dataframe: bool = False,
) -> Any:
    """Выполнение запроса к файловым источникам через polars. Возвращает LazyFrame."""
    if pl is None:
        raise ImportError("polars не установлен, невозможно прочитать файловый источник")

    main_file_id = main_table.get('file_id')
    if not main_file_id:
        raise ValueError("file_id не указан для главной таблицы")

    try:
        FileUpload.objects.get(pk=main_file_id, connection=conn, owner=user)
    except FileUpload.DoesNotExist as exc:
        raise ValueError('Файл не найден в выбранном подключении') from exc

    result_lf = _read_file_direct_polars(main_file_id)

    if result_lf is None:
        logger.warning("Файл %s не содержит данных", main_file_id)
        return []

    if isinstance(result_lf, pl.DataFrame):
        result_lf = result_lf.lazy()

    for rel in relations:
        right_file_id = rel.get('file_id')
        if not right_file_id:
            continue

        try:
            from ..services.services import read_file_to_dataframe
            right_table_data = read_file_to_dataframe(right_file_id, row_limit=None)
            if right_table_data is None or len(right_table_data) == 0:
                continue
            right_df = _table_data_to_dataframe(right_table_data)
            if right_df is None:
                continue
            right_lf = right_df.lazy() if isinstance(right_df, pl.DataFrame) else right_df
        except Exception as e:
            logger.warning("Ошибка чтения файла %s: %s", right_file_id, e)
            continue

        left_col = rel.get('left_column')
        right_col = rel.get('right_column')
        join_type = (rel.get('joinType') or 'LEFT JOIN').upper()

        if not left_col or not right_col:
            continue

        how = 'left'
        if 'INNER' in join_type:
            how = 'inner'
        elif 'RIGHT' in join_type:
            result_lf, right_lf = right_lf, result_lf
            left_col, right_col = right_col, left_col
            how = 'left'
        elif 'FULL' in join_type:
            how = 'outer'

        result_lf = result_lf.join(
            right_lf,
            left_on=left_col,
            right_on=right_col,
            how=how,
            suffix='_right',
        )

    if limit:
        result_lf = result_lf.head(limit)

    if return_dataframe:
        return result_lf
    from .pipeline_types import collect_result
    return collect_result(result_lf).to_dicts()


def _execute_db_source(
    conn: Connection,
    main_table: Dict[str, Any],
    relations: List[Dict[str, Any]],
    limit: Optional[int],
    return_dataframe: bool = False,
    pushdown_filter: Optional[Dict[str, Any]] = None,
    pushdown_aggregation: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    dialect: str = 'postgresql',
) -> Any:
    """Единый метод выполнения SQL запроса к БД с column-oriented загрузкой в Polars.
    Возвращает LazyFrame (через .lazy()) для дальнейшей lazy-обработки."""
    try:
        query, bind_params = _build_sql_query(
            main_table, relations, limit, dialect=dialect,
            pushdown_filter=pushdown_filter, pushdown_aggregation=pushdown_aggregation,
            params=params or {},
        )

        if return_dataframe and pl is not None:
            col_data = execute_sql_columnar(conn, query, bind_params or {})
            if not col_data:
                return pl.LazyFrame()
            return pl.DataFrame(col_data).lazy()

        rows = execute_sql(conn, query, bind_params or {})
        return rows
    except Exception as e:
        logger.exception("Ошибка выполнения %s запроса", dialect)
        raise ValueError('Не удалось выполнить запрос к источнику данных') from e


def _resolve_param(value: Any, params: Dict[str, Any]) -> Any:
    """Подставляет $param_name из params."""
    if isinstance(value, str) and value.strip().startswith('$'):
        name = value.strip()[1:].strip()
        return params.get(name) if name else value
    return value


def _sql_value_literal(val: Any, dialect: str) -> str:
    """Безопасное представление значения для SQL."""
    if val is None:
        return 'NULL'
    if isinstance(val, bool):
        return '1' if val else '0'
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"


def _build_sql_query(
    main_table: Dict[str, Any],
    relations: List[Dict[str, Any]],
    limit: Optional[int],
    dialect: str = 'postgresql',
    pushdown_filter: Optional[Dict[str, Any]] = None,
    pushdown_aggregation: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Построение SQL запроса с JOIN'ами, опционально WHERE и GROUP BY.
    Возвращает (query_str, bind_params).
    """
    params = params or {}
    bind_params: Dict[str, Any] = {}

    def quote_id(name: str) -> str:
        if not isinstance(name, str) or not name:
            raise ValueError('Не задано имя таблицы или поля')
        if dialect == 'mssql':
            return '[' + name.replace(']', ']]') + ']'
        elif dialect == 'clickhouse':
            return '`' + name.replace('`', '``') + '`'
        else:
            return '"' + name.replace('"', '""') + '"'

    main_name = main_table.get('name') or main_table.get('table')
    main_schema = main_table.get('schema')

    if main_schema:
        main_ref = f'{quote_id(main_schema)}.{quote_id(main_name)}'
    else:
        main_ref = quote_id(main_name)

    main_alias = 'a'
    query_parts = [f'SELECT {main_alias}.*']
    from_clause = f'FROM {main_ref} AS {main_alias}'

    join_clauses = []
    for idx, rel in enumerate(relations):
        right_name = rel.get('rightTableName')
        right_schema = rel.get('rightTableSchema')
        left_col = rel.get('left_column')
        right_col = rel.get('right_column')
        join_type = (rel.get('joinType') or 'LEFT JOIN').upper()

        if not right_name or not left_col or not right_col:
            continue

        if right_schema:
            right_ref = f'{quote_id(right_schema)}.{quote_id(right_name)}'
        else:
            right_ref = quote_id(right_name)

        right_alias = f't{idx + 1}'

        if 'INNER' in join_type:
            join_keyword = 'INNER JOIN'
        elif 'RIGHT' in join_type:
            join_keyword = 'RIGHT JOIN'
        elif 'FULL' in join_type:
            join_keyword = 'FULL OUTER JOIN'
        else:
            join_keyword = 'LEFT JOIN'

        join_clause = (
            f'{join_keyword} {right_ref} AS {right_alias} '
            f'ON {main_alias}.{quote_id(left_col)} = {right_alias}.{quote_id(right_col)}'
        )
        join_clauses.append(join_clause)
        query_parts[0] = query_parts[0].rstrip('*') + f'*, {right_alias}.*'

    where_clauses = []
    if pushdown_filter:
        conditions = pushdown_filter.get('conditions') or []
        for i, cond in enumerate(conditions):
            field = cond.get('field')
            op = (cond.get('operator') or '=').lower()
            raw_val = cond.get('value')
            val = _resolve_param(raw_val, params)
            if not field:
                continue
            col = quote_id(field)
            pref = f'{main_alias}.{col}'
            if op == 'isnull':
                where_clauses.append(f'{pref} IS NULL')
            elif op == 'notnull':
                where_clauses.append(f'{pref} IS NOT NULL')
            elif op in ('=', '=='):
                if dialect == 'clickhouse':
                    where_clauses.append(f'{pref} = {_sql_value_literal(val, dialect)}')
                else:
                    key = f'w{i}'
                    bind_params[key] = val
                    where_clauses.append(f'{pref} = :{key}')
            elif op in ('!=', '<>'):
                if dialect == 'clickhouse':
                    where_clauses.append(f'{pref} <> {_sql_value_literal(val, dialect)}')
                else:
                    key = f'w{i}'
                    bind_params[key] = val
                    where_clauses.append(f'{pref} <> :{key}')
            elif op in ('>', '>=', '<', '<='):
                if dialect == 'clickhouse':
                    where_clauses.append(f'{pref} {op} {_sql_value_literal(val, dialect)}')
                else:
                    key = f'w{i}'
                    bind_params[key] = val
                    where_clauses.append(f'{pref} {op} :{key}')
            elif op == 'between' and val is not None:
                mn = _resolve_param(
                    val.get('min') if isinstance(val, dict)
                    else (val[0] if isinstance(val, (list, tuple)) and len(val) >= 2 else None),
                    params,
                )
                mx = _resolve_param(
                    val.get('max') if isinstance(val, dict)
                    else (val[1] if isinstance(val, (list, tuple)) and len(val) >= 2 else None),
                    params,
                )
                if dialect == 'clickhouse':
                    where_clauses.append(
                        f'{pref} BETWEEN {_sql_value_literal(mn, dialect)} AND {_sql_value_literal(mx, dialect)}'
                    )
                else:
                    k1, k2 = f'w{i}a', f'w{i}b'
                    bind_params[k1], bind_params[k2] = mn, mx
                    where_clauses.append(f'{pref} BETWEEN :{k1} AND :{k2}')

    group_by_cols = []
    agg_select = []
    if pushdown_aggregation:
        group_by = pushdown_aggregation.get('groupBy') or []
        aggs = pushdown_aggregation.get('aggregations') or []
        for f in group_by:
            group_by_cols.append(f'{main_alias}.{quote_id(f)}')
        for agg in aggs:
            field = agg.get('field')
            fn = (agg.get('agg') or 'count').lower()
            out = (agg.get('outputName') or f'{field or "count"}_{fn}').strip()
            col = f'{main_alias}.{quote_id(field)}' if field else '1'
            if fn == 'count':
                agg_select.append(f'COUNT(*) AS {quote_id(out)}')
            elif fn == 'sum':
                agg_select.append(f'SUM({col}) AS {quote_id(out)}')
            elif fn == 'avg':
                agg_select.append(f'AVG({col}) AS {quote_id(out)}')
            elif fn == 'min':
                agg_select.append(f'MIN({col}) AS {quote_id(out)}')
            elif fn == 'max':
                agg_select.append(f'MAX({col}) AS {quote_id(out)}')
            elif fn == 'ucount':
                agg_select.append(f'COUNT(DISTINCT {col}) AS {quote_id(out)}')
            else:
                agg_select.append(f'COUNT(*) AS {quote_id(out)}')

    query = f'{query_parts[0]} {from_clause}'
    if join_clauses:
        query += ' ' + ' '.join(join_clauses)
    if where_clauses:
        query += ' WHERE ' + ' AND '.join(where_clauses)
    if agg_select:
        query = f'SELECT {", ".join(group_by_cols + agg_select)} {from_clause}'
        if join_clauses:
            query += ' ' + ' '.join(join_clauses)
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
        if group_by_cols:
            query += ' GROUP BY ' + ', '.join(group_by_cols)
    if limit:
        if dialect == 'mssql':
            query = query.replace('SELECT ', f'SELECT TOP {limit} ', 1)
        else:
            query += f' LIMIT {limit}'
    return (query, bind_params)
