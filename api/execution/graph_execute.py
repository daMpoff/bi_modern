# -*- coding: utf-8 -*-
"""
Выполнение пайплайна графа (nodes/edges) на бэкенде.
Оркестрация: топология, кэш, вызов обработчиков узлов.
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from ..config import PREVIEW_ROW_LIMIT, SOURCE_LIMIT, USE_SQL_PUSHDOWN
from .graph_plan import compile_graph, GraphValidationError
from .formulas import normalize_formulas, parse_formula
from .sql_pushdown import can_push_filter, can_push_aggregation
from .node_handlers import (
    get_source_data,
    apply_filter,
    apply_filter_polars,
    apply_aggregation,
    apply_aggregation_polars,
    filter_chart_data_by_config,
)
from .pipeline_data import (
    apply_formulas,
    apply_formulas_polars,
    execute_python_script,
    execute_python_script_polars,
)
from .pipeline_join import apply_join as apply_join_rows
from .pipeline_join import apply_join_polars
from .pipeline_types import (
    collect_result,
    get_schema_names,
    is_lazy,
    is_polars_available,
    row_count,
    to_dataframe,
    to_lazy,
    to_rows,
    to_rows_slice,
)

logger = logging.getLogger(__name__)

_BI_DEBUG = os.getenv('BI_DEBUG', '').lower() in ('1', 'true', 'yes')
_BI_DEBUG_EXPLAIN = os.getenv('BI_DEBUG_EXPLAIN', '').lower() in ('1', 'true', 'yes')

NODE_TYPE_DATA_SOURCE = 'dataSource'
NODE_TYPE_FILTER = 'filter'
NODE_TYPE_AGGREGATION = 'aggregation'
NODE_TYPE_JOIN = 'join'
NODE_TYPE_FORMULA = 'formula'
NODE_TYPE_PYTHON_SCRIPT = 'pythonScript'
NODE_TYPE_CHART = 'chart'
NODE_TYPE_OUTPUT = 'output'


def execute_graph(
    nodes: List[Dict],
    edges: List[Dict],
    user,
    params: Dict[str, Any] = None,
    include_node_row_counts: bool = False,
    preview: bool = False,
) -> Dict[str, Any]:
    """Выполнить проверенный граф, возвращая ошибки без маскировки под пустые данные."""
    try:
        return _execute_graph(nodes, edges, user, params, include_node_row_counts, preview)
    except Exception as exc:
        logger.exception('Ошибка исполнения конвейера')
        return {'chartData': [], 'error': f'Ошибка выполнения конвейера: {exc}'}


def _execute_graph(nodes, edges, user, params=None, include_node_row_counts=False, preview=False):
    """
    Выполняет граф и возвращает данные для узлов типа chart/output.
    Данные хранятся в Polars DataFrame на протяжении всего пайплайна,
    конвертация в List[Dict] происходит только на финальном этапе.
    """
    params = params or {}
    try:
        plan = compile_graph(nodes, edges)
    except GraphValidationError as exc:
        return {'chartData': [], 'error': str(exc)}
    nodes_by_id = plan.nodes_by_id
    edges_map = plan.edges_map
    order = plan.order

    source_limit: Optional[int] = PREVIEW_ROW_LIMIT if preview else SOURCE_LIMIT
    use_polars = is_polars_available()

    if _BI_DEBUG:
        logger.debug(
            'execute_graph start: preview=%s source_limit=%s use_polars=%s order=%s',
            preview, source_limit, use_polars, order,
        )

    children_map = plan.children_map
    source_nodes_in_order = [
        nid for nid in order
        if (nodes_by_id.get(nid) or {}).get('type') == NODE_TYPE_DATA_SOURCE
    ]

    try:
        required_columns = _collect_required_columns(order, nodes_by_id, edges_map) if use_polars else {}
    except ValueError as exc:
        return {'chartData': [], 'error': str(exc)}

    if len(source_nodes_in_order) > 1:
        source_result = _fetch_sources_parallel(
            source_nodes_in_order, nodes_by_id, children_map,
            user, source_limit, use_polars, params, not include_node_row_counts,
        )
    elif source_nodes_in_order:
        source_result = _fetch_single_source(
            source_nodes_in_order[0], nodes_by_id, children_map,
            user, source_limit, use_polars, params, not include_node_row_counts,
        )
    else:
        source_result = {'cache': {}, 'pushdown_skip': set()}
    if 'error' in source_result:
        return source_result
    cache = source_result['cache']
    pushdown_skip = source_result['pushdown_skip']

    if use_polars and required_columns:
        for src_nid, cols in required_columns.items():
            if cols is None:
                continue
            cached = cache.get(src_nid)
            if cached is None or not is_lazy(cached):
                continue
            try:
                available = set(get_schema_names(cached))
                select_cols = [c for c in cols if c in available]
                if select_cols and len(select_cols) < len(available):
                    cache[src_nid] = cached.select(select_cols)
                    if _BI_DEBUG:
                        logger.debug(
                            'Projection pushdown for %s: %d/%d columns selected',
                            src_nid, len(select_cols), len(available),
                        )
            except Exception as e:
                logger.debug('Projection pushdown failed for %s: %s', src_nid, e)

    for nid in order:
        node = nodes_by_id.get(nid)
        if not node:
            continue
        ntype = node.get('type')
        config = (node.get('data') or {}).get('config') or {}

        if ntype == NODE_TYPE_DATA_SOURCE:
            if use_polars and nid in cache:
                cached = cache[nid]
                if not is_lazy(cached):
                    cache[nid] = to_lazy(cached)
            continue

        if nid in pushdown_skip:
            continue

        if ntype == NODE_TYPE_FILTER:
            sources = edges_map.get(nid, [])
            if len(sources) != 1:
                return {'chartData': [], 'error': 'Фильтр должен иметь один вход'}
            inp = cache.get(sources[0])
            if use_polars and (is_lazy(inp) or hasattr(inp, 'filter')):
                cache[nid] = apply_filter_polars(inp, config, params)
            else:
                df = to_dataframe(inp)
                if use_polars and hasattr(df, 'filter'):
                    cache[nid] = apply_filter_polars(df, config, params)
                else:
                    cache[nid] = apply_filter(to_rows(inp), config, params)

        elif ntype == NODE_TYPE_AGGREGATION:
            sources = edges_map.get(nid, [])
            if len(sources) != 1:
                return {'chartData': [], 'error': 'Агрегация должна иметь один вход'}
            inp = cache.get(sources[0])
            if use_polars and (is_lazy(inp) or hasattr(inp, 'group_by')):
                cache[nid] = apply_aggregation_polars(inp, config)
            else:
                df = to_dataframe(inp)
                if use_polars and hasattr(df, 'group_by'):
                    cache[nid] = apply_aggregation_polars(df, config)
                else:
                    cache[nid] = apply_aggregation(to_rows(inp), config)

        elif ntype == NODE_TYPE_JOIN:
            sources = edges_map.get(nid, [])
            if len(sources) != 2:
                return {'chartData': [], 'error': 'Соединение должно иметь два входа'}
            left_id, right_id = sources
            left_inp = cache.get(left_id)
            right_inp = cache.get(right_id)
            if use_polars:
                if is_lazy(left_inp) or is_lazy(right_inp):
                    left_lf = to_lazy(left_inp) if not is_lazy(left_inp) else left_inp
                    right_lf = to_lazy(right_inp) if not is_lazy(right_inp) else right_inp
                    cache[nid] = apply_join_polars(left_lf, right_lf, config)
                else:
                    left_df = to_dataframe(left_inp)
                    right_df = to_dataframe(right_inp)
                    if hasattr(left_df, 'join'):
                        cache[nid] = apply_join_polars(left_df, right_df, config)
                    else:
                        cache[nid] = apply_join_rows(to_rows(left_inp), to_rows(right_inp), config)
            else:
                cache[nid] = apply_join_rows(to_rows(left_inp), to_rows(right_inp), config)

        elif ntype == NODE_TYPE_FORMULA:
            sources = edges_map.get(nid, [])
            if len(sources) != 1:
                return {'chartData': [], 'error': 'Формула должна иметь один вход'}
            inp = cache.get(sources[0])
            _polars_path = use_polars and (is_lazy(inp) or hasattr(inp, 'with_columns'))
            try:
                if _polars_path:
                    cache[nid] = apply_formulas_polars(inp, config, params)
                else:
                    cache[nid] = apply_formulas(to_rows(inp), config, params)
            except Exception as e:
                logger.exception('Formula error for node %s', nid)
                return {'chartData': [], 'error': f'Ошибка формулы: {e}'}

        elif ntype == NODE_TYPE_PYTHON_SCRIPT:
            sources = edges_map.get(nid, [])
            if len(sources) != 1:
                return {'chartData': [], 'error': 'Python Script должен иметь один вход'}
            inp = cache.get(sources[0])
            if use_polars and is_lazy(inp):
                if _BI_DEBUG_EXPLAIN:
                    logger.debug('Query plan before PythonScript collect:\n%s', inp.explain())
                inp = collect_result(inp)
            _polars_path = use_polars and hasattr(inp, 'to_dicts')
            try:
                if _polars_path:
                    result = execute_python_script_polars(inp, config)
                    if use_polars and hasattr(result, 'lazy'):
                        result = result.lazy()
                    cache[nid] = result
                else:
                    cache[nid] = execute_python_script(to_rows(inp), config)
            except Exception as e:
                logger.exception('Python script error for node %s', nid)
                return {'chartData': [], 'error': f'Ошибка Python скрипта: {e}'}

        elif ntype in (NODE_TYPE_CHART, NODE_TYPE_OUTPUT):
            sources = edges_map.get(nid, [])
            if len(sources) != 1:
                label = 'График' if ntype == NODE_TYPE_CHART else 'Выход'
                return {'chartData': [], 'error': f'{label} должен иметь один вход'}

            frame = cache.get(sources[0])
            if is_lazy(frame):
                if _BI_DEBUG_EXPLAIN:
                    logger.debug('Query plan before %s collect:\n%s', ntype, frame.explain())
                frame = collect_result(frame)
            total = row_count(frame)
            chart_data = _finalize_chart(frame, config) if ntype == NODE_TYPE_CHART else []
            result = {'chartData': chart_data, '_raw_df': frame, '_total_rows': total}
            if include_node_row_counts:
                terminal_count = len(chart_data) if ntype == NODE_TYPE_CHART else total
                result['node_row_counts'] = _collect_row_counts(cache, order, nid, terminal_count)
            return result

        else:
            sources = edges_map.get(nid, [])
            if len(sources) == 1:
                cache[nid] = cache.get(sources[0])
            continue

    return {'chartData': [], 'error': 'График не найден в цепочке'}


def _finalize_chart(inp: Any, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Подготавливает данные графика, фильтруя по конфигурации."""
    data = to_rows(inp)
    return filter_chart_data_by_config(data, config)


