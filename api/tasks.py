"""
Celery задачи для асинхронной обработки предпросмотра датасетов.
Использует polars для быстрой обработки файлов с поддержкой чанкинга и параллельной обработки.
"""

import gc
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from celery import shared_task
from django.db import connection
from rest_framework.exceptions import ValidationError

from .bi_datasets.models import FileUpload
from .config import CHUNK_SIZE, MAX_WORKERS
from .services.services import introspect_columns

logger = logging.getLogger(__name__)


def _read_file_with_polars(file_upload_id: int, sheet_name: Optional[str] = None,
                           row_limit: Optional[int] = None,
                           progress_callback=None) -> Tuple[List[str], List[List[Any]]]:
    """
    Читает файл используя polars для максимальной производительности с векторизацией.
    """
    try:
        import polars as pl
    except ImportError:
        logger.warning("Polars не установлен, используется fallback метод")
        from .services.services import read_file_to_dataframe
        table = read_file_to_dataframe(file_upload_id, sheet_name, row_limit)
        return table.columns, table.rows

    try:
        upload = FileUpload.objects.get(pk=file_upload_id)
    except FileUpload.DoesNotExist:
        logger.error(f"FileUpload с id={file_upload_id} не найден")
        raise ValueError(f"FileUpload с id={file_upload_id} не найден")

    if not upload.file:
        logger.error(f"FileUpload {file_upload_id} не имеет файла")
        raise ValueError(f"FileUpload {file_upload_id} не имеет файла")

    path = upload.file.path

    from .bi_datasets.binary_storage import is_binary_file, read_from_binary

    if is_binary_file(path) or upload.file_type == 'bin':
        if progress_callback:
            progress_callback(0.1)
        try:
            columns, rows_list = read_from_binary(path, row_limit=row_limit)
            if progress_callback:
                progress_callback(1.0)
            return columns, rows_list
        except Exception as e:
            logger.error(f"Ошибка чтения бинарного файла {file_upload_id}: {str(e)}")
            raise

    if progress_callback:
        progress_callback(0.1)

    try:
        if upload.file_type == 'xlsx':
            if sheet_name:
                df = pl.read_excel(path, sheet_name=sheet_name)
            else:
                df = pl.read_excel(path, sheet_index=0)

            if progress_callback:
                progress_callback(0.5)

            if row_limit is not None and row_limit > 0:
                df = df.head(row_limit)

            columns = df.columns
            rows_list = df.to_numpy().tolist()

            if progress_callback:
                progress_callback(1.0)

            return list(columns), rows_list

        elif upload.file_type in ('csv', 'txt'):
            file_size = os.path.getsize(path) if os.path.exists(path) else 0
            use_streaming = file_size > 10 * 1024 * 1024 and row_limit is None
            if use_streaming:
                try:
                    lazy = pl.scan_csv(path, encoding='utf8', try_parse_dates=True)
                except Exception:
                    lazy = pl.scan_csv(path, encoding='cp1251', try_parse_dates=True)
                df = lazy.collect(streaming=True)
            else:
                try:
                    df = pl.read_csv(path, encoding='utf8', try_parse_dates=True)
                except Exception:
                    df = pl.read_csv(path, encoding='cp1251', try_parse_dates=True)
                if row_limit is not None and row_limit > 0:
                    df = df.head(row_limit)
            if progress_callback:
                progress_callback(0.5)
            columns = df.columns
            rows_list = df.to_numpy().tolist()

            if progress_callback:
                progress_callback(1.0)

            return list(columns), rows_list
        else:
            raise ValidationError(f"Неподдерживаемый тип файла: {upload.file_type}")

    except Exception as e:
        logger.error(f"Ошибка чтения файла {file_upload_id} с polars: {str(e)}")
        from .services.services import read_file_to_dataframe
        table = read_file_to_dataframe(file_upload_id, sheet_name, row_limit)
        return table.columns, table.rows


