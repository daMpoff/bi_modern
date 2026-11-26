from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache.backends.locmem import LocMemCache
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate

from ..bi_pipelines.models import Pipeline
from ..bi_pipelines.serializers import PipelineChartSerializer
from ..bi_pipelines.views import PipelineExecuteAsyncView, PipelineTaskStatusView
from ..execution.result_cache import task_key, task_owner_key


class PipelineAsyncTests(SimpleTestCase):
    def setUp(self):
        self.result_cache = LocMemCache('pipeline-api-regressions', {})
        self.result_cache.clear()
        self.user = SimpleNamespace(pk=17, id=17, is_authenticated=True)
        self.pipeline = SimpleNamespace(pk=21, graph_data={'nodes': [{'id': 'out'}], 'edges': []})

    def request(self, method, payload=None):
        req = getattr(APIRequestFactory(), method)('/', payload or {}, format='json')
        force_authenticate(req, user=self.user)
        return req

    def test_status_does_not_read_another_users_celery_result(self):
        self.result_cache.set(task_owner_key('other'), {'user_id': 18, 'pipeline_id': 21})
        with patch('modules.bi_analysis_modern.api.bi_pipelines.views.execution_cache', return_value=self.result_cache), \
                patch('celery.result.AsyncResult') as backend:
            response = PipelineTaskStatusView.as_view()(self.request('get'), task_id='other')
        self.assertEqual(response.status_code, 404)
        backend.assert_not_called()

    def test_status_preserves_total_rows_instead_of_sample_length(self):
        self.result_cache.set(task_owner_key('own'), {'user_id': 17, 'pipeline_id': 21})
        self.result_cache.set(task_key('own'), {'chartData': [{'x': 1}], 'rows_count': 9000})
        task = Mock()
        task.failed.return_value = False
        task.successful.return_value = True
        with patch('modules.bi_analysis_modern.api.bi_pipelines.views.execution_cache', return_value=self.result_cache), \
                patch.object(Pipeline.objects, 'filter') as pipelines, \
                patch('celery.result.AsyncResult', return_value=task):
            pipelines.return_value.exists.return_value = True
            response = PipelineTaskStatusView.as_view()(self.request('get'), task_id='own')
        self.assertEqual(response.data['rows_count'], 9000)

    def test_publish_failure_returns_503_and_removes_task_binding(self):
        with patch('modules.bi_analysis_modern.api.bi_pipelines.views.execution_cache', return_value=self.result_cache), \
                patch.object(Pipeline.objects, 'get', return_value=self.pipeline), \
                patch('modules.bi_analysis_modern.api.tasks.execute_pipeline_async.apply_async', side_effect=RuntimeError('offline')) as publish:
            with self.assertLogs('modules.bi_analysis_modern.api.bi_pipelines.views', level='ERROR'):
                response = PipelineExecuteAsyncView.as_view()(self.request('post'), pk=21)
        task_id = publish.call_args.kwargs['task_id']
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(self.result_cache.get(task_owner_key(task_id)))

    def test_async_execution_handles_unset_preview_limit(self):
        from django.contrib.auth import get_user_model
        from ..tasks import execute_pipeline_async
        rows = [{'x': 1}, {'x': 2}, {'x': 3}]
        with patch.object(get_user_model().objects, 'get', return_value=self.user), \
                patch.object(Pipeline.objects, 'get', return_value=self.pipeline), \
                patch('modules.bi_analysis_modern.api.execution.graph_execute.execute_graph', return_value={'chartData': rows}), \
                patch('modules.bi_analysis_modern.api.config.EXECUTE_PREVIEW_ROWS', None), \
                patch('modules.bi_analysis_modern.api.config.EXECUTE_CHUNK_SIZE', 2), \
                patch('modules.bi_analysis_modern.api.execution.result_cache.execution_cache', return_value=self.result_cache):
            execute_pipeline_async.push_request(id='sample')
            try:
                result = execute_pipeline_async.run(21, 17)
            finally:
                execute_pipeline_async.pop_request()
        self.assertEqual(result['rows_count'], 3)
        self.assertEqual(self.result_cache.get(task_key('sample'))['chartData'], rows[:2])

    def test_chart_cannot_reference_another_users_pipeline(self):
        serializer = PipelineChartSerializer(context={'request': SimpleNamespace(user=self.user)})
        with self.assertRaises(ValidationError):
            serializer.validate_pipeline(SimpleNamespace(owner_id=18))
