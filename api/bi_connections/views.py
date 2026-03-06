from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404
import os

from src.core.utils.mixins import SwaggerSafeMixin

from .models import Connection
from .serializers import ConnectionSerializer
from .methods import CheckConnection
from .connection_runner import get_tables, get_table_preview
from .meta import get_connection_table_columns_meta


class ConnectionListCreateView(SwaggerSafeMixin, generics.ListCreateAPIView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Connection.objects.none()
        user = self.request.user
        if not user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ConnectionDetailView(SwaggerSafeMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        if obj.owner != self.request.user:
            raise PermissionDenied('У вас нет доступа к этому подключению')
        return obj

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Connection.objects.none()
        return Connection.objects.filter(owner=self.request.user).select_related('owner')


class CheckConnectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        db_type = request.data.get('type')
        host = request.data.get('host')
        port = request.data.get('port')
        username = request.data.get('username')
        password = request.data.get('password')
        database = request.data.get('database', 'default')

        try:
            if db_type == 'clickhouse':
                success, message = CheckConnection.check_clickhouse(host, port, username, password)
            elif db_type == 'postgresql':
                success, message = CheckConnection.check_postgresql(host, port, username, password, database)
            elif db_type == 'mssql':
                success, message = CheckConnection.check_mssql(host, port, username, password, database)
            else:
                return Response({'success': False, 'message': 'Тип базы данных не поддерживается'}, status=400)

            return Response({'success': success, 'message': message})

        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)


class ConnectionTablesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, connection_id):
        connection = get_object_or_404(Connection, id=connection_id, owner=request.user)
        try:
            tables = get_tables(connection)
            return Response(tables)
        except Exception as e:
            raise ValidationError(f"Ошибка при получении таблиц: {str(e)}")


class ConnectionTableColumnsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, connection_id):
        connection = get_object_or_404(Connection, id=connection_id, owner=request.user)
        table_name = request.query_params.get('table_name')
        schema = request.query_params.get('schema', 'public')

        if not table_name:
            raise ValidationError("Параметр table_name обязателен")

        try:
            columns = get_connection_table_columns_meta(connection, table_name, schema)
            return Response(columns)
        except Exception as e:
            raise ValidationError(f"Ошибка при получении колонок: {str(e)}")


class ConnectionTablePreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, connection_id):
        connection = get_object_or_404(Connection, id=connection_id, owner=request.user)
        table_name = request.query_params.get('table_name')
        schema = request.query_params.get('schema', 'public')
        limit = int(request.query_params.get('limit', 200))
        offset = int(request.query_params.get('offset', 0))

        if not table_name:
            raise ValidationError("Параметр table_name обязателен")

        try:
            data = get_table_preview(connection, table_name, schema, limit, offset)
            return Response(data)
        except Exception as e:
            raise ValidationError(f"Ошибка при получении данных таблицы: {str(e)}")


class ConnectionFilesStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from ..bi_datasets.models import FileUpload

        file_connections = Connection.objects.filter(
            owner=request.user,
            connector_type__icontains='file'
        )

        result = {}

        for connection in file_connections:
            try:
                files = FileUpload.objects.filter(connection=connection, owner=request.user)
                files_data = []

                for file in files:
                    file_path = file.file.path if file.file else None
                    exists = file_path and os.path.exists(file_path)
                    files_data.append({
                        'id': file.id,
                        'name': file.name or file.original_filename or '',
                        'file_path': file_path,
                        'missing': not exists,
                        'exists': exists,
                        'status': 'ok' if exists else 'missing'
                    })

                has_missing_files = len(files_data) == 0
                has_problematic_files = any(
                    file.get('missing', False) or
                    not file.get('exists', False) or
                    file.get('status') in ['missing', 'error']
                    for file in files_data
                )

                result[connection.id] = {
                    'hasMissingFiles': has_missing_files,
                    'hasProblematicFiles': has_problematic_files,
                    'filesCount': len(files_data),
                    'files': files_data
                }

            except Exception as e:
                result[connection.id] = {
                    'hasMissingFiles': True,
                    'hasProblematicFiles': True,
                    'filesCount': 0,
                    'error': str(e)
                }

        return Response(result)
