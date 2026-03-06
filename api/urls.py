from django.urls import path, include

from .views import (
    DataSourceColumnsView,
    GraphExecuteView,
    SuggestJoinKeysView,
)

urlpatterns = [
    path('bi_datasets/', include('modules.bi_analysis_modern.api.bi_datasets.urls')),
    path('bi_connections/', include('modules.bi_analysis_modern.api.bi_connections.urls')),
    path('bi_charts/', include('modules.bi_analysis_modern.api.bi_charts.urls')),
    path('bi_dashboards/', include('modules.bi_analysis_modern.api.bi_dashboards.urls')),
    path('pipelines/', include('modules.bi_analysis_modern.api.bi_pipelines.urls')),
    path('data_source/columns/', DataSourceColumnsView.as_view(), name='data-source-columns'),
    path('graphs/execute/', GraphExecuteView.as_view(), name='graph-execute'),
    path('graphs/suggest-join-keys/', SuggestJoinKeysView.as_view(), name='suggest-join-keys'),
]
