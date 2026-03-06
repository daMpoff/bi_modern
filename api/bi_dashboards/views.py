import re

from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from src.core.utils.mixins import SwaggerSafeMixin

from .models import Dashboard, DashboardItem
from ..bi_pipelines.models import PipelineChart
from .serializers import (
    DashboardSerializer,
    DashboardWriteSerializer,
    DashboardShortSerializer,
    DashboardItemSerializer,
)
from .block_data import get_block_data

_PARAMS_KEY_RE = re.compile(r'^params\[(.+)\]$')


def _normalize_query_params(query_params, exclude_keys=None):
    """Flat dict for pipeline params. Keys like params[glucose] become glucose."""
    exclude = set(exclude_keys or []) | {'format'}
    out = {}
    for k, v in (query_params or {}).items():
        if k in exclude:
            continue
        val = v[0] if isinstance(v, list) else v
        m = _PARAMS_KEY_RE.match(k)
        if m:
            out[m.group(1)] = val
        else:
            out[k] = val
    return out


class DashboardListCreateView(SwaggerSafeMixin, generics.ListCreateAPIView):
    queryset = Dashboard.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Dashboard.objects.none()
        return Dashboard.objects.filter(owner=self.request.user).select_related('owner')

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return DashboardShortSerializer
        return DashboardWriteSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DashboardDetailView(SwaggerSafeMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Dashboard.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Dashboard.objects.none()
        return Dashboard.objects.filter(owner=self.request.user).prefetch_related(
            'pages__items'
        )

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return DashboardSerializer
        return DashboardWriteSerializer


class DashboardItemListCreateView(SwaggerSafeMixin, generics.ListCreateAPIView):
    queryset = DashboardItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DashboardItemSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DashboardItem.objects.none()
        page_id = self.request.query_params.get('page')
        if page_id:
            return DashboardItem.objects.filter(page_id=page_id).select_related('page__dashboard')
        return DashboardItem.objects.none()

    def perform_create(self, serializer):
        page_id = self.request.data.get('page')
        if page_id:
            from .models import DashboardPage
            try:
                page = DashboardPage.objects.select_related('dashboard').get(id=page_id)
                if page.dashboard.owner != self.request.user:
                    raise permissions.PermissionDenied("У вас нет доступа к этой странице дашборда")
                serializer.save(page=page)
            except DashboardPage.DoesNotExist:
                raise permissions.PermissionDenied("Страница дашборда не найдена")


class DashboardItemDetailView(SwaggerSafeMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = DashboardItem.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DashboardItemSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DashboardItem.objects.none()
        return DashboardItem.objects.filter(
            page__dashboard__owner=self.request.user
        ).select_related('page__dashboard')

    def perform_destroy(self, instance):
        chart_id = None
        if instance.type in ('График', 'Чарт') and instance.config:
            chart_id = instance.config.get('pipelineChartId')
        instance.delete()
        if not chart_id:
            return
        remaining = DashboardItem.objects.filter(
            type__in=['График', 'Чарт'],
            config__pipelineChartId=chart_id
        ).count()
        if remaining > 0:
            return
        chart = PipelineChart.objects.filter(
            pk=chart_id,
            owner=self.request.user
        ).select_related('pipeline').first()
        if not chart or not getattr(chart.pipeline, 'is_dashboard_only', False):
            return
        pipeline = chart.pipeline
        charts_count = pipeline.charts.count()
        chart.delete()
        if charts_count == 1:
            pipeline.delete()


class DashboardItemDataView(SwaggerSafeMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if getattr(self, 'swagger_fake_view', False):
            return Response({'chartData': []})
        item = get_object_or_404(
            DashboardItem.objects.select_related('page__dashboard').filter(
                page__dashboard__owner=request.user
            ),
            pk=pk
        )
        params = _normalize_query_params(request.query_params)
        data = get_block_data(item, request.user, params=params)
        return Response({'chartData': data})
