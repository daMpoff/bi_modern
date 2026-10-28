from types import SimpleNamespace
from unittest.mock import patch

from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, override_settings
from django.urls import include, path, resolve
from rest_framework.test import APIRequestFactory, force_authenticate

from .bi_connections.views import CheckConnectionView
from .bi_connections.models import Connection
from .bi_connections.serializers import ConnectionSerializer
from .views import GraphExecuteView


urlpatterns = [path('api/bi_analysis_modern/', include('modules.bi_analysis_modern.api.urls'))]


@override_settings(ROOT_URLCONF=__name__)
class ModernRoutingTests(SimpleTestCase):
    def test_urls_resolve_inside_modern(self):
        for suffix in (
            'bi_connections/', 'bi_connections/42/',
            'bi_connections/42/tables/', 'bi_connections/files-status/',
            'bi_datasets/upload/', 'bi_datasets/upload/42/',
            'bi_datasets/upload/finalize/', 'bi_datasets/connection/42/files/',
            'bi_dashboards/', 'bi_dashboards/42/',
            'pipelines/', 'pipelines/42/', 'pipelines/charts/',
            'graphs/execute/', 'graphs/suggest-join-keys/', 'data_source/columns/',
        ):
            with self.subTest(url=suffix):
                match = resolve('/api/bi_analysis_modern/' + suffix)
                self.assertTrue(match.func.view_class.__module__.startswith('modules.bi_analysis_modern.'))

    def test_api_requires_authentication(self):
        request = APIRequestFactory().post('/api/bi_analysis_modern/graphs/execute/', {}, format='json')
        self.assertIn(GraphExecuteView.as_view()(request).status_code, (401, 403))

    def test_graph_request_calls_modern_executor(self):
        payload = {'nodes': [], 'edges': []}
        request = APIRequestFactory().post('/api/bi_analysis_modern/graphs/execute/', payload, format='json')
        user = SimpleNamespace(pk=123, is_authenticated=True)
        force_authenticate(request, user=user)
        with patch('modules.bi_analysis_modern.api.views.execute_graph', return_value={'chartData': []}) as execute:
            response = GraphExecuteView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        execute.assert_called_once_with([], [], user, preview=False)

    def test_connection_check_uses_modern_connector(self):
        request = APIRequestFactory().post('/api/bi_analysis_modern/bi_connections/check-connection/', {
            'type': 'postgresql', 'host': 'localhost', 'port': 5432,
            'username': 'reader', 'password': 'test', 'database': 'analytics',
        }, format='json')
        force_authenticate(request, user=SimpleNamespace(pk=123, is_authenticated=True))
        with patch('modules.bi_analysis_modern.api.bi_connections.views.CheckConnection.check_postgresql',
                   return_value=(True, 'OK')) as connector:
            response = CheckConnectionView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        connector.assert_called_once_with('localhost', 5432, 'reader', 'test', 'analytics')

    def test_migration_graph_has_no_missing_core_dependencies(self):
        loader = MigrationLoader(None)
        loader.graph.validate_consistency()
        self.assertIn(('bi_analysis_modern', '0002_dashboard_route_namespace'), loader.graph.nodes)

    def test_renaming_connection_keeps_credentials(self):
        connection = Connection(name='Before', connector_type='postgres', config={
            'host': 'localhost', 'database': 'analytics', 'password': 'test',
        })
        serializer = ConnectionSerializer(connection, data={'name': 'After'}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(connection, 'save'):
            serializer.save()
        self.assertEqual(connection.name, 'After')
        self.assertEqual(connection.config['password'], 'test')
        self.assertEqual(connection.config['database'], 'analytics')

    def test_partial_connection_config_keeps_database_and_password(self):
        connection = Connection(name='Connection', connector_type='postgres', config={
            'host': 'before', 'database': 'analytics', 'password': 'test',
        })
        serializer = ConnectionSerializer(connection, data={'config': {'host': 'after'}}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(connection, 'save'):
            serializer.save()
        self.assertEqual(connection.config, {'host': 'after', 'database': 'analytics', 'password': 'test'})
