import io
from unittest.mock import patch

import polars as pl
from django.test import SimpleTestCase, override_settings

from .execution.python_executor import execute_isolated, NoRedirects
from .pipeline_data import execute_python_script, execute_python_script_polars
from ..sandbox.protocol import pack


class PythonExecutorClientTests(SimpleTestCase):
    def test_both_pipeline_engines_delegate_to_the_executor(self):
        with patch('modules.bi_analysis_modern.api.execution.python_executor.execute_isolated',
                   return_value=pl.DataFrame({'x': [2]})) as executor:
            self.assertEqual(execute_python_script([{'x': 1}], {'code': 'result = rows'}), [{'x': 2}])
            self.assertEqual(executor.call_args.args[2], 'rows')
            self.assertEqual(execute_python_script_polars(pl.DataFrame({'x': [1]}).lazy(),
                             {'code': 'result = df'}).to_dicts(), [{'x': 2}])
            self.assertEqual(executor.call_args.args[2], 'polars')

    @override_settings(BI_PYTHON_EXECUTOR_URL='', BI_PYTHON_EXECUTOR_TOKEN='')
    def test_no_configuration_fails_closed_without_executing_code(self):
        with self.assertRaisesMessage(ValueError, 'не настроен'):
            execute_isolated(pl.DataFrame({'x': [1]}), 'while True: pass', 'polars')

    @override_settings(BI_PYTHON_EXECUTOR_URL='http://executor:8766', BI_PYTHON_EXECUTOR_TOKEN='x' * 40)
    def test_response_metadata_and_schema_survive_transport(self):
        buffer = io.BytesIO()
        expected = pl.DataFrame({'x': [1]}, schema={'x': pl.Int32})
        expected.write_ipc(buffer)
        with patch('modules.bi_analysis_modern.api.execution.python_executor.build_opener') as opener:
            response = opener.return_value.open.return_value
            response.read.return_value = pack({'ok': True}, buffer.getvalue())
            actual = execute_isolated(expected, 'result = df', 'polars')
        self.assertEqual(actual.schema, expected.schema)
        self.assertEqual(actual.to_dicts(), expected.to_dicts())

    def test_redirects_cannot_forward_internal_token(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, None, None, None, None))
