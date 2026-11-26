import csv
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from math import isnan, isinf
import math
from itertools import islice
from typing import List, Optional, Tuple

from django.db import connection, transaction, models
from rest_framework.exceptions import ValidationError
from psycopg2 import sql
from openpyxl import load_workbook
import logging

from ..bi_datasets.models import FileUpload
from ..bi_datasets.binary_storage import is_binary_file, read_from_binary

logger = logging.getLogger(__name__)


class TableData:
    __slots__ = ('columns', 'rows')

    def __init__(self, columns, rows):
        self.columns = columns or []
        self.rows = rows or []

    def __len__(self):
        return len(self.rows)

    def limited(self, limit):
        if limit is None or limit <= 0 or len(self.rows) <= limit:
            return self
        return TableData(self.columns, self.rows[:limit])


def introspect_columns(table_name):
    """Возвращает список имён колонок таблицы в БД по умолчанию (Django connection)."""
    with connection.cursor() as cursor:
        if '.' in table_name:
            schema, table = table_name.split('.', 1)
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                [schema, table],
            )
        else:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
                [table_name],
            )
        return [row[0] for row in cursor.fetchall()]


def _normalize_header(header):
    if not header:
        return []
    normalized = []
    for col in header:
        if col is None:
            normalized.append('')
        else:
            normalized.append(str(col))
    return normalized


def _ensure_row(values, expected_len):
    row = list(values or [])
    if expected_len and len(row) < expected_len:
        row.extend([None] * (expected_len - len(row)))
    elif expected_len and len(row) > expected_len:
        row = row[:expected_len]
    return row


def _is_null(val):
    if val is None:
        return True
    if isinstance(val, float):
        return isnan(val)
    return False


def _sanitize_value(value):
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def _sanitize_rows(rows: List[List[object]]) -> List[List[object]]:
    sanitized = []
    for row in rows:
        sanitized.append([_sanitize_value(val) for val in row])
    return sanitized


@contextmanager
def _excel_rows(path, sheet_name=None):
    workbook = load_workbook(filename=path, read_only=True, data_only=True)
    try:
        sheets = workbook.sheetnames
        if sheet_name and sheet_name not in sheets:
            raise ValidationError(f"Лист '{sheet_name}' не найден в файле")
        sheet = workbook[sheet_name or sheets[0]] if sheets else None
        yield (sheet.iter_rows(values_only=True) if sheet is not None else iter(())), sheets
    finally:
        workbook.close()


def _read_excel_table(path, sheet_name=None, row_limit=None):
    with _excel_rows(path, sheet_name) as (rows, _):
        columns = _normalize_header(next(rows, None))
        return TableData(columns, [_ensure_row(row, len(columns)) for row in islice(rows, row_limit)])


def _read_csv_table(path, row_limit=None, encoding='cp1251'):
    with open(path, 'r', encoding=encoding, errors='replace', newline='') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        columns = _normalize_header(header)

        if row_limit == 0:
            return TableData(columns, [])

        rows = []
        for row in reader:
            rows.append(_ensure_row(row, len(columns)))
            if row_limit and row_limit > 0 and len(rows) >= row_limit:
                break

    return TableData(columns, rows)


