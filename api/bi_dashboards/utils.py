# -*- coding: utf-8 -*-
from .models import DashboardItem


def remove_dashboard_blocks_by_chart_id(chart_id):
    """
    Удаляет все блоки дашбордов (тип График/Чарт), в config которых указан данный pipelineChartId.
    Возвращает количество удалённых записей.
    """
    qs = DashboardItem.objects.filter(
        type__in=['График', 'Чарт'],
        config__pipelineChartId=chart_id
    )
    count, _ = qs.delete()
    return count
