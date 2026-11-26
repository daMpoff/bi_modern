from contextlib import closing, contextmanager
from uuid import UUID, uuid4
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile
from django.core.files import File
from django.db import router, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
import openpyxl
import tempfile
import os
import csv
import logging

from src.core.utils.mixins import SwaggerSafeMixin

from ..bi_connections.models import Connection
from .models import FileUpload
from .serializers import FileUploadSerializer
from .temp_uploads import resolve_upload, save_upload
from .binary_storage import convert_to_binary, is_binary_file, read_from_binary
from ..execution.result_cache import ASYNC_RESULT_TTL, execution_cache
from ..services.services import count_file_rows, read_file_preview_slice, read_temp_preview

logger = logging.getLogger(__name__)


class TempUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'Файл не передан'}, status=400)
        suffix = os.path.splitext(file.name)[-1]
        return Response({
            'temp_path': save_upload(file, request.user),
            'original_filename': file.name,
            'file_type': suffix.lstrip('.').lower()
        }, status=201)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return FileUpload.objects.none()
        return FileUpload.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


@contextmanager
def _replacement_content(upload, sheet):
    if not sheet or not upload.name.lower().endswith('.xlsx'):
        yield upload
        return
    with tempfile.TemporaryFile() as copy:
        try:
            with closing(load_workbook(upload)) as workbook:
                if sheet not in workbook.sheetnames:
                    raise ValidationError({'sheet': 'Лист не найден в книге.'})
                for page in list(workbook):
                    if page.title != sheet:
                        workbook.remove(page)
                workbook.save(copy)
        except ValidationError:
            raise
        except (ValueError, KeyError, OSError, BadZipFile, InvalidFileException, ParseError) as exc:
            raise ValidationError({'file': 'Не удалось прочитать книгу XLSX.'}) from exc
        copy.seek(0)
        yield File(copy)


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
        upload = self.request.FILES.get('file')
        replacement_name = None
        storage = serializer.instance.file.storage
        try:
            if upload:
                suffix = os.path.splitext(upload.name)[1].lower()
                with _replacement_content(upload, self.request.data.get('sheet')) as content:
                    target = serializer.instance.file.field.generate_filename(serializer.instance, f'{uuid4()}{suffix}')
                    replacement_name = storage.save(target, content)

            database = router.db_for_write(FileUpload, instance=serializer.instance)
            with transaction.atomic(using=database):
                instance = get_object_or_404(self.get_queryset().using(database).select_for_update(),
                                             pk=serializer.instance.pk)
                serializer.instance = instance
                if not upload:
                    serializer.save(original_filename=instance.original_filename, file_type=instance.file_type)
                    return

                old_name = instance.file.name
                instance = serializer.save(file=replacement_name, original_filename=upload.name,
                                           file_type=suffix.lstrip('.'))
                instance.columns_info = extract_columns_info(instance)
                instance.save(update_fields=['columns_info'])
                if old_name:
                    transaction.on_commit(lambda: storage.delete(old_name), using=database, robust=True)
        except Exception:
            if replacement_name:
                storage.delete(replacement_name)
            raise

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

        temp_path = resolve_upload(temp_path, request.user)
        if temp_path is None:
            return Response({"error": "Временный файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        connection_obj = None
        if connection_id:
            try:
                connection_obj = Connection.objects.get(pk=connection_id, owner=request.user)
            except (Connection.DoesNotExist, ValueError, TypeError):
                return Response({"error": "Connection not found"}, status=404)

        upload = FileUpload(
            owner=request.user,
            name=name,
            original_filename=original_filename,
            file_type=file_type,
            connection=connection_obj
        )
        # Only one finalization can consume this reference. Restore it on failure so the owner can retry.
        with tempfile.TemporaryDirectory(dir=os.path.dirname(temp_path)) as workdir:
            source = os.path.join(workdir, os.path.basename(temp_path))
            try:
                os.replace(temp_path, source)
            except FileNotFoundError:
                return Response({"error": "Временный файл не найден"}, status=404)

            try:
                binary = os.path.join(workdir, 'converted.bin')
                if convert_to_binary(source, binary, sheet_name=sheet, file_type=file_type):
                    try:
                        with open(binary, 'rb') as stream:
                            upload.file.save(f'{upload.file_uuid}.bin', File(stream), save=False)
                        upload.file_type = 'bin'
                    except OSError:
                        logger.warning('Не удалось сохранить бинарную копию, сохраняем исходный формат.', exc_info=True)
                if not upload.file:
                    suffix = os.path.splitext(source)[1]
                    with open(source, 'rb') as stream, _replacement_content(File(stream), sheet) as content:
                        upload.file.save(f'{upload.file_uuid}{suffix}', content, save=False)

                upload.columns_info = extract_columns_info(upload)
                upload.save(force_insert=True)
            except Exception:
                os.replace(source, temp_path)
                if upload.file:
                    upload.file.delete(save=False)
                raise
        return Response(FileUploadSerializer(upload).data, status=status.HTTP_201_CREATED)


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
        has_header = str(request_data.get('has_header', True)).lower() == 'true'
        sheet_name = request_data.get('sheet_name')
        row_limit = request_data.get('row_limit')
        if row_limit is not None:
            try:
                row_limit = int(row_limit)
                if row_limit < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ValidationError({'row_limit': 'Ожидается целое неотрицательное число.'})
        use_async = str(request_data.get('async', False)).lower() == 'true'

        temp_path = resolve_upload(temp_path, request.user)
        if temp_path is None:
            return Response({"error": "Временный файл не найден"}, status=status.HTTP_404_NOT_FOUND)

        file_size = os.path.getsize(temp_path)
        should_use_async = (use_async or file_size > 5 * 1024 * 1024 or
                            (row_limit is not None and row_limit > 500) or row_limit is None)

        if should_use_async:
            from ..tasks import process_file_preview
            task_id = str(uuid4())
            cache = execution_cache()
            owner_key = _preview_owner_key(task_id)
            cache.set(owner_key, request.user.pk, ASYNC_RESULT_TTL)
            try:
                process_file_preview.apply_async(args=(temp_path, sheet_name, row_limit, has_header), task_id=task_id)
            except Exception:
                cache.delete(owner_key)
                raise
            return Response({
                "task_id": task_id,
                "status": "processing",
                "message": "Предпросмотр обрабатывается асинхронно"
            }, status=202)

        try:
            parsed = read_temp_preview(temp_path, sheet_name, row_limit, has_header)
            return Response({'parsed': parsed})
        except ValidationError:
            raise
        except Exception as exc:
            return Response({"error": f"Ошибка при чтении файла: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _preview_owner_key(task_id):
    return f'bi_modern:file-preview-owner:{task_id}'


class FilePreviewTaskStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({"detail": "Не указан task_id"}, status=400)
        try:
            task_id = str(UUID(task_id))
        except ValueError:
            return Response({"detail": "Задача не найдена"}, status=404)
        if execution_cache().get(_preview_owner_key(task_id)) != request.user.pk:
            return Response({"detail": "Задача не найдена"}, status=404)

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
