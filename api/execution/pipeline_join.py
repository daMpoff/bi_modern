"""Соединение таблиц с одинаковыми именами полей в Python и Polars."""


def _join_options(config):
    left_key = (config.get('leftKey') or '').strip()
    right_key = (config.get('rightKey') or '').strip()
    if not left_key or not right_key:
        raise ValueError('Для соединения нужны левый и правый ключи')
    kind = (config.get('joinType') or 'LEFT JOIN').upper().replace(' OUTER', '')
    kinds = {'INNER JOIN': 'inner', 'LEFT JOIN': 'left', 'RIGHT JOIN': 'right', 'FULL JOIN': 'full'}
    if kind not in kinds:
        raise ValueError(f'Неизвестный тип соединения: {kind}')
    return left_key, right_key, kinds[kind]


def apply_join(left_data, right_data, config):
    left_key, right_key, how = _join_options(config)
    return _apply_join_python(left_data, right_data, left_key, right_key, how.upper() + ' JOIN')


def apply_join_polars(left_df, right_df, config):
    import polars as pl
    left_key, right_key, how = _join_options(config)
    lazy = isinstance(left_df, pl.LazyFrame) or isinstance(right_df, pl.LazyFrame)
    left_schema = left_df.collect_schema() if isinstance(left_df, pl.LazyFrame) else left_df.schema
    right_schema = right_df.collect_schema() if isinstance(right_df, pl.LazyFrame) else right_df.schema
    # У пустого источника SQL может не быть схемы: создаём только известный ключ.
    if not left_schema:
        left_df = pl.DataFrame({left_key: pl.Series([], dtype=right_schema.get(right_key, pl.Null))})
    if not right_schema:
        right_df = pl.DataFrame({right_key: pl.Series([], dtype=left_schema.get(left_key, pl.Null))})
    if lazy:
        left_df = left_df.lazy() if isinstance(left_df, pl.DataFrame) else left_df
        right_df = right_df.lazy() if isinstance(right_df, pl.DataFrame) else right_df
    return left_df.join(right_df, left_on=left_key, right_on=right_key, how=how,
                        suffix='_right', coalesce=False, maintain_order='left_right')


def _apply_join_python(left_data, right_data, left_key, right_key, join_type):
    how = _join_options({'leftKey': left_key, 'rightKey': right_key, 'joinType': join_type})[2]
    left_fields = list(dict.fromkeys(key for row in left_data for key in row)) or [left_key]
    right_fields = list(dict.fromkeys(key for row in right_data for key in row)) or [right_key]
    right_names = {key: key + '_right' if key in left_fields else key for key in right_fields}
    names = left_fields + list(right_names.values())
    if len(set(names)) != len(names):
        raise ValueError('Имена колонок соединения пересекаются с суффиксом _right')
    right_by_key = {}
    for index, row in enumerate(right_data):
        key = row.get(right_key)
        if key is not None:
            right_by_key.setdefault(key, []).append((index, row))
    def merge(left, right):
        return {**{key: left.get(key) for key in left_fields},
                **{name: right.get(key) for key, name in right_names.items()}}
    result, matched = [], set()
    for left in left_data:
        key = left.get(left_key)
        matches = right_by_key.get(key, []) if key is not None else []
        for index, right in matches:
            result.append(merge(left, right))
            matched.add(index)
        if not matches and how in ('left', 'full'):
            result.append(merge(left, {}))
    if how in ('right', 'full'):
        result.extend(merge({}, right) for index, right in enumerate(right_data) if index not in matched)
    return result
