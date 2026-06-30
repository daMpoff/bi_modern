# -*- coding: utf-8 -*-
"""
Миграция данных: заполнение меню модуля BI Analysis Modern.
"""

from django.db import migrations


def populate_menu(apps, schema_editor):
    from src.core.cms.adp.menu.migration_utils import MenuMigrationHelper

    helper = MenuMigrationHelper(apps, 'modules/bi_analysis_modern')
    helper.clear_module_items()

    root = helper.create_group(
        'Бизнес-аналитика',
        'BIModern',
        icon='BarChart2',
    )
    helper.create_routes_batch([
        ('Дашборды', 'Dashboards', 'LayoutDashboard'),
        ('Пайплайны', 'Pipelines', 'GitBranch'),
        ('Подключения', 'ConnectionsModern', 'Database'),
    ], parent=root)


def reverse_populate_menu(apps, schema_editor):
    MenuItem = apps.get_model('cms_adp', 'MenuItem')
    MenuItem.objects.filter(module_source='modules/bi_analysis_modern').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('cms_adp', '0007_populate_core_menu'),
    ]

    operations = [
        migrations.RunPython(populate_menu, reverse_populate_menu),
    ]
