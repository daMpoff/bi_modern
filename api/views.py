import time

from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


from .data_source_provider import get_columns_meta
from .graph_execute import execute_graph
from .suggest_join_keys import suggest_join_keys


class GraphExecuteView(APIView):
    """
    POST bi_analysis_modern/graphs/execute/
    Body: { "nodes": [ { "id", "type", "data": { "config": {} } } ], "edges": [ { "source", "target" } ] }
    Returns: { "chartData": [ ... ], "columns": [...], "rows_count": N } или { "chartData": [], "error": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .config import CHART_MAX_POINTS
        from .downsampling import uniform_sample
        from .pipeline_types import row_count as _row_count

        nodes = (request.data or {}).get('nodes') or []
        edges = (request.data or {}).get('edges') or []
        result = execute_graph(nodes, edges, request.user, preview=False)

        raw_df = result.pop('_raw_df', None)
        total_rows = result.pop('_total_rows', None)

        PREVIEW_LIMIT = 10000
        if not result.get('chartData') and raw_df is not None and hasattr(raw_df, 'columns'):
            n = total_rows if total_rows is not None else _row_count(raw_df)
            sampled = uniform_sample(raw_df, PREVIEW_LIMIT)
            result['chartData'] = sampled.to_dicts()
            result['columns'] = list(raw_df.columns)
            result['rows_count'] = n
        elif not result.get('chartData') and raw_df is not None and isinstance(raw_df, list):
            n = total_rows if total_rows is not None else len(raw_df)
            result['chartData'] = raw_df[:PREVIEW_LIMIT]
            result['columns'] = list(raw_df[0].keys()) if raw_df else []
            result['rows_count'] = n
        else:
            chart_data = result.get('chartData', [])
            result['rows_count'] = total_rows if total_rows is not None else len(chart_data)
            if chart_data:
                result['columns'] = list(chart_data[0].keys())

        return Response(result)


class SuggestJoinKeysView(APIView):
    """
    POST bi_analysis_modern/graphs/suggest-join-keys/
    Body: { "leftSource": { "config": {...} }, "rightSource": { "config": {...} } }
    Returns: { "suggestions": [{ "leftKey", "rightKey" }], "leftColumns": [...], "rightColumns": [...] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        left_config = (data.get('leftSource') or {}).get('config') or {}
        right_config = (data.get('rightSource') or {}).get('config') or {}
        result = suggest_join_keys(left_config, right_config, request.user)
        return Response(result)


class DataSourceColumnsView(APIView):
    """
    POST bi_analysis_modern/data_source/columns/
    Body: { "connection_id": int, "main_table": { "id", "name", "schema", "file_id", ... } }
    Returns: { "columns": [ { "name": str, "type": str }, ... ] }
    Единый endpoint для колонок таблицы БД или файла.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data or {}
        connection_id = data.get('connection_id')
        main_table = data.get('main_table')
        if connection_id is None or main_table is None:
            return Response(
                {'columns': [], 'error': 'connection_id и main_table обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            columns = get_columns_meta(int(connection_id), main_table, request.user)
            return Response({'columns': columns})
        except Exception as e:
            return Response(
                {'columns': [], 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
