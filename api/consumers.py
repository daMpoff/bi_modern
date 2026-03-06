"""
WebSocket consumers for real-time BI dashboard updates.

Architecture:
    - Each dashboard has its own channel group: `bi_dashboard_{dashboard_id}`
    - Clients connect via ws://.../ws/bi/dashboard/{dashboard_id}/
    - Server can push data updates, notifications, and status changes
    - Supports incremental data append and full refresh

Usage from backend code:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'bi_dashboard_{dashboard_id}',
        {
            'type': 'dashboard.data_update',
            'block_id': block_id,
            'action': 'append',   # 'append' | 'replace' | 'refresh'
            'rows': [...],
        }
    )
"""

import json
import logging

from channels.generic.websocket import AsyncJsonWebSocketConsumer

logger = logging.getLogger(__name__)


class DashboardConsumer(AsyncJsonWebSocketConsumer):
    """
    WebSocket consumer for a single dashboard.

    The client connects with a dashboard_id in the URL and is added
    to the corresponding channel group.  The server can push updates
    to all clients viewing that dashboard.
    """

    async def connect(self):
        self.dashboard_id = self.scope['url_route']['kwargs'].get('dashboard_id')
        if not self.dashboard_id:
            await self.close()
            return

        self.group_name = f'bi_dashboard_{self.dashboard_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        logger.info('WS connected: dashboard=%s channel=%s', self.dashboard_id, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info('WS disconnected: dashboard=%s code=%s', getattr(self, 'dashboard_id', '?'), close_code)

    async def receive_json(self, content, **kwargs):
        """
        Handle messages from the client.

        Supported client messages:
            { "action": "subscribe", "block_ids": [1, 2, 3] }
            { "action": "ping" }
        """
        action = content.get('action', '')

        if action == 'ping':
            await self.send_json({'type': 'pong'})
            return

        if action == 'subscribe':
            self.subscribed_blocks = set(content.get('block_ids', []))
            await self.send_json({
                'type': 'subscribed',
                'block_ids': list(self.subscribed_blocks),
            })
            return

        await self.send_json({
            'type': 'error',
            'message': f'Unknown action: {action}',
        })

    async def dashboard_data_update(self, event):
        block_id = event.get('block_id')

        if hasattr(self, 'subscribed_blocks') and self.subscribed_blocks:
            if block_id not in self.subscribed_blocks:
                return

        await self.send_json({
            'type': 'data_update',
            'block_id': block_id,
            'action': event.get('action', 'replace'),
            'rows': event.get('rows', []),
            'total_rows': event.get('total_rows'),
        })

    async def dashboard_notification(self, event):
        await self.send_json({
            'type': 'notification',
            'level': event.get('level', 'info'),
            'message': event.get('message', ''),
        })

    async def dashboard_status(self, event):
        await self.send_json({
            'type': 'status',
            'block_id': event.get('block_id'),
            'status': event.get('status', 'ready'),
            'error': event.get('error'),
        })


def push_dashboard_update(dashboard_id, block_id, rows, action='append', total_rows=None):
    """Push data update to all clients viewing a dashboard."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    group_name = f'bi_dashboard_{dashboard_id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'dashboard.data_update',
            'block_id': block_id,
            'action': action,
            'rows': rows,
            'total_rows': total_rows,
        }
    )


def push_dashboard_notification(dashboard_id, message, level='info'):
    """Push a notification to all clients viewing a dashboard."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    group_name = f'bi_dashboard_{dashboard_id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'dashboard.notification',
            'level': level,
            'message': message,
        }
    )
