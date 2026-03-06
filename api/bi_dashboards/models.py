from django.db import models
from django.conf import settings

JSONField = models.JSONField


class Dashboard(models.Model):
    PLACEMENT_MODE_CHOICES = [
        ('grid', 'Сетка (12 колонок)'),
        ('absolute', 'Абсолютное размещение'),
    ]

    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, default='', verbose_name='Описание')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bi_modern_dashboards',
        verbose_name='Владелец'
    )
    placement_mode = models.CharField(
        max_length=20,
        choices=PLACEMENT_MODE_CHOICES,
        blank=True,
        null=True,
        verbose_name='Режим размещения'
    )
    version = models.PositiveIntegerField(default=1, verbose_name='Версия')
    version_at = models.DateTimeField(null=True, blank=True, verbose_name='Время версии')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    class Meta:
        verbose_name = 'Дашборд'
        verbose_name_plural = 'Дашборды'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def charts_count(self):
        chart_ids = set()
        for page in self.pages.all():
            for item in page.items.all():
                if item.type == 'Чарт' and item.config:
                    charts_list = item.config.get('chartsList', [])
                    for chart_data in charts_list:
                        if isinstance(chart_data, dict) and 'id' in chart_data:
                            chart_ids.add(chart_data['id'])
                        elif isinstance(chart_data, int):
                            chart_ids.add(chart_data)
        return len(chart_ids)


class DashboardPage(models.Model):
    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name='pages',
        verbose_name='Дашборд'
    )
    name = models.CharField(max_length=255, verbose_name='Название страницы')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Страница дашборда'
        verbose_name_plural = 'Страницы дашборда'
        ordering = ['order', 'id']
        unique_together = [['dashboard', 'order']]

    def __str__(self):
        return f"{self.dashboard.name} - {self.name}"


class DashboardItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('График', 'График'),
        ('Текст', 'Текст'),
        ('Фото', 'Фото'),
        ('Видео', 'Видео'),
        ('Таблица', 'Таблица'),
        ('Текст + элемент', 'Текст + элемент'),
        ('Заголовок', 'Заголовок'),
        ('Чарт', 'Чарт'),
        ('Селектор', 'Селектор'),
    ]

    page = models.ForeignKey(
        DashboardPage,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Страница'
    )
    type = models.CharField(
        max_length=50,
        choices=ITEM_TYPE_CHOICES,
        verbose_name='Тип элемента'
    )
    x = models.IntegerField(default=0, verbose_name='Позиция X')
    y = models.IntegerField(default=0, verbose_name='Позиция Y')
    width = models.IntegerField(default=200, verbose_name='Ширина')
    height = models.IntegerField(default=150, verbose_name='Высота')
    config = models.JSONField(default=dict, blank=True, verbose_name='Конфигурация')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Элемент дашборда'
        verbose_name_plural = 'Элементы дашборда'
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.page.dashboard.name} - {self.type}"
