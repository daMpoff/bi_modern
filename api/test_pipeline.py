from types import SimpleNamespace
import sqlite3
from unittest.mock import patch

import polars as pl
from django.test import SimpleTestCase, override_settings

from .graph_execute import execute_graph, _get_pushdown_config
from .inline_source_executor import _build_sql_query, _execute_db_source, _execute_file_source
from .pipeline_data import (apply_formulas, apply_formulas_polars, evaluate_formula,
                            execute_python_script, execute_python_script_polars)
from .pipeline_join import apply_join, apply_join_polars
from .lineage import compute_lineage
from .pipeline_types import collect_result
from .bi_datasets.models import FileUpload
from .bi_pipelines.views import _execute_cache_get, _execute_cache_put
from ..sandbox.worker import execute as execute_worker


def node(identifier, kind, config=None):
    return {'id': identifier, 'type': kind, 'data': {'config': config or {}}}


class PipelineRegressionTests(SimpleTestCase):
    def test_editor_formula_config_is_executed_in_both_engines(self):
        config = {'outputField': 'total', 'expression': 'price * 2'}
        rows = [{'price': 3}]
        self.assertEqual(apply_formulas(rows, config), [{'price': 3, 'total': 6}])
        result = apply_formulas_polars(pl.DataFrame(rows).lazy(), config)
        self.assertEqual(collect_result(result).to_dicts(), [{'price': 3, 'total': 6}])

    def test_dollar_parameter_is_parsed_as_a_parameter(self):
        self.assertEqual(evaluate_formula('price * $rate', {'price': 3}, {'rate': 4}), 12)
        config = {'outputField': 'total', 'expression': 'price * $rate'}
        frame = apply_formulas_polars(pl.DataFrame({'price': [3]}).lazy(), config, {'rate': 4})
        self.assertEqual(collect_result(frame)['total'].to_list(), [12])

    def test_join_inputs_follow_ports_instead_of_random_ids(self):
        nodes = [node('z-left', 'dataSource'), node('a-right', 'dataSource'),
                 node('join', 'join', {'joinType': 'LEFT JOIN', 'leftKey': 'id', 'rightKey': 'id'}),
                 node('out', 'output')]
        nodes[0]['data']['config'] = {'source': 'left'}
        nodes[1]['data']['config'] = {'source': 'right'}
        edges = [
            {'source': 'a-right', 'target': 'join', 'targetHandle': 'right-target'},
            {'source': 'z-left', 'target': 'join', 'targetHandle': 'left-target'},
            {'source': 'join', 'target': 'out'},
        ]
        def source(config, *args, **kwargs):
            return pl.DataFrame({'id': [1, 2]}) if config['source'] == 'left' else pl.DataFrame({'id': [1]})
        with patch('modules.bi_analysis_modern.api.graph_execute.get_source_data', side_effect=source), \
                patch('modules.bi_analysis_modern.api.graph_execute.USE_SQL_PUSHDOWN', False):
            result = execute_graph(nodes, edges, SimpleNamespace(pk=1))
        self.assertNotIn('error', result)
        self.assertEqual(result['_raw_df']['id'].to_list(), [1, 2])

    def test_duplicate_node_ids_are_rejected_before_loading_sources(self):
        nodes = [node('source', 'dataSource'), node('source', 'dataSource'), node('out', 'output')]
        with patch('modules.bi_analysis_modern.api.graph_execute.get_source_data', return_value=pl.DataFrame({'x': [1]})) as source:
            result = execute_graph(nodes, [{'source': 'source', 'target': 'out'}], None)
        self.assertIn('error', result)
        source.assert_not_called()

    def test_source_id_cannot_collide_with_parallel_loader_error_state(self):
        nodes = [node('__error__', 'dataSource'), node('other', 'dataSource'),
                 node('join', 'join', {'joinType': 'INNER JOIN', 'leftKey': 'id', 'rightKey': 'id'}),
                 node('out', 'output')]
        edges = [{'source': '__error__', 'target': 'join', 'targetHandle': 'left-target'},
                 {'source': 'other', 'target': 'join', 'targetHandle': 'right-target'},
                 {'source': 'join', 'target': 'out'}]
        with patch('modules.bi_analysis_modern.api.graph_execute.get_source_data', return_value=pl.DataFrame({'id': [1]})), \
                patch('modules.bi_analysis_modern.api.graph_execute.USE_SQL_PUSHDOWN', False):
            result = execute_graph(nodes, edges, None)
        self.assertIsInstance(result, dict)
        self.assertNotIn('error', result)
        self.assertEqual(result['_total_rows'], 1)

    def test_missing_edge_endpoint_is_rejected(self):
        result = execute_graph([node('out', 'output')], [{'source': 'missing', 'target': 'out'}], None)
        self.assertIn('error', result)

    def test_pushdown_does_not_skip_contains_filter(self):
        nodes = {'src': node('src', 'dataSource'),
                 'filter': node('filter', 'filter', {'conditions': [{'field': 'name', 'operator': 'contains', 'value': 'a'}]})}
        result = _get_pushdown_config(nodes, {'src': ['filter']}, 'src', {})
        self.assertEqual(result, (None, None, set()))

    def test_global_sql_aggregation_is_not_replaced_by_raw_rows(self):
        sql, params = _build_sql_query({'name': 'sales'}, [], None,
                                     pushdown_aggregation={'aggregations': [{'agg': 'count', 'outputName': 'total'}]})
        self.assertIn('COUNT(*) AS "total"', sql)
        self.assertNotIn('a.*', sql)

    def test_generated_sql_aggregates_actual_rows(self):
        with sqlite3.connect(':memory:') as database:
            database.execute('CREATE TABLE sales (amount INTEGER)')
            database.executemany('INSERT INTO sales VALUES (?)', [(10,), (20,), (30,)])
            sql, params = _build_sql_query({'name': 'sales'}, [], None,
                pushdown_filter={'conditions': [{'field': 'amount', 'operator': '>=', 'value': 20}]},
                pushdown_aggregation={'aggregations': [{'agg': 'sum', 'field': 'amount', 'outputName': 'total'}]})
            self.assertEqual(database.execute(sql, params).fetchall(), [(50,)])

    def test_identifier_quotes_are_escaped(self):
        with sqlite3.connect(':memory:') as database:
            database.execute('CREATE TABLE "sales""archive" (amount INTEGER)')
            sql, params = _build_sql_query({'name': 'sales"archive'}, [], None)
            self.assertEqual(database.execute(sql, params).fetchall(), [])

    def test_source_query_failure_is_not_a_successful_empty_table(self):
        with patch('modules.bi_analysis_modern.api.inline_source_executor.execute_sql', side_effect=RuntimeError('offline')):
            with self.assertLogs('modules.bi_analysis_modern.api.inline_source_executor', level='ERROR'), self.assertRaises(ValueError):
                _execute_db_source(SimpleNamespace(), {'name': 'sales'}, [], None)

    def test_file_must_belong_to_the_selected_connection_and_user(self):
        with patch.object(FileUpload.objects, 'get', side_effect=FileUpload.DoesNotExist), \
                patch('modules.bi_analysis_modern.api.inline_source_executor._read_file_direct_polars',
                      return_value=pl.DataFrame({'private': [1]}).lazy()):
            with self.assertRaises(ValueError):
                _execute_file_source(SimpleNamespace(pk=1), {'file_id': 99}, [], SimpleNamespace(pk=2), None, True)

    def test_new_execution_does_not_invalidate_another_open_tab(self):
        _execute_cache_put('tab-one', [{'x': 1}], ['x'], 1, 901, 902)
        _execute_cache_put('tab-two', [{'x': 2}], ['x'], 1, 901, 902)
        self.assertIsNotNone(_execute_cache_get('tab-one', 901, 902))
        self.assertIsNone(_execute_cache_get('tab-one', 903, 902))

    def test_python_script_uses_the_result_variable_shown_in_the_editor(self):
        rows = [{'x': 1}, {'x': 2}]
        self.assertEqual(execute_worker(pl.DataFrame(rows), 'result = rows[:1]', 'rows').to_dicts(), rows[:1])
        frame = execute_worker(pl.DataFrame(rows), 'result = df.head(1)', 'polars')
        self.assertEqual(frame.to_dicts(), rows[:1])

    def test_python_comprehensions_can_use_script_variables(self):
        result = execute_worker(pl.DataFrame({'x': [2]}), 'factor = 3\nresult = [{"x": row["x"] * factor} for row in rows]', 'rows')
        self.assertEqual(result.to_dicts(), [{'x': 6}])

    def test_round_precision_and_chained_comparisons_match_python(self):
        rows = [{'price': 2.555}, {'price': 20.0}]
        for expression in ('round(price, 2)', '1 < price < 10'):
            config = {'outputField': 'value', 'expression': expression}
            eager = apply_formulas(rows, config)
            lazy = collect_result(apply_formulas_polars(pl.DataFrame(rows).lazy(), config)).to_dicts()
            self.assertEqual(lazy, eager)

    def test_join_schema_and_null_keys_match_in_both_engines(self):
        left = [{'id': 1, 'value': 'L1'}, {'id': None, 'value': 'Lnull'}]
        right = [{'id': 1, 'value': 'R1'}, {'id': None, 'value': 'Rnull'}]
        for how in ('INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN'):
            with self.subTest(join=how):
                config = {'joinType': how, 'leftKey': 'id', 'rightKey': 'id'}
                expected = apply_join(left, right, config)
                frame = apply_join_polars(pl.DataFrame(left).lazy(), pl.DataFrame(right).lazy(), config)
                self.assertEqual(collect_result(frame).to_dicts(), expected)
                self.assertTrue(all('id_right' in row for row in expected))

    def test_left_join_with_empty_right_side_keeps_its_columns(self):
        config = {'joinType': 'LEFT JOIN', 'leftKey': 'id', 'rightKey': 'id'}
        frame = apply_join_polars(pl.DataFrame({'id': [1]}).lazy(),
                                 pl.DataFrame(schema={'id': pl.Int64, 'name': pl.String}).lazy(), config)
        self.assertEqual(collect_result(frame).to_dicts(), [{'id': 1, 'id_right': None, 'name': None}])

    def test_lineage_and_execution_reject_the_same_invalid_graph(self):
        nodes = [node('one', 'output'), node('two', 'output')]
        self.assertEqual(compute_lineage(nodes, [])['error'], execute_graph(nodes, [], None)['error'])

    def test_pushdown_does_not_apply_an_unbound_optional_parameter(self):
        nodes = {'src': node('src', 'dataSource'), 'filter': node('filter', 'filter', {
            'conditions': [{'field': 'year', 'operator': '=', 'value': '$year'}],
        })}
        self.assertEqual(_get_pushdown_config(nodes, {'src': ['filter']}, 'src', {}), (None, None, set()))

    def test_formula_input_is_not_removed_by_projection_before_aggregation(self):
        nodes = [node('src', 'dataSource'), node('formula', 'formula', {
            'outputField': 'total', 'expression': 'price * $rate',
        }), node('agg', 'aggregation', {'aggregations': [{'field': 'total', 'agg': 'sum'}]}), node('out', 'output')]
        edges = [{'source': left, 'target': right} for left, right in [('src', 'formula'), ('formula', 'agg'), ('agg', 'out')]]
        with patch('modules.bi_analysis_modern.api.graph_execute.get_source_data',
                   return_value=pl.DataFrame({'price': [2, 3], 'unused': [1, 1]}).lazy()):
            result = execute_graph(nodes, edges, None, params={'rate': 4})
        self.assertNotIn('error', result)
        self.assertEqual(result['_raw_df']['total_sum'].to_list(), [20])

    def test_lineage_counts_describe_each_step_before_sql_optimization(self):
        nodes = [node('src', 'dataSource'), node('filter', 'filter', {
            'conditions': [{'field': 'value', 'operator': '>', 'value': 0}],
        }), node('out', 'output')]
        edges = [{'source': 'src', 'target': 'filter'}, {'source': 'filter', 'target': 'out'}]
        with patch('modules.bi_analysis_modern.api.graph_execute.get_source_data',
                   return_value=pl.DataFrame({'value': [0, 1, 2]}).lazy()) as source:
            result = execute_graph(nodes, edges, None, include_node_row_counts=True)
        self.assertIsNone(source.call_args.kwargs['pushdown_filter'])
        self.assertEqual(result['node_row_counts'], {'src': 3, 'filter': 2, 'out': 2})

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_cached_polars_result_remains_readable_from_another_cache_instance(self):
        from django.core.cache.backends.filebased import FileBasedCache
        from .execution.result_cache import _local_cache, _key
        _execute_cache_put('frame', pl.DataFrame({'x': [1, 2]}), ['x'], 2, 901, 902)
        other = FileBasedCache(_local_cache()._dir, {})
        self.assertEqual(other.get(_key('frame', 901, 902))['raw_df'].to_dicts(), [{'x': 1}, {'x': 2}])
