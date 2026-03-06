from uuid import uuid4
from django.core.files import File
from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from openpyxl import load_workbook
import openpyxl
import tempfile
import os
import csv
import logging

from src.core.utils.mixins import SwaggerSafeMixin

from ..bi_connections.models import Connection
from .models import FileUpload
from .serializers import FileUploadSerializer
from .binary_storage import is_binary_file, read_from_binary
from ..services.services import count_file_rows, read_file_preview_slice

logger = logging.getLogger(__name__)


class TempUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Файл не передан'}, status=400)
        suffix = os.path.splitext(file.name)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            temp_path = tmp.name
        return Response({
            'temp_path': temp_path,
            'original_filename': file.name,
            'file_type': suffix.lstrip('.').lower()
        }, status=201)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FileUpload.objects.none()
        return FileUpload.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FileUploadDetailView(SwaggerSafeMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FileUpload.objects.none()
        return FileUpload.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        columns_info = extract_columns_info(instance)
        instance.columns_info = columns_info
        instance.save(update_fields=['columns_info'])

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        logger.info(f"[RETRIEVE] Попытка получить FileUpload с ID={pk}, пользователь={request.user.id}")

        try:
            instance = self.get_object()
            logger.info(f"[RETRIEVE] FileUpload найден: ID={instance.id}, UUID={instance.file_uuid}, owner={instance.owner.id}")
        except FileUpload.DoesNotExist:
            logger.warning(f"[RETRIEVE] FileUpload с ID={pk} не найден (DoesNotExist), пользователь={request.user.id}")
            return Response(
                {"detail": "No FileUpload matches the given query."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Http404:
            logger.warning(f"[RETRIEVE] FileUpload с ID={pk} не найден (Http404), пользователь={request.user.id}")
            return Response(
                {"detail": "No FileUpload matches the given query."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(instance)
        data = serializer.data

        if not instance.file or not hasattr(instance.file, 'path'):
            data['parsed'] = []
            return Response(data)

        encoding = request.query_params.get('encoding', 'utf-8')
        delimiter = request.query_params.get('delimiter', ',')
        has_header = request.query_params.get('has_header', 'true').lower() == 'true'

        limit = request.query_params.get('limit')
        offset = request.query_params.get('offset', '0')
        limit = int(limit) if limit else None
        offset = int(offset) if offset else 0

        sheet_name = request.query_params.get('sheet_name') or request.query_params.get('sheet')

        total_rows_count = None
        try:
            total_rows_count = count_file_rows(instance.id, sheet_name)
        except Exception as e:
            logger.warning(f"Не удалось подсчитать строки для файла {instance.id}: {str(e)}")

        try:
            columns, rows, sheets = read_file_preview_slice(
                instance,
                offset=offset,
                limit=limit,
                encoding=encoding,
                delimiter=delimiter,
                sheet_name=sheet_name,
            )

            if sheets is not None:
                data['sheets'] = sheets

            if has_header:
                parsed = [list(columns), *rows]
            else:
                parsed = rows

            data['parsed'] = parsed

            if total_rows_count is not None:
                data['total_count'] = total_rows_count
            else:
                data['total_count'] = offset + len(rows)

            return Response(data)

        except Exception as exc:
            logger.error(f"Ошибка при чтении файла {instance.id}: {str(exc)}", exc_info=True)
            return Response({'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        instance = serializer.instance

        if not instance.file_uuid:
            instance.file_uuid = uuid4()
            instance.save(update_fields=['file_uuid'])

        file = self.request.FILES.get('file')
        request_data = getattr(self.request, 'data', {})
        name = request_data.get('name') if isinstance(request_data, dict) else None
        sheet = request_data.get('sheet') if isinstance(request_data, dict) else None
        file_type = (file.name.split('.')[-1].lower()
                     if file else
                     (name.split('.')[-1].lower() if name and '.' in name else None))

        if file and file_type == 'xlsx' and sheet:
            suffix = os.path.splitext(file.name)[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name

            try:
                wb = load_workbook(temp_path, read_only=False)
                sheets_to_remove = [ws_name for ws_name in wb.sheetnames if ws_name != sheet]
                for ws_name in sheets_to_remove:
                    ws = wb[ws_name]
                    wb.remove(ws)

                single_sheet_path = temp_path + "_single.xlsx"
                wb.save(single_sheet_path)
                wb.close()

                instance = serializer.save(
                    name=name or serializer.instance.name,
                    original_filename=file.name,
                    file_type=file_type
                )

                if instance.file and hasattr(instance.file, 'path') and os.path.exists(instance.file.path):
                    try:
                        instance.file.delete(save=False)
                    except Exception as e:
                        logger.warning(f"Ошибка при удалении старого файла: {e}")

                uuid_filename = f"{instance.file_uuid}.bin" if file_type == 'bin' else f"{instance.file_uuid}{os.path.splitext(file.name)[1]}"
                with open(single_sheet_path, 'rb') as f:
                    instance.file.save(uuid_filename, File(f), save=True)

                try:
                    os.remove(single_sheet_path)
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Ошибка при удалении временных файлов: {e}")

            except Exception as e:
                logger.error(f"Ошибка при обработке листов: {e}")
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                if file:
                    file_ext = os.path.splitext(file.name)[1] or ('.bin' if file_type == 'bin' else '.xlsx')
                    uuid_filename = f"{instance.file_uuid}{file_ext}"
                    with open(temp_path, 'rb') as f:
                        instance.file.save(uuid_filename, File(f), save=True)

                instance = serializer.save(
                    name=name or serializer.instance.name,
                    original_filename=(file.name if file else serializer.instance.original_filename),
                    file_type=file_type
                )
        else:
            if file:
                file_ext = os.path.splitext(file.name)[1] or ('.bin' if file_type == 'bin' else '.xlsx')
                uuid_filename = f"{instance.file_uuid}{file_ext}"
                instance.file.save(uuid_filename, file, save=False)

            instance = serializer.save(
                name=name or serializer.instance.name,
                original_filename=(file.name if file else serializer.instance.original_filename),
                file_type=file_type
            )

        columns_info = extract_columns_info(instance)
        instance.columns_info = columns_info
        instance.save(update_fields=['columns_info'])

    def perform_destroy(self, instance):
        if instance.file and os.path.isfile(instance.file.path):
            try:
                os.remove(instance.file.path)
            except PermissionError:
                import gc
                gc.collect()
                raise ValidationError("Файл занят другим процессом.")
        instance.delete()

    @staticmethod
    def _parse_csv(path, encoding, delimiter, has_header):
        with open(path, 'r', encoding=encoding) as f:
            reader = csv.reader(f, delimiter='\t' if delimiter == '\\t' else delimiter)
            rows = list(reader)
        if not has_header and rows:
            alph = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            headers = [alph[i] if i < len(alph) else f"Col{i}" for i in range(len(rows[0]))]
            rows.insert(0, headers)
        return rows

    @staticmethod
    def _parse_xlsx(path, has_header):
        wb = load_workbook(filename=path, read_only=True)
        try:
            sheet = wb.sheetnames[0]
            ws = wb[sheet]
            data = list(ws.values)
            sheetnames = wb.sheetnames
            if not has_header:
                return data, sheetnames
            headers, *body = data
            return [list(headers), *body], sheetnames
        finally:
            wb.close()


class FileUploadByConnectionView(SwaggerSafeMixin, generics.ListAPIView):
    serializer_class = FileUploadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FileUpload.objects.none()
        conn_id = self.kwargs['connection_id']
        return FileUpload.objects.filter(
            owner=self.request.user,
            connection_id=conn_id
        ).select_related('connection', 'owner').order_by('-uploaded_at')


def detect_column_type(values):
    filtered = [v for v in values if v not in (None, '')]
    if not filtered:
        return "string"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in filtered):
        if all(isinstance(v, int) for v in filtered):
            return "integer"
        return "float"
    try:
        import dateutil.parser
        if all(isinstance(dateutil.parser.parse(str(v)), object) for v in filtered):
            return "date"
    except Exception:
        pass
    if all(str(v).lower() in ('true', 'false') for v in filtered):
        return "bool"
    return "string"


def extract_columns_info(instance):
    """
    Извлекает информацию о колонках из файла.
    Читает только первые 200 строк для ускорения.
    """
    path = instance.file.path

    if is_binary_file(path) or instance.file_type == 'bin':
        try:
            columns, rows = read_from_binary(path, row_limit=200)
            if not rows:
                return {'columns': [], 'types': []}
            types = []
            sample_rows = rows[:50] if len(rows) > 50 else rows
            for col_idx in range(len(columns)):
                col_values = [row[col_idx] for row in sample_rows if len(row) > col_idx and row[col_idx] is not None]
                types.append(detect_column_type(col_values))
            return {'columns': columns, 'types': types}
        except Exception as e:
            logger.error(f"Ошибка чтения бинарного файла для извлечения колонок: {str(e)}")
            return {'columns': [], 'types': []}

    if instance.file_type == 'xlsx':
        try:
            wb = openpyxl.load_workbook(filename=path, read_only=True, data_only=True)
            sheet = wb.active
            rows = []
            for idx, row in enumerate(sheet.iter_rows(values_only=True)):
                if idx >= 200:
                    break
                rows.append(row)
            if not rows:
                return {'columns': [], 'types': []}
            headers = rows[0] if rows else []
            columns = list(headers)
            types = []
            sample_rows = rows[1:51] if len(rows) > 1 else []
            for col_idx in range(len(columns)):
                col_values = [row[col_idx] for row in sample_rows if len(row) > col_idx and row[col_idx] is not None]
                types.append(detect_column_type(col_values))
            wb.close()
            return {'columns': columns, 'types': types}
        except Exception:
            return {'columns': [], 'types': []}

    elif instance.file_type == 'csv':
        try:
            rows = []
            with open(path, encoding='utf-8') as f:
                reader = csv.reader(f)
                for idx, row in enumerate(reader):
                    if idx >= 200:
                        break
                    rows.append(row)
            if not rows:
                return {'columns': [], 'types': []}
            headers = rows[0] if rows else []
            columns = list(headers)
            types = []
            sample_rows = rows[1:51] if len(rows) > 1 else []
            for col_idx in range(len(columns)):
                col_values = [row[col_idx] for row in sample_rows if len(row) > col_idx and row[col_idx]]
                types.append(detect_column_type(col_values))
            return {'columns': columns, 'types': types}
        except Exception:
            return {'columns': [], 'types': []}

    return {'columns': [], 'types': []}


class FinalizeUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_data = getattr(request, 'data', {})
        if not isinstance(request_data, dict):
            request_data = {}
        temp_path = request_data.get('temp_path')
        name = request_data.get('name')
        original_filename = request_data.get('original_filename')
        file_type = request_data.get('file_type')
        connection_id = request_data.get('connection')
        sheet = request_data.get('sheet')

        if not all([temp_path, name, original_filename, file_type]):
            return Response(
                {"error": "Необходимы поля temp_path, name, original_filename, file_type"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not os.path.exists(temp_path):
            return Response({"error": "Временный файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        connection_obj = None
        if connection_id:
            try:
                connection_obj = Connection.objects.get(pk=connection_id)
            except Connection.DoesNotExist:
                return Response({"error": "Connection not found"}, status=404)

        upload = FileUpload(
            owner=request.user,
            name=name,
            original_filename=original_filename,
            file_type=file_type,
            connection=connection_obj
        )
        upload.save()

        if not upload.file_uuid:
            upload.file_uuid = uuid4()
            upload.save(update_fields=['file_uuid'])

        logger.info(f"Создан FileUpload с UUID: {upload.file_uuid}, ID: {upload.id}")

        binary_converted = False
        binary_path = None
        polars_available = False

        try:
            from .binary_storage import convert_to_binary

            try:
                import polars as pl
                polars_available = True
                logger.info("Polars установлен, конвертация в .bin возможна")
            except ImportError:
                logger.error("Polars не установлен! Файлы не будут конвертироваться в .bin формат")

            if polars_available and temp_path and file_type and os.path.exists(temp_path):
                temp_binary_path = temp_path + ".bin"
                logger.info(f"[CONVERT] Начинаем конвертацию файла {temp_path} в бинарный формат {temp_binary_path}, тип: {file_type}, лист: {sheet}")

                conversion_result = convert_to_binary(temp_path, temp_binary_path, sheet_name=sheet, file_type=file_type)
                logger.info(f"[CONVERT] Результат конвертации: {conversion_result}")

                if conversion_result and os.path.exists(temp_binary_path):
                    binary_path = temp_binary_path
                    binary_converted = True
                    file_size = os.path.getsize(binary_path)
                    logger.info(f"[CONVERT] Файл успешно конвертирован в бинарный формат: {binary_path}, размер: {file_size} байт")
                else:
                    logger.warning(f"[CONVERT] Не удалось конвертировать файл {temp_path} в бинарный формат")
        except Exception as e:
            logger.error(f"[CONVERT] Ошибка при конвертации в бинарный формат: {str(e)}", exc_info=True)

        if not upload.file_uuid:
            upload.file_uuid = uuid4()
            upload.save(update_fields=['file_uuid'])

        logger.info(f"[SAVE] binary_converted={binary_converted}, binary_path={binary_path}")

        if binary_converted and binary_path and os.path.exists(binary_path):
            binary_filename = f"{upload.file_uuid}.bin"
            logger.info(f"[SAVE] Сохраняем бинарный файл: {binary_filename}")
            try:
                with open(binary_path, 'rb') as f:
                    upload.file.save(binary_filename, File(f), save=True)
                upload.file_type = 'bin'
                upload.save(update_fields=['file', 'file_type'])
                logger.info("[SAVE] Бинарный файл успешно сохранен")
            except Exception as e:
                logger.error(f"[SAVE] Ошибка при сохранении бинарного файла: {str(e)}", exc_info=True)
                binary_converted = False

            try:
                if binary_path and os.path.exists(binary_path):
                    os.remove(binary_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный бинарный файл: {e}")
        else:
            logger.warning(f"[SAVE] Используется оригинальный файл вместо бинарного. polars_available={polars_available}")

            if original_filename:
                file_ext = os.path.splitext(original_filename)[1] or '.bin'
            else:
                file_ext = '.bin' if file_type == 'bin' else ('.xlsx' if file_type == 'xlsx' else '.csv')

            uuid_filename = f"{upload.file_uuid}{file_ext}"

            if temp_path and os.path.exists(temp_path):
                with open(temp_path, 'rb') as f:
                    upload.file.save(uuid_filename, File(f), save=True)

        upload.columns_info = extract_columns_info(upload)
        upload.save(update_fields=['columns_info'])

        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass

        serializer = FileUploadSerializer(upload)
        response_data = serializer.data
        logger.info(f"[FINALIZE] Файл успешно создан: ID={upload.id}, UUID={upload.file_uuid}, name={upload.name}, owner={upload.owner.id}")
        return Response(response_data, status=status.HTTP_201_CREATED)


class XlsxSheetListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file or not file.name.endswith('.xlsx'):
            raise ValidationError("Ожидался .xlsx файл")

        try:
            wb = load_workbook(filename=file, read_only=True)
            sheets = wb.sheetnames
            wb.close()
            return Response({"filename": file.name, "sheets": sheets})
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class XlsxTempPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_data = getattr(request, 'data', {})
        if not isinstance(request_data, dict):
            request_data = {}
        temp_path = request_data.get('temp_path')
        has_header = (request_data.get('has_header', 'true').lower() == 'true'
                      if isinstance(request_data.get('has_header'), str) else True)
        sheet_name = request_data.get('sheet_name')
        row_limit = request_data.get('row_limit')
        if row_limit is not None:
            row_limit = int(row_limit)
        use_async = (request_data.get('async', 'false').lower() == 'true'
                     if isinstance(request_data.get('async'), str) else False)

        if not temp_path or not os.path.exists(temp_path):
            return Response({"error": "Временный файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        file_size = os.path.getsize(temp_path)
        should_use_async = (use_async or file_size > 5 * 1024 * 1024 or
                            (row_limit is not None and row_limit > 500) or row_limit is None)

        if should_use_async:
            from ..tasks import process_file_preview
            task = process_file_preview.delay(temp_path, sheet_name, row_limit, has_header)
            return Response({
                "task_id": task.id,
                "status": "processing",
                "message": "Предпросмотр обрабатывается асинхронно"
            }, status=202)

        try:
            try:
                import polars as pl

                file_ext = os.path.splitext(temp_path)[1].lower()

                if file_ext in ('.xlsx', '.xls'):
                    if sheet_name:
                        df = pl.read_excel(temp_path, sheet_name=sheet_name)
                    else:
                        df = pl.read_excel(temp_path, sheet_index=0)

                    if row_limit and row_limit > 0:
                        df = df.head(row_limit)

                    columns = df.columns
                    rows_list = df.to_numpy().tolist()

                    if has_header and rows_list:
                        parsed = [list(columns), *rows_list]
                    else:
                        parsed = rows_list

                    return Response({"parsed": parsed})

                elif file_ext in ('.csv', '.txt'):
                    try:
                        df = pl.read_csv(temp_path, encoding='utf8', try_parse_dates=True)
                    except Exception:
                        df = pl.read_csv(temp_path, encoding='cp1251', try_parse_dates=True)

                    if row_limit and row_limit > 0:
                        df = df.head(row_limit)

                    columns = df.columns
                    rows_list = df.to_numpy().tolist()

                    if has_header and rows_list:
                        parsed = [list(columns), *rows_list]
                    else:
                        parsed = rows_list

                    return Response({"parsed": parsed})
            except ImportError:
                pass

            wb = load_workbook(filename=temp_path, read_only=True, data_only=True)
            try:
                ws = wb.active
            except IndexError:
                wb.close()
                return Response({"parsed": []})

            rows = []
            for row in ws.iter_rows(values_only=True):
                normalized = [("" if cell is None else str(cell)) for cell in row]
                rows.append(normalized)
                if row_limit and len(rows) >= row_limit:
                    break
            wb.close()

            if not rows:
                return Response({"parsed": []})

            if has_header:
                header, *body = rows
                parsed = [list(header), *body]
            else:
                parsed = rows

            return Response({"parsed": parsed})
        except Exception as exc:
            return Response({"error": f"Ошибка при чтении файла: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FilePreviewTaskStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({"detail": "Не указан task_id"}, status=400)

        try:
            from celery.result import AsyncResult
            from src.config.celery import celery_app

            task = AsyncResult(task_id, app=celery_app)

            if task.state == 'PENDING':
                response = {
                    'task_id': task_id,
                    'status': 'pending',
                    'message': 'Задача ожидает выполнения'
                }
            elif task.state == 'PROGRESS':
                response = {
                    'task_id': task_id,
                    'status': 'processing',
                    'message': task.info.get('message', 'Задача выполняется') if isinstance(task.info, dict) else 'Задача выполняется',
                    'progress': task.info.get('progress', 0) if isinstance(task.info, dict) else None
                }
            elif task.state == 'SUCCESS':
                response = {
                    'task_id': task_id,
                    'status': 'success',
                    'result': task.result
                }
            elif task.state == 'FAILURE':
                response = {
                    'task_id': task_id,
                    'status': 'failure',
                    'error': str(task.info) if task.info else 'Неизвестная ошибка'
                }
            else:
                response = {
                    'task_id': task_id,
                    'status': task.state.lower(),
                    'message': f'Статус задачи: {task.state}'
                }

            return Response(response, status=200)

        except Exception as e:
            return Response({"detail": f"Ошибка получения статуса задачи: {str(e)}"}, status=500)