def _read_file_chunked(file_upload_id: int, sheet_name: Optional[str] = None,
                      row_limit: Optional[int] = None,
                      progress_callback=None) -> Tuple[List[str], List[List[Any]]]:
    """Читает файл по частям (чанками) для больших файлов с векторизацией."""
    try:
        import polars as pl
    except ImportError:
        return _read_file_with_polars(file_upload_id, sheet_name, row_limit, progress_callback)

    try:
        upload = FileUpload.objects.get(pk=file_upload_id)
    except FileUpload.DoesNotExist:
        raise ValueError(f"FileUpload с id={file_upload_id} не найден")

    if not upload.file:
        raise ValueError(f"FileUpload {file_upload_id} не имеет файла")

    path = upload.file.path
    file_size = os.path.getsize(path)
    estimated_rows = file_size // 100

    try:
        if upload.file_type == 'xlsx':
            if sheet_name:
                df = pl.read_excel(path, sheet_name=sheet_name)
            else:
                df = pl.read_excel(path, sheet_index=0)

            if progress_callback:
                progress_callback(0.3)

            if row_limit and row_limit > 0:
                df = df.head(row_limit)

            if progress_callback:
                progress_callback(0.7)

            columns = df.columns
            rows_list = df.to_numpy().tolist()

            if progress_callback:
                progress_callback(1.0)

            return list(columns), rows_list

        elif upload.file_type in ('csv', 'txt'):
            columns = None
            all_rows = []
            rows_read = 0

            try:
                reader = pl.scan_csv(path, encoding='utf8', try_parse_dates=True)
            except:
                reader = pl.scan_csv(path, encoding='cp1251', try_parse_dates=True)

            schema = reader.schema
            columns = list(schema.keys())

            if progress_callback:
                progress_callback(0.1)

            chunk_count = 0
            for chunk in reader.iter_slices(n_rows=CHUNK_SIZE):
                chunk_df = chunk.collect()
                chunk_rows_list = chunk_df.to_numpy().tolist()

                all_rows.extend(chunk_rows_list)
                rows_read += len(chunk_rows_list)
                chunk_count += 1

                if chunk_count % 10 == 0:
                    del chunk_df
                    gc.collect()

                if progress_callback and estimated_rows > 0:
                    progress = min(0.9, 0.1 + (rows_read / estimated_rows) * 0.8)
                    progress_callback(progress)

                if row_limit and row_limit > 0 and rows_read >= row_limit:
                    all_rows = all_rows[:row_limit]
                    break

            if progress_callback:
                progress_callback(1.0)

            return columns, all_rows
        else:
            return _read_file_with_polars(file_upload_id, sheet_name, row_limit, progress_callback)

    except Exception as e:
        logger.error(f"Ошибка чтения файла {file_upload_id} по чанкам: {str(e)}")
        return _read_file_with_polars(file_upload_id, sheet_name, row_limit, progress_callback)


def _read_files_parallel(file_data_list: List[Dict[str, Any]]) -> List[Tuple[List[str], List[List[Any]]]]:
    """Читает несколько файлов параллельно используя ThreadPoolExecutor."""
    results = [None] * len(file_data_list)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                _read_file_with_polars,
                file_data['file_id'],
                file_data.get('sheet_name'),
                file_data.get('row_limit')
            ): idx
            for idx, file_data in enumerate(file_data_list)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error(f"Ошибка чтения файла {file_data_list[idx]}: {str(e)}")
                results[idx] = ([], [])

    return results


def _read_files_parallel_with_progress(file_data_list: List[Dict[str, Any]],
                                      progress_callback: Optional[Callable[[int, float], None]] = None) -> List[Tuple[List[str], List[List[Any]]]]:
    """Читает несколько файлов параллельно с поддержкой прогресса."""
    results = [None] * len(file_data_list)

    def read_file_with_progress(file_data, file_idx):
        def local_progress_callback(progress):
            if progress_callback:
                progress_callback(file_idx, progress)

        try:
            try:
                upload = FileUpload.objects.get(pk=file_data['file_id'])
            except FileUpload.DoesNotExist:
                return ([], [])

            if not upload.file:
                return ([], [])

            file_size = os.path.getsize(upload.file.path)
            use_chunked = file_size > 10 * 1024 * 1024

            if use_chunked:
                return _read_file_chunked(
                    file_data['file_id'],
                    file_data.get('sheet_name'),
                    file_data.get('row_limit'),
                    local_progress_callback
                )
            else:
                return _read_file_with_polars(
                    file_data['file_id'],
                    file_data.get('sheet_name'),
                    file_data.get('row_limit'),
                    local_progress_callback
                )
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_data}: {str(e)}")
            return ([], [])

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(read_file_with_progress, file_data, idx): idx
            for idx, file_data in enumerate(file_data_list)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
                gc.collect()
            except Exception as e:
                logger.error(f"Ошибка чтения файла {file_data_list[idx]}: {str(e)}")
                results[idx] = ([], [])
                gc.collect()

    return results


