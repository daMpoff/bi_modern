"""
WebSocket URL routing for the BI analysis module.

WebSocket endpoints:
    ws://.../ws/bi/dashboard/{dashboard_id}/  — real-time dashboard updates
"""

from django.urls import re_path

from .consumers import DashboardConsumer

websocket_urlpatterns = [
    re_path(r'ws/bi/dashboard/(?P<dashboard_id>\w+)/$', DashboardConsumer.as_asgi()),
]
