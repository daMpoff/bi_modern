import json
import logging
import re
import uuid

from django.http import HttpResponse as DjangoHttpResponse
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..bi_dashboards.utils import remove_dashboard_blocks_by_chart_id
from ..config import EXECUTE_PREVIEW_ROWS, EXECUTE_CHUNK_SIZE, CHART_MAX_POINTS
from ..graph_execute import execute_graph
from ..execution.node_handlers import filter_chart_data_by_config
from ..lineage import compute_lineage
from ..pipeline_types import row_count, to_rows_slice, to_json_bytes
from ..downsampling import downsample_for_chart
from .models import Pipeline, PipelineChart
from .serializers import PipelineSerializer, PipelineChartSerializer

logger = logging.getLogger(__name__)

_PARAMS_KEY_RE = re.compile(r'^params\[(.+)\]$')

from ..execution.result_cache import (
    put_result as _execute_cache_put,
    get_result as _execute_cache_get,
    execution_cache, task_key, task_owner_key, ASYNC_RESULT_TTL,
)


def _normalize_query_params(query_params, exclude_keys=None):
    """Build flat dict for execute_graph. Keys like params[glucose] become glucose."""
    exclude_keys = set(exclude_keys or []) | {'format'}
    out = {}
    for k, v in (query_params or {}).items():
        if k in exclude_keys:
            continue
        val = v[0] if isinstance(v, list) else v
        m = _PARAMS_KEY_RE.match(k)
        if m:
            out[m.group(1)] = val
        else:
            out[k] = val
    return out


class PipelineListCreateView(generics.ListCreateAPIView):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset.none()
        qs = self.queryset.filter(owner=self.request.user)
        if self.request.query_params.get('include_dashboard_only') != 'true':
            qs = qs.filter(is_dashboard_only=False)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PipelineDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Pipeline.objects.all()
    serializer_class = PipelineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        if instance.is_dashboard_only:
            chart_ids = list(instance.charts.values_list('id', flat=True))
            for chart_id in chart_ids:
                remove_dashboard_blocks_by_chart_id(chart_id)
        instance.delete()


