"""Проверка операций, которые SQL-источник умеет выполнить полностью."""


def can_push_filter(config, params=None):
    params = params or {}
    supported = {'=', '==', '!=', '<>', '>', '>=', '<', '<=', 'between', 'isnull', 'notnull'}
    for condition in config.get('conditions') or []:
        if not condition.get('field'):
            return False
        operator = (condition.get('operator') or '=').lower()
        if operator not in supported:
            return False
        value = condition.get('value')
        if isinstance(value, str) and value.strip().startswith('$'):
            value = params.get(value.strip()[1:])
            if value is None or value == '':
                return False
        if operator == 'between':
            bounds = (value.get('min'), value.get('max')) if isinstance(value, dict) else value
            if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
                return False
            for bound in bounds:
                if isinstance(bound, str) and bound.strip().startswith('$'):
                    bound = params.get(bound.strip()[1:])
                if bound is None or bound == '':
                    return False
    return True


def can_push_aggregation(config):
    aggregations = config.get('aggregations') or []
    return bool(aggregations) and all(
        (item.get('agg') or 'count').lower() in {'sum', 'count', 'avg', 'min', 'max', 'ucount'}
        for item in aggregations
    )
