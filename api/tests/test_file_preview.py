from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from openpyxl import Workbook
from rest_framework.test import APIRequestFactory, force_authenticate

from ..bi_datasets.binary_storage import convert_to_binary, read_from_binary
from ..bi_datasets.models import FileUpload
from ..bi_datasets.views import XlsxTempPreviewView
from ..services.services import count_file_rows, read_file_preview_slice, read_file_to_dataframe
from ..tasks import process_file_preview


class FilePreviewTests(SimpleTestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'sheets.xlsx'
        book = Workbook()
        book.active.title = 'Summary'
        book.active.append(['Total'])
        book.active.append([3])
        details = book.create_sheet('Details')
        for row in [['Name', 'Qty'], ['A', 1], ['B', 2]]:
            details.append(row)
        book.save(self.path)
        book.close()

    def test_api_preserves_first_data_row_without_header(self):
        request = APIRequestFactory().post('/preview/', {
            'temp_path': 'upload', 'has_header': False, 'row_limit': 1, 'sheet_name': 'Details',
        }, format='json')
        force_authenticate(request, user=SimpleNamespace(pk=1, is_authenticated=True))
        with patch('modules.bi_analysis_modern.api.bi_datasets.views.resolve_upload', return_value=str(self.path)):
            response = XlsxTempPreviewView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['parsed'], [['Name', 'Qty']])

    def test_worker_preview_default_sheet_and_unlimited_selected_sheet(self):
        with patch.object(process_file_preview, 'update_state'):
            self.assertEqual(process_file_preview.run(str(self.path), None, 1), {'parsed': [['Total'], [3]]})
            result = process_file_preview.run(str(self.path), 'Details', None)
        self.assertEqual(result['parsed'], [['Name', 'Qty'], ['A', 1], ['B', 2]])

    def test_saved_workbook_preserves_selected_sheet_and_pagination(self):
        upload = SimpleNamespace(file=SimpleNamespace(path=str(self.path)), file_type='xlsx')
        with patch.object(FileUpload.objects, 'get', return_value=upload):
            self.assertEqual(count_file_rows(1, 'Details'), 2)
            self.assertEqual(read_file_to_dataframe(1, 'Details', 1).rows, [['A', 1]])
            columns, rows, sheets = read_file_preview_slice(upload, 1, 1, 'utf8', ',', 'Details')
        self.assertEqual((columns, rows, sheets), (['Name', 'Qty'], [['B', 2]], ['Summary', 'Details']))

    def test_selected_sheet_round_trips_through_arrow_ipc(self):
        binary = str(self.path.with_suffix('.bin'))
        self.assertTrue(convert_to_binary(str(self.path), binary, sheet_name='Details'))
        columns, rows = read_from_binary(binary)
        self.assertEqual((columns, rows), (['Name', 'Qty'], [['A', 1], ['B', 2]]))
