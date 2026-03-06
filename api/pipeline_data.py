# -*- coding: utf-8 -*-
"""
Унифицированный тип данных пайплайна BI.

Канонический формат: List[Dict[str, Any]]
Каждая строка — словарь {имя_колонки: значение}.

Модуль предоставляет нормализацию входных данных к каноническому формату,
безопасный парсер арифметических выражений для блока «Формула»
и векторизованную Polars-версию для работы с большими данными.
"""
import ast
import logging
import math
import operator
from typing import Any, Dict, List

try:
    import polars as pl
    _POLARS_AVAILABLE = True
except ImportError:
    pl = None
    _POLARS_AVAILABLE = False

logger = logging.getLogger(__name__)

PipelineRows = List[Dict[str, Any]]

_FORBIDDEN_KEYWORDS = [
    'import ', '__import__', 'exec(', 'eval(', 'compile(',
    'open(', '__builtins__', 'globals(', 'locals(',
    'getattr(', 'setattr(', 'delattr(', '__class__',
    '__subclasses__', '__bases__', '__mro__',
    'os.', 'sys.', 'subprocess', 'shutil',
]


def normalize_to_rows(data: Any) -> PipelineRows:
    """
    Приводит данные к каноническому формату List[Dict[str, Any]].
    Поддерживает: list of dict, dict с columns/rows, None.
    """
    if data is None:
        return []
    if isinstance(data, list):
        if not data:
            return []
        if isinstance(data[0], dict):
            return data
        return []
    if isinstance(data, dict):
        columns = data.get('columns')
        rows = data.get('rows')
        if columns and rows and isinstance(columns, list) and isinstance(rows, list):
            return [dict(zip(columns, row)) for row in rows]
        return []
    return []


_POLARS_BIN_OPS = {
    ast.Add: lambda l, r: l + r,
    ast.Sub: lambda l, r: l - r,
    ast.Mult: lambda l, r: l * r,
    ast.Div: lambda l, r: l / r,
    ast.FloorDiv: lambda l, r: (l / r).floor(),
    ast.Mod: lambda l, r: l % r,
    ast.Pow: lambda l, r: l.pow(r) if hasattr(l, 'pow') else l ** r,
}

_POLARS_CMP_OPS = {
    ast.Gt: lambda l, r: l > r,
    ast.GtE: lambda l, r: l >= r,
    ast.Lt: lambda l, r: l < r,
    ast.LtE: lambda l, r: l <= r,
    ast.Eq: lambda l, r: l == r,
    ast.NotEq: lambda l, r: l != r,
}

_POLARS_SAFE_FUNCTIONS = None


def _get_polars_safe_functions():
    global _POLARS_SAFE_FUNCTIONS
    if _POLARS_SAFE_FUNCTIONS is not None:
        return _POLARS_SAFE_FUNCTIONS
    if pl is None:
        _POLARS_SAFE_FUNCTIONS = {}
        return _POLARS_SAFE_FUNCTIONS
    _POLARS_SAFE_FUNCTIONS = {
        'abs': lambda e: e.abs(),
        'round': lambda e, decimals=pl.lit(0): e.round(0),
        'sqrt': lambda e: e.sqrt(),
        'ceil': lambda e: e.ceil(),
        'floor': lambda e: e.floor(),
        'log': lambda e: e.log(math.e),
        'log10': lambda e: e.log(10),
    }
    return _POLARS_SAFE_FUNCTIONS


