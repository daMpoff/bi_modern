# -*- coding: utf-8 -*-
"""
Data Lineage: цепочка узлов от источников данных до графика/выхода.
Без выполнения пайплайна, только по графу (nodes/edges).
"""
from typing import Any, Dict, List

from .execution.graph_plan import compile_graph, GraphValidationError

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
    try:
        plan = compile_graph(nodes, edges)
    except GraphValidationError as exc:
        return {'nodes': [], 'edges': [], 'error': str(exc)}
    nodes_by_id = plan.nodes_by_id
    order = plan.order
    reachable = set(order)

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