@shared_task(bind=True, name='modules.bi_analysis_modern.api.tasks.process_draft_preview')
def process_draft_preview(self, draft_data: Dict[str, Any]):
    """
    Асинхронная задача для обработки предпросмотра черновика датасета.
    Для файловых источников использует Polars in-memory join (вместо SQL VALUES).
    Для БД источников — стандартный SQL через psycopg2.
    """
    try:
        self.update_state(state='PROGRESS', meta={'progress': 0.05, 'message': 'Инициализация'})

        main_table = draft_data.get('mainTable')
        if not main_table or (isinstance(main_table, dict) and not main_table):
            raise ValidationError("Не указана главная таблица")

        joined_tables = draft_data.get('joinedTables', [])
        limit = draft_data.get('limit')
        if limit is not None:
            limit = int(limit)

        def get_sheet_name(table_dict):
            if not isinstance(table_dict, dict):
                return None
            sheet = (
                table_dict.get('sheet_name') or
                table_dict.get('sheetName') or
                table_dict.get('sheet')
            )
            if sheet:
                return sheet
            nested_file = table_dict.get('file_upload') or {}
            if isinstance(nested_file, dict):
                return nested_file.get('sheet_name') or nested_file.get('sheet')
            return None

        is_main_file = 'file_id' in main_table and main_table.get('file_id')
        has_any_file = is_main_file or any(
            'file_id' in jt and jt.get('file_id') for jt in joined_tables
        )

        if has_any_file:
            result = _process_draft_preview_polars(
                self, main_table, joined_tables, limit, is_main_file, get_sheet_name,
            )
        else:
            result = _process_draft_preview_sql(
                self, main_table, joined_tables, limit,
            )

        self.update_state(state='PROGRESS', meta={'progress': 1.0, 'message': 'Завершено'})
        return result

    except Exception as e:
        logger.error("Ошибка обработки предпросмотра черновика: %s", str(e))
        raise


