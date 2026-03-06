from django.urls import path

from .views import (
    PipelineListCreateView,
    PipelineDetailView,
    PipelineExecuteView,
    PipelineExecuteChunkView,
    PipelineExecuteAsyncView,
    PipelineTaskStatusView,
    PipelinePreviewView,
    PipelineFieldsView,
    PipelineFieldValuesView,
    PipelineLineageView,
    PipelineChartListCreateView,
    PipelineChartDetailView,
    PipelineChartDataView,
)

urlpatterns = [
    path('', PipelineListCreateView.as_view(), name='pipeline-list-create'),
    path('<int:pk>/', PipelineDetailView.as_view(), name='pipeline-detail'),
    path('<int:pk>/execute/', PipelineExecuteView.as_view(), name='pipeline-execute'),
    path('<int:pk>/execute-chunk/', PipelineExecuteChunkView.as_view(), name='pipeline-execute-chunk'),
    path('<int:pk>/execute_async/', PipelineExecuteAsyncView.as_view(), name='pipeline-execute-async'),
    path('tasks/<str:task_id>/', PipelineTaskStatusView.as_view(), name='pipeline-task-status'),
    path('<int:pk>/preview/', PipelinePreviewView.as_view(), name='pipeline-preview'),
    path('<int:pk>/fields/', PipelineFieldsView.as_view(), name='pipeline-fields'),
    path('<int:pk>/lineage/', PipelineLineageView.as_view(), name='pipeline-lineage'),
    path('<int:pk>/fields/<str:field_name>/values/', PipelineFieldValuesView.as_view(), name='pipeline-field-values'),
    path('charts/', PipelineChartListCreateView.as_view(), name='pipeline-chart-list-create'),
    path('charts/<int:pk>/', PipelineChartDetailView.as_view(), name='pipeline-chart-detail'),
    path('charts/<int:pk>/data/', PipelineChartDataView.as_view(), name='pipeline-chart-data'),
]