def _ast_to_polars_expr(node: ast.AST, params: Dict[str, Any]) -> Any:
    """Рекурсивно преобразует AST-ноду в Polars выражение."""
    if isinstance(node, ast.Expression):
        return _ast_to_polars_expr(node.body, params)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return pl.lit(node.value)
        raise ValueError(f'Недопустимая константа: {node.value!r}')

    if isinstance(node, ast.Num):
        return pl.lit(node.n)

    if isinstance(node, ast.Name):
        name = node.id
        if name.startswith('$'):
            param_val = params.get(name[1:])
            if param_val is None:
                return pl.lit(None)
            try:
                return pl.lit(float(param_val))
            except (TypeError, ValueError):
                return pl.lit(param_val)
        funcs = _get_polars_safe_functions()
        if name in funcs:
            return ('__func__', name)
        return pl.col(name).cast(pl.Float64, strict=False)

    if isinstance(node, ast.BinOp):
        left = _ast_to_polars_expr(node.left, params)
        right = _ast_to_polars_expr(node.right, params)
        op_fn = _POLARS_BIN_OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError(f'Недопустимый оператор: {type(node.op).__name__}')
        return op_fn(left, right)

    if isinstance(node, ast.UnaryOp):
        operand = _ast_to_polars_expr(node.operand, params)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return operand
        raise ValueError(f'Недопустимый унарный оператор: {type(node.op).__name__}')

    if isinstance(node, ast.Call):
        func_node = node.func
        if isinstance(func_node, ast.Name):
            funcs = _get_polars_safe_functions()
            fn = funcs.get(func_node.id)
            if fn is None:
                raise ValueError(f'Неизвестная функция: {func_node.id}')
            args = [_ast_to_polars_expr(a, params) for a in node.args]
            if not args:
                raise ValueError(f'Функция {func_node.id} требует аргумент')
            return fn(args[0])
        raise ValueError('Вызов недопустимой функции')

    if isinstance(node, ast.Compare):
        left = _ast_to_polars_expr(node.left, params)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _ast_to_polars_expr(comparator, params)
            op_fn = _POLARS_CMP_OPS.get(type(op_node))
            if op_fn is None:
                raise ValueError(f'Недопустимый оператор сравнения: {type(op_node).__name__}')
            left = op_fn(left, right)
        return left

    if isinstance(node, ast.IfExp):
        test = _ast_to_polars_expr(node.test, params)
        body = _ast_to_polars_expr(node.body, params)
        orelse = _ast_to_polars_expr(node.orelse, params)
        return pl.when(test).then(body).otherwise(orelse)

    raise ValueError(f'Недопустимый элемент выражения: {type(node).__name__}')


def _build_polars_expr(expression: str, params: Dict[str, Any]) -> Any:
    """Парсит арифметическое выражение в Polars Expr."""
    tree = ast.parse(expression.strip(), mode='eval')
    return _ast_to_polars_expr(tree, params)


def apply_formulas_polars(df: Any, config: Dict[str, Any], params: Dict[str, Any] = None) -> Any:
    """
    Векторизованное применение формул через Polars выражения.
    Каждая формула парсится в pl.Expr и выполняется целиком по колонке.
    Работает и с DataFrame, и с LazyFrame (with_columns поддерживается обоими).
    """
    params = params or {}
    formulas = config.get('formulas') or []
    if not formulas:
        return df
    if not isinstance(df, pl.LazyFrame) and hasattr(df, 'is_empty') and df.is_empty():
        return df

    for formula in formulas:
        name = (formula.get('name') or '').strip()
        expression = (formula.get('expression') or '').strip()
        if not name or not expression:
            continue
        try:
            expr = _build_polars_expr(expression, params)
            df = df.with_columns(expr.alias(name))
        except Exception as e:
            logger.debug('Polars formula failed for %r, fallback to row-by-row: %s', expression, e)
            from .pipeline_types import collect_result
            if isinstance(df, pl.LazyFrame):
                df = collect_result(df)
            rows = df.to_dicts()
            for row in rows:
                row[name] = evaluate_formula(expression, row, params)
            df = pl.DataFrame(rows)
    return df


_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    'abs': abs,
    'round': round,
    'min': min,
    'max': max,
    'sqrt': math.sqrt,
    'ceil': math.ceil,
    'floor': math.floor,
    'log': math.log,
    'log10': math.log10,
}


