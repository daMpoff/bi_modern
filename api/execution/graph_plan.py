"""Проверка графа и общий порядок обхода для исполнения и линии данных."""
from collections import deque
from dataclasses import dataclass


NODE_TYPES = frozenset({'dataSource', 'filter', 'aggregation', 'join', 'formula',
                        'pythonScript', 'chart', 'output'})
TERMINAL_TYPES = frozenset({'chart', 'output'})


class GraphValidationError(ValueError):
    pass


def join_input_ids(edges, node_id):
    incoming = [edge for edge in edges if edge['target'] == node_id]
    if len(incoming) != 2:
        raise GraphValidationError('Соединение должно иметь два входа')
    explicit = [edge for edge in incoming if edge.get('targetHandle') in ('left-target', 'right-target')]
    if not explicit:
        # Сохранённые ранее графы не содержат портов; сохраняем прежний смысл ключей.
        return sorted(edge['source'] for edge in incoming)
    slots = {}
    for edge in explicit:
        slot = edge['targetHandle']
        if slot in slots:
            raise GraphValidationError('У каждого входа соединения может быть только одна связь')
        slots[slot] = edge['source']
    for edge in incoming:
        if edge not in explicit:
            slot = 'left-target' if 'left-target' not in slots else 'right-target'
            slots[slot] = edge['source']
    return [slots['left-target'], slots['right-target']]


@dataclass(frozen=True)
class GraphPlan:
    nodes_by_id: dict
    edges_map: dict
    children_map: dict
    order: tuple
    terminal_id: str


def compile_graph(nodes, edges):
    if not isinstance(nodes, list) or not nodes:
        raise GraphValidationError('Нет узлов')
    if not isinstance(edges, list):
        raise GraphValidationError('Связи графа должны быть списком')
    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            raise GraphValidationError('Каждый узел должен иметь строковый id')
        if node['id'] in by_id:
            raise GraphValidationError(f'Повторяется id узла: {node["id"]}')
        if node.get('type') not in NODE_TYPES:
            raise GraphValidationError(f'Неизвестный тип узла: {node.get("type")}')
        if not isinstance(node.get('data', {}), dict) or not isinstance((node.get('data') or {}).get('config', {}), dict):
            raise GraphValidationError('Настройки узла должны быть объектом')
        by_id[node['id']] = node
    terminals = [node['id'] for node in nodes if node['type'] in TERMINAL_TYPES]
    if len(terminals) != 1:
        raise GraphValidationError('Граф должен иметь ровно один выход или график')
    inputs = {nid: [] for nid in by_id}
    children = {nid: [] for nid in by_id}
    seen = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise GraphValidationError('Некорректная связь графа')
        source, target = edge.get('source'), edge.get('target')
        if not isinstance(source, str) or not isinstance(target, str) or source not in by_id or target not in by_id:
            raise GraphValidationError('Связь ссылается на отсутствующий узел')
        if any(edge.get(key) is not None and not isinstance(edge[key], str) for key in ('sourceHandle', 'targetHandle')):
            raise GraphValidationError('Некорректный порт связи')
        key = (source, target, edge.get('sourceHandle'), edge.get('targetHandle'))
        if key in seen:
            raise GraphValidationError('Повторяется связь между узлами')
        seen.add(key)
        inputs[target].append(source)
        children[source].append(target)
    degrees = {nid: len(deps) for nid, deps in inputs.items()}
    ready = deque(nid for nid in by_id if degrees[nid] == 0)
    order = []
    while ready:
        nid = ready.popleft()
        order.append(nid)
        for child in children[nid]:
            degrees[child] -= 1
            if degrees[child] == 0:
                ready.append(child)
    if len(order) != len(by_id):
        raise GraphValidationError('Обнаружен цикл в графе')
    reachable, pending = set(), [terminals[0]]
    while pending:
        nid = pending.pop()
        if nid not in reachable:
            reachable.add(nid)
            pending.extend(inputs[nid])
    for nid in reachable:
        kind = by_id[nid]['type']
        expected = 0 if kind == 'dataSource' else 2 if kind == 'join' else 1
        if len(inputs[nid]) != expected:
            raise GraphValidationError(f'Узел {nid} ({kind}) требует входов: {expected}')
        if kind == 'join':
            inputs[nid] = join_input_ids(edges, nid)
    # Отброшенные ветви не должны влиять на SQL-оптимизацию выбранного выхода.
    children = {nid: [child for child in values if child in reachable] for nid, values in children.items()}
    return GraphPlan(by_id, inputs, children, tuple(nid for nid in order if nid in reachable), terminals[0])
