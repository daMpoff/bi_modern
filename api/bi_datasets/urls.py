from django.urls import path

from .views import (
    TempUploadView,
    FileUploadDetailView,
    FinalizeUploadView,
    XlsxSheetListView,
    XlsxTempPreviewView,
    FilePreviewTaskStatusView,
    FileUploadByConnectionView,
)

urlpatterns = [
    path('upload/', TempUploadView.as_view(), name='temp-upload'),
    path('upload/<int:pk>/', FileUploadDetailView.as_view(), name='file-upload-detail'),
    path('upload/finalize/', FinalizeUploadView.as_view(), name='finalize-upload'),
    path('xlsx/sheets/', XlsxSheetListView.as_view(), name='xlsx-sheet-list'),
    path('xlsx/preview/', XlsxTempPreviewView.as_view(), name='xlsx-preview'),
    path('xlsx/preview/task-status/', FilePreviewTaskStatusView.as_view(), name='xlsx-preview-task-status'),
    path('connection/<int:connection_id>/files/', FileUploadByConnectionView.as_view(), name='fileupload-by-connection'),
]
