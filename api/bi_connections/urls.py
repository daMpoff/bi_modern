from django.urls import path

from .views import (
    ConnectionListCreateView,
    ConnectionDetailView,
    CheckConnectionView,
    ConnectionTablesView,
    ConnectionTableColumnsView,
    ConnectionTablePreviewView,
    ConnectionFilesStatusView,
)

urlpatterns = [
    path('', ConnectionListCreateView.as_view(), name='connection-list-create'),
    path('<int:pk>/', ConnectionDetailView.as_view(), name='connection-detail'),
    path("check-connection/", CheckConnectionView.as_view(), name="check-connection"),
    path('<int:connection_id>/tables/', ConnectionTablesView.as_view(), name='connection-tables'),
    path('<int:connection_id>/tables/columns/', ConnectionTableColumnsView.as_view(), name='connection-table-columns'),
    path('<int:connection_id>/tables/preview/', ConnectionTablePreviewView.as_view(), name='connection-table-preview'),
    path('files-status/', ConnectionFilesStatusView.as_view(), name='connection-files-status'),
]