def _collect_row_counts(
    cache: Dict[str, Any], order: List[str], terminal_nid: str, terminal_count: int
) -> Dict[str, int]:
    counts = {}
    for nid in order:
        data = cache.get(nid)
        if is_lazy(data):
            try:
                import polars as pl
                cnt = data.select(pl.len()).collect().item()
                counts[nid] = cnt
            except Exception:
                counts[nid] = None
        else:
            counts[nid] = row_count(data)
    counts[terminal_nid] = terminal_count
    return counts


def _fetch_single_source(
    nid: str,
    nodes_by_id: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    user,
    source_limit: Optional[int],
    use_polars: bool,
    params: Dict[str, Any],
    allow_sql_pushdown: bool = True,
) -> Dict[str, Any]:
    """Загрузка одного источника данных. Возвращает LazyFrame при use_polars=True."""
    node = nodes_by_id.get(nid)
    config = (node.get('data') or {}).get('config') or {}
    main_table = config.get('main_table') or {}

    pushdown_filter, pushdown_agg, local_skip = (
        _get_pushdown_config(nodes_by_id, children_map, nid, params)
        if allow_sql_pushdown and USE_SQL_PUSHDOWN and not main_table.get('file_id')
        else (None, None, set())
    )

    try:
        data = get_source_data(
            config, user, limit=source_limit, return_dataframe=use_polars,
            pushdown_filter=pushdown_filter, pushdown_aggregation=pushdown_agg,
            params=params,
        )
        if data is None:
            return {'chartData': [], 'error': 'Не удалось получить данные из источника'}

        df = to_lazy(data) if use_polars else data

        if _BI_DEBUG and use_polars and not is_lazy(df) and hasattr(df, 'is_empty') and df.is_empty():
            label = (node.get('data') or {}).get('label', nid)
            logger.warning('Source "%s" returned 0 rows', label)
    except Exception as e:
        logger.exception('Error getting source data for node %s', nid)
        return {'chartData': [], 'error': f'Ошибка источника данных: {e}'}

    result_cache = {nid: df}
    for skip_nid in local_skip:
        result_cache[skip_nid] = df
    return {'cache': result_cache, 'pushdown_skip': local_skip}