class PipelineExecuteAsyncView(APIView):
    """Асинхронное выполнение пайплайна (Celery). Возвращает task_id для опроса."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            pipeline = Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        if not nodes:
            return Response({'task_id': None, 'error': 'Пайплайн пуст'})

        params = (request.data if isinstance(request.data, dict) else {}).get('params') or {}
        from ..tasks import execute_pipeline_async
        task_id = str(uuid.uuid4())
        result_cache = execution_cache()
        result_cache.set(task_owner_key(task_id), {'user_id': request.user.id, 'pipeline_id': pk}, ASYNC_RESULT_TTL)
        try:
            execute_pipeline_async.apply_async(args=(pk, request.user.id, params), task_id=task_id)
        except Exception:
            result_cache.delete(task_owner_key(task_id))
            logger.exception('Не удалось отправить задачу исполнения конвейера')
            return Response({'error': 'Очередь выполнения недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'task_id': task_id})


class PipelineTaskStatusView(APIView):
    """Статус и результат асинхронной задачи пайплайна."""
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        from celery.result import AsyncResult
        result_cache = execution_cache()
        owner = result_cache.get(task_owner_key(task_id))
        if (not owner or owner.get('user_id') != request.user.id
                or not Pipeline.objects.filter(pk=owner['pipeline_id'], owner=request.user).exists()):
            return Response({'error': 'Задача не найдена'}, status=status.HTTP_404_NOT_FOUND)
        task = AsyncResult(task_id)
        if task.failed():
            return Response({
                'status': 'FAILURE',
                'error': str(task.result) if task.result else 'Ошибка выполнения',
            })
        if task.successful():
            result = result_cache.get(task_key(task_id))
            if result:
                return Response({
                    'status': 'SUCCESS',
                    'data': result.get('chartData', []),
                    'error': result.get('error'),
                    'rows_count': result.get('rows_count', len(result.get('chartData', []))),
                })
            return Response({
                'status': 'SUCCESS',
                'data': [],
                'error': 'Результат истёк (TTL 1ч)',
            })
        return Response({'status': task.state})


class PipelineExecuteView(APIView):
    """Выполнить пайплайн и вернуть выходные данные."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            pipeline = Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])

        if not nodes:
            return Response({'data': [], 'error': 'Пайплайн пуст'})

        params = (request.data if isinstance(request.data, dict) else {}).get('params') or {}

        try:
            result = execute_graph(nodes, edges, request.user, params=params, preview=False)
        except Exception as e:
            logger.exception('Pipeline execute error (pk=%s)', pk)
            return Response({'data': [], 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        raw_df = result.get('_raw_df')
        total_rows = result.get('_total_rows')
        error = result.get('error')

        if raw_df is not None and hasattr(raw_df, 'head'):
            rc = total_rows if total_rows is not None else row_count(raw_df)
            columns = list(raw_df.columns)
            result_set_id = str(uuid.uuid4())
            _execute_cache_put(result_set_id, raw_df, columns, rc, request.user.id, pk)
            chunk_size = EXECUTE_CHUNK_SIZE
            first_slice = raw_df.slice(0, chunk_size)
            data_json = to_json_bytes(first_slice, None)
            rows_sent = min(rc, chunk_size)
            error_json = json.dumps(error, ensure_ascii=False, default=str).encode('utf-8')
            cols_json = json.dumps(columns, ensure_ascii=False).encode('utf-8')
            body = (
                b'{"data":' + data_json + b',"error":' + error_json +
                b',"rows_count":' + str(rc).encode() + b',"columns":' + cols_json +
                b',"result_set_id":' + json.dumps(result_set_id).encode() + b'}'
            )
        elif raw_df is not None and isinstance(raw_df, list) and raw_df:
            rc = total_rows if total_rows is not None else len(raw_df)
            columns = list(raw_df[0].keys()) if raw_df else []
            result_set_id = str(uuid.uuid4())
            _execute_cache_put(result_set_id, raw_df, columns, rc, request.user.id, pk)
            chunk_size = EXECUTE_CHUNK_SIZE
            first_chunk = raw_df[:chunk_size]
            data_json = json.dumps(first_chunk, ensure_ascii=False, default=str).encode('utf-8')
            rows_sent = len(first_chunk)
            error_json = json.dumps(error, ensure_ascii=False, default=str).encode('utf-8')
            cols_json = json.dumps(columns, ensure_ascii=False).encode('utf-8')
            body = (
                b'{"data":' + data_json + b',"error":' + error_json +
                b',"rows_count":' + str(rc).encode() + b',"columns":' + cols_json +
                b',"result_set_id":' + json.dumps(result_set_id).encode() + b'}'
            )
        else:
            output_data = result.get('chartData', [])
            rc = len(output_data)
            chunk_size = EXECUTE_CHUNK_SIZE
            first_chunk = output_data[:chunk_size]
            data_json = json.dumps(first_chunk, ensure_ascii=False, default=str).encode('utf-8')
            rows_sent = len(first_chunk)
            columns = list(output_data[0].keys()) if output_data else []
            error_json = json.dumps(error, ensure_ascii=False, default=str).encode('utf-8')
            cols_json = json.dumps(columns, ensure_ascii=False).encode('utf-8')
            body = (
                b'{"data":' + data_json + b',"error":' + error_json +
                b',"rows_count":' + str(rc).encode() + b',"columns":' + cols_json +
                b',"result_set_id":null}'
            )

        resp = DjangoHttpResponse(body, content_type='application/json')
        resp['X-Rows-Count'] = str(rc)
        return resp


class PipelineExecuteChunkView(APIView):
    """Подгрузка чанка данных по result_set_id (после execute)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        result_set_id = (request.query_params.get('result_set_id') or '').strip()
        if not result_set_id:
            return Response(
                {'error': 'result_set_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            offset = max(0, int(request.query_params.get('offset', 0)))
            limit = min(max(1, int(request.query_params.get('limit', EXECUTE_CHUNK_SIZE))), 10000)
        except (TypeError, ValueError):
            offset, limit = 0, EXECUTE_CHUNK_SIZE
        entry = _execute_cache_get(result_set_id, request.user.id, pk)
        if not entry:
            return Response(
                {'error': 'Результат не найден или истёк'},
                status=status.HTTP_404_NOT_FOUND
            )
        raw_df = entry['raw_df']
        if raw_df is not None and hasattr(raw_df, 'slice'):
            chunk = raw_df.slice(offset, limit)
            data_json = to_json_bytes(chunk, None)
        elif isinstance(raw_df, list):
            chunk = raw_df[offset:offset + limit]
            data_json = json.dumps(chunk, ensure_ascii=False, default=str).encode('utf-8')
        else:
            return DjangoHttpResponse(b'{"data":[]}', content_type='application/json')
        return DjangoHttpResponse(
            b'{"data":' + data_json + b'}',
            content_type='application/json'
        )


class PipelinePreviewView(APIView):
    """Предпросмотр данных пайплайна."""
    permission_classes = [IsAuthenticated]
    MAX_PREVIEW_ROWS = EXECUTE_PREVIEW_ROWS

    def post(self, request, pk):
        try:
            pipeline = Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])

        if not nodes:
            return Response({'data': [], 'columns': [], 'error': 'Пайплайн пуст'})

        params = (request.data if isinstance(request.data, dict) else {}).get('params') or {}

        try:
            result = execute_graph(nodes, edges, request.user, params=params, preview=True)
        except Exception as e:
            logger.exception('Pipeline preview error (pk=%s)', pk)
            return Response(
                {'data': [], 'columns': [], 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        raw_df = result.get('_raw_df')
        total_rows = result.get('_total_rows')
        error = result.get('error')

        if raw_df is not None and hasattr(raw_df, 'columns'):
            columns = list(raw_df.columns)
            total = total_rows if total_rows is not None else row_count(raw_df)
            data_json = to_json_bytes(raw_df, self.MAX_PREVIEW_ROWS)
        else:
            output_data = result.get('chartData', []) or []
            total = len(output_data)
            columns = list(output_data[0].keys()) if output_data else []
            data_json = json.dumps(output_data[:self.MAX_PREVIEW_ROWS], ensure_ascii=False, default=str).encode('utf-8')

        cols_json = json.dumps(columns, ensure_ascii=False).encode('utf-8')
        error_json = json.dumps(error, ensure_ascii=False, default=str).encode('utf-8')
        body = b'{"data":' + data_json + b',"columns":' + cols_json + b',"total_rows":' + str(total).encode() + b',"error":' + error_json + b'}'
        return DjangoHttpResponse(body, content_type='application/json')


def _infer_field_type(value):
    if value is None:
        return 'string'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    if hasattr(value, 'year'):
        return 'date'
    return 'string'


class PipelineFieldsView(APIView):
    """Список выходных полей пайплайна (имя и тип)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            pipeline = Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        if not nodes:
            return Response({'fields': [], 'error': None})

        params = _normalize_query_params(request.query_params)
        try:
            result = execute_graph(nodes, edges, request.user, params=params, preview=True)
        except Exception as e:
            logger.exception('Pipeline fields error (pk=%s)', pk)
            return Response({'fields': [], 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        raw_df = result.get('_raw_df')
        error = result.get('error')

        if raw_df is not None and hasattr(raw_df, 'columns') and hasattr(raw_df, 'dtypes'):
            row_sample = to_rows_slice(raw_df, 1)
            if row_sample:
                fields = [{'name': key, 'type': _infer_field_type(row_sample[0].get(key))} for key in row_sample[0]]
            else:
                fields = [{'name': col, 'type': 'string'} for col in raw_df.columns]
            return Response({'fields': fields, 'error': error})

        output_data = result.get('chartData', []) or []
        if not output_data:
            return Response({'fields': [], 'error': error})
        row = output_data[0]
        fields = [{'name': key, 'type': _infer_field_type(row.get(key))} for key in row.keys()]
        return Response({'fields': fields, 'error': error})


class PipelineFieldValuesView(APIView):
    """Уникальные значения поля (для выпадающих селекторов)."""
    permission_classes = [IsAuthenticated]
    MAX_ROWS_SCAN = 10000
    DEFAULT_VALUES_LIMIT = 100

    def get(self, request, pk, field_name):
        try:
            pipeline = Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        if not nodes:
            return Response({'values': [], 'error': None})

        limit = request.query_params.get('limit')
        try:
            limit = int(limit) if limit is not None else self.DEFAULT_VALUES_LIMIT
            limit = min(max(1, limit), 500)
        except (TypeError, ValueError):
            limit = self.DEFAULT_VALUES_LIMIT

        params = _normalize_query_params(request.query_params, exclude_keys=['limit'])
        try:
            result = execute_graph(nodes, edges, request.user, params=params, preview=True)
        except Exception as e:
            logger.exception('Pipeline field values error (pk=%s)', pk)
            return Response({'values': [], 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        error = result.get('error')
        raw_df = result.get('_raw_df')

        if raw_df is not None and hasattr(raw_df, 'columns'):
            try:
                import polars as pl
                if field_name in raw_df.columns:
                    unique_series = raw_df[field_name].unique().head(limit)
                    values = unique_series.to_list()
                    return Response({'values': values, 'error': error})
            except Exception:
                pass

        output_data = result.get('chartData', []) or []
        seen = set()
        values = []
        for row in output_data[:self.MAX_ROWS_SCAN]:
            if field_name not in row:
                continue
            v = row[field_name]
            key = (v if isinstance(v, (int, float, bool)) or v is None else str(v))
            if key not in seen:
                seen.add(key)
                values.append(v)
                if len(values) >= limit:
                    break
        return Response({'values': values, 'error': error})


class PipelineLineageView(APIView):
    """Data Lineage: цепочка узлов от источников до графика."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            pipeline = Pipeline.objects.get(pk=pk, owner=request.user)
        except Pipeline.DoesNotExist:
            return Response(
                {'error': 'Пайплайн не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        result = compute_lineage(nodes, edges)
        if result.get('error'):
            return Response(result)

        include_counts = request.query_params.get('include_counts', '').lower() in ('1', 'true')
        if include_counts and result.get('nodes'):
            params = _normalize_query_params(request.query_params, exclude_keys=['include_counts'])
            try:
                exec_result = execute_graph(
                    nodes, edges, request.user,
                    params=params,
                    include_node_row_counts=True,
                    preview=True,
                )
                node_row_counts = exec_result.get('node_row_counts')
                if node_row_counts is not None:
                    for node in result['nodes']:
                        node['rows_count'] = node_row_counts.get(node['id'])
                if exec_result.get('error'):
                    result['error'] = exec_result.get('error')
            except Exception as e:
                logger.exception('Lineage counts error (pk=%s)', pk)
                result['error'] = str(e)
        return Response(result)


class PipelineChartListCreateView(generics.ListCreateAPIView):
    queryset = PipelineChart.objects.all()
    serializer_class = PipelineChartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset.none()
        qs = self.queryset.filter(owner=self.request.user).select_related('pipeline')
        pipeline_id = self.request.query_params.get('pipeline')
        if pipeline_id:
            qs = qs.filter(pipeline_id=pipeline_id)
        elif self.request.query_params.get('include_dashboard_only') != 'true':
            qs = qs.filter(pipeline__is_dashboard_only=False)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PipelineChartDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PipelineChart.objects.select_related('pipeline').all()
    serializer_class = PipelineChartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return self.queryset.none()
        return self.queryset.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        pipeline = instance.pipeline
        is_dashboard_only = pipeline.is_dashboard_only
        charts_count = pipeline.charts.count()
        remove_dashboard_blocks_by_chart_id(instance.id)
        instance.delete()
        if is_dashboard_only and charts_count == 1:
            pipeline.delete()


class PipelineChartDataView(APIView):
    """Получить данные для рендера графика с автоматическим downsampling."""
    permission_classes = [IsAuthenticated]

    ARROW_MIME = 'application/vnd.apache.arrow.stream'

    def _wants_arrow(self, request):
        accept = request.META.get('HTTP_ACCEPT', '')
        return self.ARROW_MIME in accept

    def get(self, request, pk):
        try:
            chart = PipelineChart.objects.select_related('pipeline').get(
                pk=pk, owner=request.user
            )
        except PipelineChart.DoesNotExist:
            return Response(
                {'error': 'График не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        pipeline = chart.pipeline
        graph_data = pipeline.graph_data or {}
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])

        if not nodes:
            return Response({'data': [], 'chart_config': chart.chart_config, 'error': 'Пайплайн пуст'})

        params = _normalize_query_params(request.query_params)

        try:
            max_points = min(int(request.query_params.get('max_points', CHART_MAX_POINTS)), 200000)
        except (TypeError, ValueError):
            max_points = CHART_MAX_POINTS

        try:
            result = execute_graph(nodes, edges, request.user, params=params, preview=False)
        except Exception as e:
            logger.exception('Pipeline chart data error (chart_pk=%s)', pk)
            return Response(
                {'data': [], 'chart_config': chart.chart_config, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        error = result.get('error')
        chart_config = chart.chart_config or {}

        raw_df = result.get('_raw_df')
        total_rows = result.get('_total_rows')

        if raw_df is not None and hasattr(raw_df, 'columns'):
            import polars as pl

            x_field = (chart_config.get('xField') or '').strip()
            y_fields = chart_config.get('yFields') or []
            if isinstance(y_fields, str):
                y_fields = [y_fields] if y_fields else []
            y_fields = [f for f in y_fields if (f or '').strip()]
            color_field = (chart_config.get('colorField') or '').strip()

            keep_cols = []
            if x_field and x_field in raw_df.columns:
                keep_cols.append(x_field)
            for yf in y_fields:
                if yf in raw_df.columns and yf not in keep_cols:
                    keep_cols.append(yf)
            if color_field and color_field in raw_df.columns and color_field not in keep_cols:
                keep_cols.append(color_field)

            filtered_df = raw_df.select(keep_cols) if keep_cols else raw_df

            chart_type = chart.chart_type or 'bar'
            downsampled_df = downsample_for_chart(
                filtered_df,
                chart_type=chart_type,
                x_field=x_field,
                y_fields=y_fields,
                max_points=max_points,
            )

            rows = downsampled_df.to_dicts()
            actual_total = total_rows if total_rows is not None else row_count(raw_df)
        else:
            output_data = result.get('chartData', [])
            rows = filter_chart_data_by_config(output_data, chart_config)
            actual_total = len(rows)
            downsampled_df = None

        if self._wants_arrow(request) and downsampled_df is not None and hasattr(downsampled_df, 'to_arrow'):
            import io
            try:
                arrow_table = downsampled_df.to_arrow()
                buf = io.BytesIO()
                import pyarrow as pa
                writer = pa.ipc.new_stream(buf, arrow_table.schema)
                writer.write_table(arrow_table)
                writer.close()
                return DjangoHttpResponse(
                    buf.getvalue(),
                    content_type=self.ARROW_MIME,
                    headers={
                        'X-Total-Rows': str(actual_total),
                        'X-Downsampled': '1' if actual_total != len(rows) else '0',
                    },
                )
            except Exception:
                pass

        return Response({
            'rows': rows,
            'chart_config': chart_config,
            'chart_type': chart.chart_type,
            'engine': chart.engine,
            'name': chart.name,
            'total_rows': actual_total,
            'downsampled': actual_total != len(rows),
            'error': error,
        })