def count_file_rows(file_upload_id, sheet_name=None):
    """Подсчитывает общее количество строк в файле без загрузки всех данных."""
    try:
        upload = FileUpload.objects.get(pk=file_upload_id)
    except FileUpload.DoesNotExist:
        raise ValidationError(f"FileUpload с id={file_upload_id} не найден")

    if not upload.file:
        raise ValidationError(f"FileUpload {file_upload_id} не имеет файла")

    path = upload.file.path

    if is_binary_file(path) or upload.file_type == 'bin':
        try:
            import polars as pl
            lazy_frame = pl.scan_ipc(path)
            agg_df = lazy_frame.select(pl.len()).collect(streaming=True)  # type: ignore[arg-type]
            return int(agg_df.to_series(0)[0])
        except Exception as e:
            logger.error(f"Ошибка чтения бинарного файла для подсчёта: {str(e)}")
            raise ValidationError(f"Ошибка чтения бинарного файла: {str(e)}")

    if upload.file_type == 'xlsx':
        sheet = sheet_name or getattr(upload, 'sheet_name', None)
        with _excel_rows(path, sheet) as (rows, _):
            next(rows, None)
            return sum(1 for _ in rows)

    try:
        import polars as pl
        if upload.file_type in ('csv', 'txt'):
            try:
                lazy_csv = pl.scan_csv(path)
            except Exception:
                lazy_csv = pl.scan_csv(path, encoding='cp1251')
            agg_df = lazy_csv.select(pl.len()).collect(streaming=True)  # type: ignore[arg-type]
            return int(agg_df.to_series(0)[0])
        else:
            raise ValidationError(f"Неподдерживаемый тип файла: {upload.file_type}")

    except ImportError:
        logger.warning("Polars недоступен для подсчёта строк, используется fallback метод")
        table_data = read_file_to_dataframe(file_upload_id, sheet_name, row_limit=1000000)
        return len(table_data.rows)
    except Exception as e:
        logger.warning(f"Ошибка подсчёта строк через polars: {str(e)}, используется fallback")
        table_data = read_file_to_dataframe(file_upload_id, sheet_name, row_limit=1000000)
        return len(table_data.rows)


def read_file_to_dataframe(file_upload_id, sheet_name=None, row_limit=None, use_polars=True):
    """Читает файл в табличную структуру."""
    try:
        upload = FileUpload.objects.get(pk=file_upload_id)
    except FileUpload.DoesNotExist:
        raise ValidationError(f"FileUpload с id={file_upload_id} не найден")

    if not upload.file:
        raise ValidationError(f"FileUpload {file_upload_id} не имеет файла")

    path = upload.file.path

    if is_binary_file(path) or upload.file_type == 'bin':
        try:
            columns, rows = read_from_binary(path, row_limit=row_limit)
            return TableData(columns, rows)
        except Exception as e:
            logger.error(f"Ошибка чтения бинарного файла: {str(e)}")
            raise ValidationError(f"Ошибка чтения бинарного файла: {str(e)}")

    if upload.file_type == 'xlsx':
        sheet = sheet_name or getattr(upload, 'sheet_name', None)
        return _read_excel_table(path, sheet, row_limit=row_limit)

    if use_polars:
        try:
            from ..tasks import _read_file_with_polars
            columns, rows = _read_file_with_polars(file_upload_id, sheet_name, row_limit)
            return TableData(columns, rows)
        except Exception as e:
            logger.warning(f"Не удалось использовать polars, используется fallback метод: {str(e)}")

    if upload.file_type in ('csv', 'txt'):
        return _read_csv_table(path, row_limit=row_limit)
    else:
        raise ValidationError(f"Неподдерживаемый тип файла: {upload.file_type}")


def _resolve_delimiter(delimiter: Optional[str]) -> str:
    if delimiter in (None, ''):
        return ','
    if delimiter == '\\t':
        return '\t'
    return delimiter


def _fallback_csv_slice(
    path: str,
    offset: int,
    limit: Optional[int],
    encoding: str,
    delimiter: str,
) -> Tuple[List[str], List[List[str]]]:
    with open(path, 'r', encoding=encoding, errors='replace', newline='') as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader, [])
        if offset > 0:
            for _ in range(offset):
                next(reader, None)
        if limit is None:
            rows = list(reader)
        else:
            rows = list(islice(reader, limit))
    return header, rows


def read_temp_preview(path, sheet_name, row_limit, has_header):
    """Прочитать заголовок (если есть) и до row_limit строк данных временного файла."""
    extension = Path(path).suffix.lower()
    if extension == '.xlsx':
        with _excel_rows(path, sheet_name) as (rows, _):
            header = next(rows, None) if has_header else None
            parsed = [list(header)] if header is not None else []
            parsed.extend(list(row) for row in islice(rows, row_limit))
            return parsed

    import polars as pl
    if extension in ('.csv', '.txt'):
        try:
            frame = pl.read_csv(path, has_header=has_header, n_rows=row_limit, encoding='utf8', try_parse_dates=True)
        except pl.exceptions.ComputeError:
            frame = pl.read_csv(path, has_header=has_header, n_rows=row_limit, encoding='cp1251', try_parse_dates=True)
    elif extension == '.xls':
        frame = pl.read_excel(path, sheet_name=sheet_name, has_header=has_header)
        if row_limit is not None:
            frame = frame.head(row_limit)
    else:
        raise ValidationError(f"Неподдерживаемый тип файла: {extension}")

    parsed = [frame.columns] if has_header and frame.columns else []
    parsed.extend(list(row) for row in frame.iter_rows())
    return parsed


