from django.db import migrations


def rename_dashboard_route(apps, schema_editor):
    MenuItem = apps.get_model('cms_adp', 'MenuItem')
    MenuItem.objects.filter(
        module_source='modules/bi_analysis_modern',
        route_name='Dashboards',
    ).update(route_name='DashboardsModern')


def restore_dashboard_route(apps, schema_editor):
    MenuItem = apps.get_model('cms_adp', 'MenuItem')
    MenuItem.objects.filter(
        module_source='modules/bi_analysis_modern',
        route_name='DashboardsModern',
    ).update(route_name='Dashboards')


class Migration(migrations.Migration):
    dependencies = [('bi_analysis_modern', '0001_menu_data')]
    operations = [migrations.RunPython(rename_dashboard_route, restore_dashboard_route)]
