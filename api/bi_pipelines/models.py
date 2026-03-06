from django.db import models
from django.conf import settings


class Pipeline(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, default='', verbose_name='Описание')
    graph_data = models.JSONField(default=dict, blank=True, verbose_name='Граф пайплайна')
    params_schema = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Параметры пайплайна',
        help_text='Список параметров: [{name, type, default_value, label}]'
    )
    is_dashboard_only = models.BooleanField(
        default=False,
        verbose_name='Только для дашборда',
        help_text='Создан под один график на дашборде; не показывать в общем списке пайплайнов'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pipelines',
        verbose_name='Владелец'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    class Meta:
        verbose_name = 'Пайплайн'
        verbose_name_plural = 'Пайплайны'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class PipelineChart(models.Model):
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name='charts',
        verbose_name='Пайплайн'
    )
    name = models.CharField(max_length=255, verbose_name='Название')
    chart_type = models.CharField(max_length=50, verbose_name='Тип графика')
    chart_config = models.JSONField(default=dict, blank=True, verbose_name='Конфигурация графика')
    engine = models.CharField(max_length=32, default='echarts', verbose_name='Движок')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pipeline_charts',
        verbose_name='Владелец'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    class Meta:
        verbose_name = 'График пайплайна'
        verbose_name_plural = 'Графики пайплайнов'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.name} ({self.pipeline.name})'
