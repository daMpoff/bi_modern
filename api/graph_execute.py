"""Публичная точка входа для выполнения BI-конвейера."""
from .execution.graph_execute import execute_graph

__all__ = ["execute_graph"]
