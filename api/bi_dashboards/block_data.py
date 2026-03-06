# -*- coding: utf-8 -*-
"""
Получение данных для блока дашборда по type и config.
"""
import logging
from typing import Any, Dict, List

from .models import DashboardItem

logger = logging.getLogger(__name__)

BLOCK_TYPE_CHART = 'График'
BLOCK_TYPE_CHART_LEGACY = 'Чарт'


def get_block_data(
    item: DashboardItem,
    user,
    params: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Возвращает данные для отображения блока по type и config.
    Для типа «График»/«Чарт» данные не возвращаются здесь — клиент использует PipelineChart API.
    params — значения параметров пайплайна (от селекторов дашборда).
    """
    params = params or {}
    block_type = (item.type or '').strip()

    if block_type in (BLOCK_TYPE_CHART, BLOCK_TYPE_CHART_LEGACY):
        return []

    logger.debug('Block type %s has no data executor', block_type)
    return []