def _process_draft_preview_polars(self, main_table, joined_tables, limit, is_main_file, get_sheet_name):
    """Polars in-memory join для файловых источников."""
    try:
        import polars as pl
    except ImportError:
        raise ValidationError("polars не установлен")

    files_to_read = []
    if is_main_file:
        files_to_read.append({
            'file_id': main_table['file_id'],
            'sheet_name': get_sheet_name(main_table),
            'row_limit': None,
        })
    for jt in joined_tables:
        if 'file_id' in jt and jt.get('file_id'):
            files_to_read.append({
                'file_id': jt['file_id'],
                'sheet_name': get_sheet_name(jt),
                'row_limit': None,
            })

    self.update_state(state='PROGRESS', meta={
        'progress': 0.15, 'message': f'Чтение {len(files_to_read)} файлов',
    })

    def progress_callback(file_idx, progress):
        total_progress = 0.15 + (file_idx / max(len(files_to_read), 1)) * 0.5 + (progress * 0.5 / max(len(files_to_read), 1))
        self.update_state(state='PROGRESS', meta={
            'progress': total_progress,
            'message': f'Обработка файла {file_idx + 1}/{len(files_to_read)}: {int(progress * 100)}%',
        })

    file_results = _read_files_parallel_with_progress(files_to_read, progress_callback) if files_to_read else []
    file_index = 0

    if is_main_file:
        main_cols, main_rows = file_results[file_index]
        file_index += 1
        col_data = {}
        for ci, col in enumerate(main_cols):
            col_data[col] = [row[ci] if ci < len(row) else None for row in main_rows]
        result_df = pl.DataFrame(col_data)
    else:
        table_name = main_table.get('table_name')
        if not table_name:
            raise ValidationError("Не указано имя таблицы для БД источника")
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM {table_name}')
            db_rows = cursor.fetchall()
            db_cols = [col[0] for col in cursor.description]
        col_data = {}
        for ci, col in enumerate(db_cols):
            col_data[col] = [row[ci] for row in db_rows]
        result_df = pl.DataFrame(col_data)

    self.update_state(state='PROGRESS', meta={'progress': 0.7, 'message': 'Выполнение JOIN'})

    for jt in joined_tables:
        is_join_file = 'file_id' in jt and jt.get('file_id')
        if is_join_file:
            join_cols, join_rows = file_results[file_index]
            file_index += 1
            jcol_data = {}
            for ci, col in enumerate(join_cols):
                jcol_data[col] = [row[ci] if ci < len(row) else None for row in join_rows]
            right_df = pl.DataFrame(jcol_data)
        else:
            table_name = jt.get('table_name')
            if not table_name:
                raise ValidationError("Не указано имя таблицы для JOIN БД источника")
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT * FROM {table_name}')
                db_rows = cursor.fetchall()
                db_cols = [col[0] for col in cursor.description]
            jcol_data = {}
            for ci, col in enumerate(db_cols):
                jcol_data[col] = [row[ci] for row in db_rows]
            right_df = pl.DataFrame(jcol_data)

        lines = jt.get('lines') or []
        if not lines or not lines[0].get('left') or not lines[0].get('right'):
            raise ValidationError("Не указаны поля для join'а")

        left_col = lines[0]['left']
        right_col = lines[0]['right']
        join_type_raw = (jt.get('joinType', 'LEFT JOIN') or 'LEFT JOIN').strip().upper()

        how = 'left'
        if 'INNER' in join_type_raw:
            how = 'inner'
        elif 'RIGHT' in join_type_raw:
            result_df, right_df = right_df, result_df
            left_col, right_col = right_col, left_col
            how = 'left'
        elif 'FULL' in join_type_raw:
            how = 'full'

        result_df = result_df.join(right_df, left_on=left_col, right_on=right_col, how=how, suffix='_right')

    if limit and result_df.height > limit:
        result_df = result_df.head(limit)

    self.update_state(state='PROGRESS', meta={'progress': 0.9, 'message': 'Формирование результата'})

    columns = list(result_df.columns)
    rows = result_df.to_numpy().tolist()
    return {'columns': columns, 'rows': rows}


