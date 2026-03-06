# -*- coding: utf-8 -*-
"""
Data Lineage: цепочка узлов от источников данных до графика/выхода.
Без выполнения пайплайна, только по графу (nodes/edges).
"""
from typing import Any, Dict, List

NODE_TYPE_DATA_SOURCE = 'dataSource'
NODE_TYPE_FILTER = 'filter'
NODE_TYPE_AGGREGATION = 'aggregation'
NODE_TYPE_JOIN = 'join'
NODE_TYPE_FORMULA = 'formula'
NODE_TYPE_PYTHON_SCRIPT = 'pythonScript'
NODE_TYPE_CHART = 'chart'
NODE_TYPE_OUTPUT = 'output'

NODE_TYPE_LABELS = {
    NODE_TYPE_DATA_SOURCE: 'Источник данных',
    NODE_TYPE_FILTER: 'Фильтр',
    NODE_TYPE_AGGREGATION: 'Агрегация',
    NODE_TYPE_JOIN: 'Соединение',
    NODE_TYPE_FORMULA: 'Формула',
    NODE_TYPE_PYTHON_SCRIPT: 'Python',
    NODE_TYPE_CHART: 'График',
    NODE_TYPE_OUTPUT: 'Выход',
}


def _build_edges_map(edges: List[Dict]) -> Dict[str, List[str]]:
    """target -> [source1, source2, ...]"""
    result = {}
    for e in edges or []:
        target = e.get('target')
        source = e.get('source')
        if target and source:
            if target not in result:
                result[target] = []
            result[target].append(source)
    return result


def _node_label(node: Dict) -> str:
    data = node.get('data') or {}
    label = (data.get('label') or '').strip()
    if label:
        return label
    ntype = node.get('type') or ''
    return NODE_TYPE_LABELS.get(ntype, ntype or 'Узел')


def compute_lineage(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
    """
    Строит lineage: узлы от источников до терминального узла (chart/output).

    Returns:
        {
            "nodes": [ {"id", "type", "label", "order"}, ... ],
            "edges": [ {"source", "target"}, ... ],
            "error": str | null
        }
        order — порядок обхода от источников к выходу (0 = источники).
    """
    if not nodes:
        return {'nodes': [], 'edges': [], 'error': 'Нет узлов'}

    nodes_by_id = {n.get('id'): n for n in nodes if n.get('id')}
    if not nodes_by_id:
        return {'nodes': [], 'edges': [], 'error': 'Нет узлов с id'}

    chart_nodes = [n for n in nodes if n.get('type') == NODE_TYPE_CHART]
    output_nodes = [n for n in nodes if n.get('type') == NODE_TYPE_OUTPUT]

    if len(chart_nodes) > 1:
        return {'nodes': [], 'edges': [], 'error': 'В пайплайне допускается только один блок «График»'}

    edges_map = _build_edges_map(edges)
    terminal_node = None
    if output_nodes:
        terminal_node = output_nodes[0]
    elif chart_nodes:
        terminal_node = chart_nodes[0]

    if not terminal_node:
        return {'nodes': [], 'edges': [], 'error': 'Нет терминального узла (chart или output)'}

    reachable = set()
    stack = [terminal_node.get('id')]
    while stack:
        nid = stack.pop()
        if nid in reachable:
            continue
        reachable.add(nid)
        for sid in edges_map.get(nid, []):
            stack.append(sid)

    order = []
    done = set()
    while len(order) < len(reachable):
        progress = False
        for nid in reachable:
            if nid in done:
                continue
            deps = edges_map.get(nid, [])
            if all(d in done for d in deps):
                order.append(nid)
                done.add(nid)
                progress = True
                break
        if not progress:
            return {'nodes': [], 'edges': [], 'error': 'Цикл или недостижимые узлы в графе'}

    lineage_edges = []
    for e in edges or []:
        if e.get('source') in reachable and e.get('target') in reachable:
            lineage_edges.append({'source': e['source'], 'target': e['target']})

    lineage_nodes = []
    for i, nid in enumerate(order):
        node = nodes_by_id.get(nid)
        if not node:
            continue
        ntype = node.get('type') or ''
        lineage_nodes.append({
            'id': nid,
            'type': ntype,
            'label': _node_label(node),
            'order': i,
        })

    return {
        'nodes': lineage_nodes,
        'edges': lineage_edges,
        'error': None,
    }