def read_file_preview_slice(
    upload: FileUpload,
    offset: int,
    limit: Optional[int],
    encoding: str,
    delimiter: str,
    sheet_name: Optional[str],
) -> Tuple[List[str], List[List[object]], Optional[List[str]]]:
    """
    Возвращает срез данных файла с учётом offset/limit.
    Для CSV/TXT и бинарных файлов используется ленивое чтение polars.
    Возвращает кортеж (columns, rows, sheets).
    """
    if offset < 0:
        offset = 0
    path = upload.file.path
    delimiter = _resolve_delimiter(delimiter)

    if is_binary_file(path) or upload.file_type == 'bin':
        columns, rows = read_from_binary(path, row_limit=limit, offset=offset)
        return columns, rows, None

    try:
        import polars as pl
    except ImportError:
        pl = None

    if upload.file_type in ('csv', 'txt'):
        if pl:
            try:
                lazy_csv = pl.scan_csv(
                    path,
                    separator=delimiter,
                    encoding=encoding,
                    try_parse_dates=True,
                )
            except Exception:
                try:
                    lazy_csv = pl.scan_csv(
                        path,
                        separator=delimiter,
                        encoding='cp1251' if encoding.lower() != 'cp1251' else 'utf8',
                        try_parse_dates=True,
                    )
                except Exception:
                    lazy_csv = None
            if lazy_csv is not None:
                if offset or limit is not None:
                    if limit is None:
                        lazy_csv = lazy_csv.slice(offset)
                    else:
                        lazy_csv = lazy_csv.slice(offset, limit)
                df = lazy_csv.collect(streaming=True)  # type: ignore[arg-type]
                columns = list(df.columns)
                rows = _sanitize_rows(df.to_numpy().tolist())
                return columns, rows, None
        header, rows = _fallback_csv_slice(path, offset, limit, encoding, delimiter)
        return header, rows, None

    if upload.file_type == 'xlsx':
        with _excel_rows(path, sheet_name) as (rows, sheets):
            columns = list(next(rows, ()))
            page = islice(rows, offset, None if limit is None else offset + limit)
            return columns, _sanitize_rows(page), sheets

    raise ValidationError(f"Неподдерживаемый тип файла: {upload.file_type}")


def dataframe_to_sql_values(table, table_alias='t0', row_limit=None):
    """Преобразует TableData в SQL (VALUES ...)."""
    if not table.columns:
        return sql.SQL('(SELECT NULL::text AS col WHERE FALSE)'), None

    limited = table

    if len(limited) == 0:
        return sql.SQL('(SELECT NULL::text AS col WHERE FALSE)'), None

    def sanitize(val):
        if _is_null(val):
            return 'NULL'
        if isinstance(val, bool):
            return 'TRUE' if val else 'FALSE'
        if isinstance(val, (int, float)):
            if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
                return 'NULL'
            return str(val)
        val_str = str(val).replace("'", "''")
        return f"'{val_str}'"

    data_rows = []
    for row in limited.rows:
        if not row:
            continue
        sanitized = [sanitize(val) for val in row]
        if sanitized:
            data_rows.append(f"({', '.join(sanitized)})")

    if not data_rows:
        return sql.SQL('(SELECT NULL::text AS col WHERE FALSE)'), None

    col_defs = []
    for col in limited.columns:
        col_name = str(col).replace('"', '""')
        if not col_name:
            col_name = 'column'
        col_defs.append(f'"{col_name}"')

    values_clause = ',\n'.join(data_rows)
    col_list = ', '.join(col_defs)

    values_query = f"""
        (VALUES {values_clause}) AS {table_alias}({col_list})
    """

    return sql.SQL(values_query), None
