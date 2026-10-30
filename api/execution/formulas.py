"""Единый формат формул редактора и разбор параметров $name без eval."""
import ast
import re


def parse_formula(expression):
    prefix = '__bi_parameter_'
    while prefix in expression:
        prefix += '_'
    parameters = {}

    def replace(match):
        placeholder = f'{prefix}{len(parameters)}'
        parameters[placeholder] = match.group(0)
        return placeholder

    normalized = re.sub(r'\$([A-Za-z_]\w*)', replace, expression.strip())
    tree = ast.parse(normalized, mode='eval')
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in parameters:
            node.id = parameters[node.id]
    return tree


def normalize_formulas(config):
    formulas = config.get('formulas')
    if formulas is None:
        formulas = [{'name': config.get('outputField'), 'expression': config.get('expression')}]
    result = []
    for formula in formulas:
        name = (formula.get('name') or '').strip()
        expression = (formula.get('expression') or '').strip()
        if not name and not expression:
            continue
        if not name or not expression:
            raise ValueError('Для формулы нужны имя выходного поля и выражение')
        try:
            parse_formula(expression)
        except SyntaxError as exc:
            raise ValueError(f'Некорректное выражение формулы «{name}»') from exc
        result.append({'name': name, 'expression': expression})
    return result
