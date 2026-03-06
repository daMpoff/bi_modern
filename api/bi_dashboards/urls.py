from django.urls import path

from .views import (
    DashboardListCreateView,
    DashboardDetailView,
    DashboardItemListCreateView,
    DashboardItemDetailView,
    DashboardItemDataView,
)

urlpatterns = [
    path('', DashboardListCreateView.as_view(), name='dashboard-list-create'),
    path('<int:pk>/', DashboardDetailView.as_view(), name='dashboard-detail'),
    path('items/', DashboardItemListCreateView.as_view(), name='dashboard-item-list-create'),
    path('items/<int:pk>/', DashboardItemDetailView.as_view(), name='dashboard-item-detail'),
    path('items/<int:pk>/data/', DashboardItemDataView.as_view(), name='dashboard-item-data'),
]