def _process_draft_preview_sql(self, main_table, joined_tables, limit):
    """SQL-only path для БД источников (без файлов)."""
    from psycopg2 import sql as psql

    table_name = main_table.get('table_name')
    if not table_name:
        raise ValidationError("Не указано имя таблицы для БД источника")

    main_alias = 'a'
    if '.' in table_name:
        schema, table = table_name.split('.', 1)
        main_from = psql.SQL('{}.{} AS {}').format(
            psql.Identifier(schema), psql.Identifier(table), psql.Identifier(main_alias),
        )
    else:
        main_from = psql.SQL('{} AS {}').format(
            psql.Identifier(table_name), psql.Identifier(main_alias),
        )

    main_cols = introspect_columns(table_name)

    select_parts = [
        psql.SQL('{}.{} AS {}').format(
            psql.Identifier(main_alias), psql.Identifier(col), psql.Identifier(col),
        )
        for col in main_cols
    ]

    join_clauses = []
    alias_idx = ord('b')
    all_cols = set(main_cols)

    for jt in joined_tables:
        tbl_alias = chr(alias_idx)
        alias_idx += 1

        jt_table_name = jt.get('table_name')
        if not jt_table_name:
            raise ValidationError("Не указано имя таблицы для JOIN БД источника")

        if '.' in jt_table_name:
            jschema, jtable = jt_table_name.split('.', 1)
            join_from = psql.SQL('{}.{} AS {}').format(
                psql.Identifier(jschema), psql.Identifier(jtable), psql.Identifier(tbl_alias),
            )
        else:
            join_from = psql.SQL('{} AS {}').format(
                psql.Identifier(jt_table_name), psql.Identifier(tbl_alias),
            )

        join_cols = introspect_columns(jt_table_name)
        for col in join_cols:
            if col not in all_cols:
                select_parts.append(psql.SQL('{}.{} AS {}').format(
                    psql.Identifier(tbl_alias), psql.Identifier(col), psql.Identifier(col),
                ))
                all_cols.add(col)

        join_type = (jt.get('joinType', 'LEFT JOIN') or 'LEFT JOIN').strip().upper()
        if 'JOIN' not in join_type:
            join_type = f'{join_type} JOIN'

        lines = jt.get('lines') or []
        if not lines or not lines[0].get('left') or not lines[0].get('right'):
            raise ValidationError("Не указаны поля для join'а")

        left_col = lines[0]['left']
        right_col = lines[0]['right']

        join_condition = psql.SQL('{}.{} = {}.{}').format(
            psql.Identifier(main_alias), psql.Identifier(left_col),
            psql.Identifier(tbl_alias), psql.Identifier(right_col),
        )
        join_clause = psql.SQL('{} {} ON {}').format(
            psql.SQL(join_type), join_from, join_condition,
        )
        join_clauses.append(join_clause)

    query_parts = [
        psql.SQL('SELECT {}').format(psql.SQL(', ').join(select_parts)),
        psql.SQL('FROM {}').format(main_from),
    ]
    query_parts.extend(join_clauses)
    if limit:
        query_parts.append(psql.SQL('LIMIT {}').format(psql.Literal(limit)))

    final_query = psql.SQL(' ').join(query_parts)

    self.update_state(state='PROGRESS', meta={'progress': 0.7, 'message': 'Выполнение запроса'})

    with connection.cursor() as cursor:
        cursor.execute(final_query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    self.update_state(state='PROGRESS', meta={'progress': 0.9, 'message': 'Формирование результата'})
    return {'columns': columns, 'rows': rows}


@shared_task(bind=True, name='modules.bi_analysis_modern.api.tasks.process_file_preview')
def process_file_preview(self, temp_path: str, sheet_name: Optional[str] = None,
                        row_limit: int = 1000000, has_header: bool = True):
    """
    Асинхронная задача для обработки предпросмотра временного файла.
    Использует polars с векторизацией и чанкингом для максимальной производительности.
    """
    try:
        import polars as pl

        self.update_state(state='PROGRESS', meta={'progress': 0.1, 'message': 'Определение типа файла'})

        file_ext = os.path.splitext(temp_path)[1].lower()

        if file_ext in ('.xlsx', '.xls'):
            self.update_state(state='PROGRESS', meta={'progress': 0.3, 'message': 'Чтение Excel файла'})

            if sheet_name:
                df = pl.read_excel(temp_path, sheet_name=sheet_name)
            else:
                df = pl.read_excel(temp_path, sheet_index=0)

            self.update_state(state='PROGRESS', meta={'progress': 0.6, 'message': 'Обработка данных'})

            if row_limit is not None and row_limit > 0:
                df = df.head(row_limit)

            columns = df.columns
            rows_list = df.to_numpy().tolist()

            self.update_state(state='PROGRESS', meta={'progress': 0.9, 'message': 'Формирование результата'})

            if has_header and rows_list:
                parsed = [list(columns), *rows_list]
            else:
                parsed = rows_list

            self.update_state(state='PROGRESS', meta={'progress': 1.0, 'message': 'Завершено'})

            return {'parsed': parsed}

        elif file_ext in ('.csv', '.txt'):
            self.update_state(state='PROGRESS', meta={'progress': 0.3, 'message': 'Чтение CSV файла'})

            try:
                df = pl.read_csv(temp_path, encoding='utf8', try_parse_dates=True)
            except:
                df = pl.read_csv(temp_path, encoding='cp1251', try_parse_dates=True)

            self.update_state(state='PROGRESS', meta={'progress': 0.6, 'message': 'Обработка данных'})

            if row_limit is not None and row_limit > 0:
                df = df.head(row_limit)

            columns = df.columns
            rows_list = df.to_numpy().tolist()

            self.update_state(state='PROGRESS', meta={'progress': 0.9, 'message': 'Формирование результата'})

            if has_header and rows_list:
                parsed = [list(columns), *rows_list]
            else:
                parsed = rows_list

            self.update_state(state='PROGRESS', meta={'progress': 1.0, 'message': 'Завершено'})

            return {'parsed': parsed}
        else:
            raise ValidationError(f"Неподдерживаемый тип файла: {file_ext}")

    except ImportError:
        logger.warning("Polars не установлен, используется fallback метод")
        from openpyxl import load_workbook

        self.update_state(state='PROGRESS', meta={'progress': 0.3, 'message': 'Чтение файла (fallback)'})

        wb = load_workbook(filename=temp_path, read_only=True, data_only=True)
        try:
            ws = wb.active
        except IndexError:
            wb.close()
            return {'parsed': []}

        rows = []
        for row in ws.iter_rows(values_only=True):
            normalized = [("" if cell is None else str(cell)) for cell in row]
            rows.append(normalized)
            if len(rows) >= row_limit:
                break
        wb.close()

        if not rows:
            return {'parsed': []}

        if has_header:
            header, *body = rows
            parsed = [list(header), *body]
        else:
            parsed = rows

        self.update_state(state='PROGRESS', meta={'progress': 1.0, 'message': 'Завершено'})

        return {'parsed': parsed}

    except Exception as e:
        logger.error(f"Ошибка обработки предпросмотра файла {temp_path}: {str(e)}")
        raise


@shared_task(bind=True, name='modules.bi_analysis_modern.api.tasks.execute_pipeline_async')
def execute_pipeline_async(self, pipeline_id: int, user_id: int, params: Optional[Dict[str, Any]] = None):
    """
    Асинхронное выполнение пайплайна. Результат сохраняется в Django cache.
    """
    from .execution.result_cache import execution_cache, task_key, ASYNC_RESULT_TTL
    from django.contrib.auth import get_user_model
    from .bi_pipelines.models import Pipeline
    from .graph_execute import execute_graph
    from .pipeline_types import row_count, to_rows_slice
    from .config import EXECUTE_PREVIEW_ROWS, EXECUTE_CHUNK_SIZE
    preview_limit = EXECUTE_PREVIEW_ROWS if EXECUTE_PREVIEW_ROWS is not None else EXECUTE_CHUNK_SIZE

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError(f'User {user_id} не найден')

    try:
        pipeline = Pipeline.objects.get(pk=pipeline_id, owner=user)
    except Pipeline.DoesNotExist:
        return {'error': 'Пайплайн не найден', 'chartData': []}

    graph_data = pipeline.graph_data or {}
    nodes = graph_data.get('nodes', [])
    edges = graph_data.get('edges', [])
    if not nodes:
        return {'chartData': [], 'error': 'Пайплайн пуст'}

    params = params or {}
    result = execute_graph(nodes, edges, user, params=params, preview=False)

    raw_df = result.pop('_raw_df', None)
    total_rows = result.pop('_total_rows', None)

    if raw_df is not None:
        rc = total_rows if total_rows is not None else row_count(raw_df)
        chart_data_slice = to_rows_slice(raw_df, preview_limit)
        cache_result = {
            'chartData': chart_data_slice,
            'error': result.get('error'),
            'rows_count': rc,
        }
    else:
        chart_data = result.get('chartData', [])
        rc = len(chart_data)
        cache_result = {
            'chartData': chart_data[:preview_limit],
            'error': result.get('error'),
            'rows_count': rc,
        }

    execution_cache().set(task_key(self.request.id), cache_result, timeout=ASYNC_RESULT_TTL)
    return {'status': 'ok', 'rows_count': rc, 'task_id': str(self.request.id)}