class _FormulaEvaluator(ast.NodeVisitor):
    """Обходит AST арифметического выражения и вычисляет результат (row-by-row)."""

    def __init__(self, row: Dict[str, Any], params: Dict[str, Any] = None):
        self._row = row
        self._params = params or {}

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f'Недопустимая константа: {node.value!r}')

    def visit_Num(self, node: ast.Num) -> Any:
        return node.n

    def visit_Name(self, node: ast.Name) -> Any:
        name = node.id
        if name.startswith('$'):
            param_val = self._params.get(name[1:])
            if param_val is None:
                return None
            try:
                return float(param_val)
            except (TypeError, ValueError):
                return param_val
        if name in self._row:
            val = self._row[name]
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
        if name in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[name]
        raise ValueError(f'Неизвестное поле: {name}')

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if left is None or right is None:
            return None
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f'Недопустимый оператор: {type(node.op).__name__}')
        try:
            return op_func(left, right)
        except ZeroDivisionError:
            return None

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if operand is None:
            return None
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f'Недопустимый унарный оператор: {type(node.op).__name__}')
        return op_func(operand)

    def visit_Call(self, node: ast.Call) -> Any:
        func = self.visit(node.func)
        if not callable(func):
            raise ValueError('Вызов недопустимой функции')
        args = [self.visit(a) for a in node.args]
        if any(a is None for a in args):
            return None
        try:
            return func(*args)
        except Exception:
            return None

    def visit_IfExp(self, node: ast.IfExp) -> Any:
        test = self.visit(node.test)
        if test:
            return self.visit(node.body)
        return self.visit(node.orelse)

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if left is None or right is None:
                return False
            if isinstance(op_node, ast.Gt):
                if not (left > right):
                    return False
            elif isinstance(op_node, ast.GtE):
                if not (left >= right):
                    return False
            elif isinstance(op_node, ast.Lt):
                if not (left < right):
                    return False
            elif isinstance(op_node, ast.LtE):
                if not (left <= right):
                    return False
            elif isinstance(op_node, ast.Eq):
                if not (left == right):
                    return False
            elif isinstance(op_node, ast.NotEq):
                if not (left != right):
                    return False
            else:
                raise ValueError(f'Недопустимый оператор сравнения: {type(op_node).__name__}')
            left = right
        return True

    def generic_visit(self, node: ast.AST) -> Any:
        raise ValueError(f'Недопустимый элемент выражения: {type(node).__name__}')


def evaluate_formula(
    expression: str,
    row: Dict[str, Any],
    params: Dict[str, Any] = None,
) -> Any:
    """
    Безопасно вычисляет арифметическое выражение для одной строки данных.
    Поля строки доступны по имени. Параметры — по имени с префиксом $: $year.
    """
    if not expression or not expression.strip():
        return None
    try:
        tree = ast.parse(expression.strip(), mode='eval')
        return _FormulaEvaluator(row, params).visit(tree)
    except Exception as e:
        logger.debug('Formula eval error for %r: %s', expression, e)
        return None


def apply_formulas(
    data: PipelineRows,
    config: Dict[str, Any],
    params: Dict[str, Any] = None,
) -> PipelineRows:
    """
    Применяет список формул к данным (row-by-row fallback).
    config.formulas: [{ name: str, expression: str }, ...]
    """
    params = params or {}
    formulas = config.get('formulas') or []
    if not formulas or not data:
        return data

    result = []
    for row in data:
        new_row = dict(row)
        for formula in formulas:
            name = (formula.get('name') or '').strip()
            expression = (formula.get('expression') or '').strip()
            if not name or not expression:
                continue
            new_row[name] = evaluate_formula(expression, new_row, params)
        result.append(new_row)
    return result


def _validate_script(code: str) -> None:
    code_lower = code.lower()
    for kw in _FORBIDDEN_KEYWORDS:
        if kw.lower() in code_lower:
            raise ValueError(f'Запрещённая конструкция в скрипте: {kw.strip()}')