def _fetch_sources_parallel(
    source_nids: List[str],
    nodes_by_id: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    user,
    source_limit: Optional[int],
    use_polars: bool,
    params: Dict[str, Any],
    allow_sql_pushdown: bool = True,
) -> Dict[str, Any]:
    """Параллельная загрузка с тем же форматом результата, что у одного источника."""
    combined_cache: Dict[str, Any] = {}
    combined_skip: set = set()
    max_workers = min(len(source_nids), 4)

    def fetch(nid):
        from django.db import close_old_connections, connections
        close_old_connections()
        try:
            return _fetch_single_source(nid, nodes_by_id, children_map,
                                        user, source_limit, use_polars, params, allow_sql_pushdown)
        finally:
            # У соединений Django в потоках нет request_finished.
            connections.close_all()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch, nid): nid for nid in source_nids}
        for future in as_completed(futures):
            nid = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.exception('Parallel source fetch error for node %s', nid)
                return {'chartData': [], 'error': f'Ошибка источника данных: {e}'}

            if 'error' in result:
                return result

            combined_cache.update(result.get('cache', {}))
            combined_skip |= result.get('pushdown_skip', set())

    return {'cache': combined_cache, 'pushdown_skip': combined_skip}


def _collect_required_columns(
    order: List[str],
    nodes_by_id: Dict[str, Dict],
    edges_map: Dict[str, List[str]],
) -> Dict[str, Optional[set]]:
    needed: Dict[str, Optional[set]] = {}

    for nid in reversed(order):
        node = nodes_by_id.get(nid)
        if not node:
            continue
        ntype = node.get('type')
        config = (node.get('data') or {}).get('config') or {}

        if ntype in (NODE_TYPE_CHART, NODE_TYPE_OUTPUT, NODE_TYPE_PYTHON_SCRIPT):
            needed[nid] = None
        elif ntype == NODE_TYPE_FILTER:
            conditions = config.get('conditions') or []
            my_cols = set()
            for cond in conditions:
                field = cond.get('field')
                if field:
                    my_cols.add(field)
            child_needed = needed.get(nid)
            if child_needed is None:
                needed[nid] = None
            else:
                needed[nid] = my_cols | child_needed
        elif ntype == NODE_TYPE_AGGREGATION:
            group_by = config.get('groupBy') or []
            aggs = config.get('aggregations') or []
            my_cols = set(group_by)
            for agg in aggs:
                field = agg.get('field')
                if field:
                    my_cols.add(field)
            needed[nid] = my_cols
        elif ntype == NODE_TYPE_FORMULA:
            formulas = normalize_formulas(config)
            my_cols = set()
            for f in formulas:
                expression = (f.get('expression') or '').strip()
                my_cols |= _extract_column_names_from_expr(expression)
            child_needed = needed.get(nid)
            if child_needed is None:
                needed[nid] = None
            else:
                needed[nid] = my_cols | child_needed
        elif ntype == NODE_TYPE_JOIN:
            left_key = (config.get('leftKey') or '').strip()
            right_key = (config.get('rightKey') or '').strip()
            child_needed = needed.get(nid)
            if child_needed is None:
                needed[nid] = None
            else:
                cols = set(child_needed)
                if left_key:
                    cols.add(left_key)
                if right_key:
                    cols.add(right_key)
                needed[nid] = cols
        elif ntype == NODE_TYPE_DATA_SOURCE:
            pass
        else:
            needed.setdefault(nid, needed.get(nid))

        sources = edges_map.get(nid, [])
        current_need = needed.get(nid)
        for src_nid in sources:
            existing = needed.get(src_nid)
            if existing is None and src_nid in needed:
                continue
            if current_need is None:
                needed[src_nid] = None
            elif existing is not None:
                needed[src_nid] = existing | current_need
            else:
                needed[src_nid] = set(current_need) if current_need else set()

    result = {}
    for nid in order:
        node = nodes_by_id.get(nid)
        if node and node.get('type') == NODE_TYPE_DATA_SOURCE:
            result[nid] = needed.get(nid)
    return result


