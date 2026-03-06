"""
Конфигурация Celery для модуля bi_analysis_modern.
Настройки задач бизнес-аналитики и их логирование.
"""

from typing import Dict, Any
from src.core.utils.celery.base import CeleryModuleConfig


class BIAnalysisCeleryConfig(CeleryModuleConfig):
    """Конфигурация Celery для модуля бизнес-аналитики."""

    def get_task_routes(self) -> Dict[str, Dict[str, Any]]:
        return {
            'modules.bi_analysis_modern.api.tasks.*': {'queue': 'bi_analysis'},
        }

    def get_task_queues(self) -> Dict[str, Dict[str, Any]]:
        return {
            'bi_analysis': {
                'exchange': 'bi_analysis',
                'routing_key': 'bi_analysis',
            }
        }

    def get_task_annotations(self) -> Dict[str, Dict[str, Any]]:
        from .config import CELERY_TASK_TIMEOUT, CELERY_SOFT_TIMEOUT

        return {
            'modules.bi_analysis_modern.api.tasks.process_draft_preview': {
                'time_limit': CELERY_TASK_TIMEOUT,
                'soft_time_limit': CELERY_SOFT_TIMEOUT,
            },
            'modules.bi_analysis_modern.api.tasks.process_file_preview': {
                'time_limit': CELERY_TASK_TIMEOUT,
                'soft_time_limit': CELERY_SOFT_TIMEOUT,
            },
            'modules.bi_analysis_modern.api.tasks.execute_pipeline_async': {
                'time_limit': 1800,
                'soft_time_limit': 1500,
            },
        }

    def get_additional_config(self) -> Dict[str, Any]:
        return {
            'bi_analysis_max_concurrent_tasks': 3,
            'bi_analysis_data_retention_days': 730,
            'bi_analysis_report_generation_interval': 86400,
        }