_SAFE_BUILTINS = {
    'len': len, 'range': range, 'enumerate': enumerate,
    'zip': zip, 'map': map, 'filter': filter,
    'sorted': sorted, 'reversed': reversed,
    'min': min, 'max': max, 'sum': sum,
    'abs': abs, 'round': round,
    'int': int, 'float': float, 'str': str, 'bool': bool,
    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
    'True': True, 'False': False, 'None': None,
    'isinstance': isinstance, 'type': type,
    'print': lambda *a, **kw: None,
}


def execute_python_script(data: PipelineRows, config: Dict[str, Any]) -> PipelineRows:
    """Выполняет пользовательский Python-скрипт над данными (List[Dict]) в песочнице."""
    code = (config.get('code') or '').strip()
    if not code or not data:
        return data

    _validate_script(code)

    sandbox_globals = {'__builtins__': _SAFE_BUILTINS}
    sandbox_locals = {'rows': [dict(r) for r in data]}

    try:
        exec(compile(code, '<pipeline_script>', 'exec'), sandbox_globals, sandbox_locals)
    except Exception as e:
        raise ValueError(f'Ошибка выполнения скрипта: {e}')

    result = sandbox_locals.get('rows')
    if not isinstance(result, list):
        raise ValueError('Скрипт должен оставить результат в переменной rows (список словарей)')
    if result and not isinstance(result[0], dict):
        raise ValueError('Каждый элемент rows должен быть словарём')
    return result


def execute_python_script_polars(df: Any, config: Dict[str, Any]) -> Any:
    """
    Выполняет Python-скрипт над Polars DataFrame.
    Скрипт получает переменные: df (DataFrame) и rows (ленивый список).
    Результат берётся из df или rows.
    """
    code = (config.get('code') or '').strip()
    if not code:
        return df
    if _POLARS_AVAILABLE and isinstance(df, pl.LazyFrame):
        from .pipeline_types import collect_result
        df = collect_result(df)
    if hasattr(df, 'is_empty') and df.is_empty():
        return df

    _validate_script(code)

    class _LazyRows:
        """Ленивый адаптер: to_dicts() вызывается только при обращении к rows."""
        def __init__(self, dataframe):
            self._df = dataframe
            self._rows = None

        def _materialize(self):
            if self._rows is None:
                self._rows = self._df.to_dicts()
            return self._rows

        def __iter__(self):
            return iter(self._materialize())

        def __len__(self):
            return self._df.height if self._rows is None else len(self._rows)

        def __getitem__(self, idx):
            return self._materialize()[idx]

        def __setitem__(self, idx, val):
            self._materialize()[idx] = val

        def append(self, val):
            self._materialize().append(val)

        def extend(self, vals):
            self._materialize().extend(vals)

    lazy_rows = _LazyRows(df)
    sandbox_globals = {'__builtins__': _SAFE_BUILTINS}
    sandbox_locals = {'rows': lazy_rows, 'df': df}

    try:
        exec(compile(code, '<pipeline_script>', 'exec'), sandbox_globals, sandbox_locals)
    except Exception as e:
        raise ValueError(f'Ошибка выполнения скрипта: {e}')

    result_df = sandbox_locals.get('df')
    if _POLARS_AVAILABLE and isinstance(result_df, pl.DataFrame):
        if result_df is not df:
            return result_df

    result_rows = sandbox_locals.get('rows')
    if result_rows is lazy_rows and lazy_rows._rows is None:
        return df

    if isinstance(result_rows, _LazyRows):
        if result_rows._rows is not None:
            return pl.DataFrame(result_rows._rows)
        return df

    if isinstance(result_rows, list):
        if not result_rows:
            return pl.DataFrame()
        if isinstance(result_rows[0], dict):
            return pl.DataFrame(result_rows)
        raise ValueError('Каждый элемент rows должен быть словарём')

    raise ValueError('Скрипт должен оставить результат в переменной rows или df')