def _extract_column_names_from_expr(expression: str) -> set:
    """Извлекает имена колонок из арифметического выражения (простая эвристика через AST)."""
    import ast as _ast
    names = set()
    if not expression:
        return names
    try:
        tree = parse_formula(expression)
    except SyntaxError:
        return names

    for node in _ast.walk(tree):
        if isinstance(node, _ast.Name):
            name = node.id
            if not name.startswith('$') and name not in (
                'abs', 'round', 'sqrt', 'ceil', 'floor', 'log', 'log10',
                'True', 'False', 'None',
            ):
                names.add(name)
    return names


def _get_pushdown_config(
    nodes_by_id: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    source_nid: str,
    params: Optional[Dict] = None,
) -> tuple:
    next_ids = children_map.get(source_nid, [])
    if len(next_ids) != 1:
        return (None, None, set())
    next_node = nodes_by_id.get(next_ids[0])
    if not next_node:
        return (None, None, set())
    next_type = next_node.get('type')
    next_config = (next_node.get('data') or {}).get('config') or {}

    if next_type == NODE_TYPE_FILTER:
        if not can_push_filter(next_config, params):
            return (None, None, set())
        filter_config = next_config
        agg_ids = children_map.get(next_ids[0], [])
        skip_ids = {next_ids[0]}
        if len(agg_ids) != 1:
            return (filter_config, None, skip_ids)
        agg_node = nodes_by_id.get(agg_ids[0])
        if not agg_node or agg_node.get('type') != NODE_TYPE_AGGREGATION:
            return (filter_config, None, skip_ids)
        agg_config = (agg_node.get('data') or {}).get('config') or {}
        if not can_push_aggregation(agg_config):
            return (filter_config, None, skip_ids)
        skip_ids.add(agg_ids[0])
        return (filter_config, agg_config, skip_ids)

    if next_type == NODE_TYPE_AGGREGATION:
        if not can_push_aggregation(next_config):
            return (None, None, set())
        return (None, next_config, {next_ids[0]})

    return (None, None, set())
