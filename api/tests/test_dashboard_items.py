from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ..bi_dashboards.models import Dashboard, DashboardPage
from ..bi_dashboards.views import DashboardItemListCreateView


class DashboardItemPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='dashboard-editor')
        dashboard = Dashboard.objects.create(name='Продажи', owner=cls.user)
        cls.page = DashboardPage.objects.create(dashboard=dashboard, name='Обзор')
        second_user = get_user_model().objects.create_user(username='second-editor')
        second_dashboard = Dashboard.objects.create(name='Бюджет', owner=second_user)
        cls.second_page = DashboardPage.objects.create(dashboard=second_dashboard, name='План')
        cls.second_page.items.create(type='Текст')

    def request(self, method, data):
        factory = APIRequestFactory()
        request = getattr(factory, method)('/', data, format='json')
        force_authenticate(request, user=self.user)
        return DashboardItemListCreateView.as_view()(request)

    def test_created_item_is_listed_on_its_owners_page(self):
        created = self.request('post', {'page': self.page.pk, 'type': 'Текст'})
        self.assertEqual(created.status_code, 201)
        visible = self.request('get', {'page': self.page.pk})
        self.assertEqual(visible.status_code, 200)
        self.assertEqual([item['id'] for item in visible.data], [created.data['id']])

    def test_item_list_is_scoped_to_the_current_owner(self):
        response = self.request('get', {'page': self.second_page.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_dashboard_counts_distinct_modern_and_legacy_charts(self):
        self.page.items.create(type='График', config={'pipelineChartId': 12})
        self.page.items.create(type='Чарт', config={'chartsList': [{'id': '12'}, 23]})
        self.assertEqual(self.page.dashboard.charts_count, 2)

    def test_new_items_require_a_page(self):
        self.assertEqual(self.request('post', {'type': 'Текст'}).status_code, 400)
        self.assertEqual(self.request('post', {'page': self.second_page.pk, 'type': 'Текст'}).status_code, 404)
