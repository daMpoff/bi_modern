from contextlib import nullcontext
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache.backends.locmem import LocMemCache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIRequestFactory, force_authenticate

from ..bi_connections.models import Connection
from ..bi_datasets import views
from ..bi_datasets.models import FileUpload
from ..bi_datasets.serializers import FileUploadSerializer
from ..bi_datasets.temp_uploads import resolve_upload
from ..tasks import process_file_preview


class TempUploadTests(SimpleTestCase):
    def setUp(self):
        self.user = get_user_model()(pk=17)
        self.second_user = get_user_model()(pk=18)
        self.requests = APIRequestFactory()
        tempdir = self.enterContext(TemporaryDirectory())
        self.enterContext(patch('tempfile.tempdir', tempdir))
        self.media = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(override_settings(MEDIA_ROOT=str(self.media)))
        cache = LocMemCache('bi-modern-preview-tests', {})
        cache.clear()
        self.enterContext(patch.object(views, 'execution_cache', return_value=cache))

    def post(self, view, data, user=None):
        request = self.requests.post('/', data, format='multipart')
        force_authenticate(request, user=user or self.user)
        return view.as_view()(request)

    def upload(self):
        upload = SimpleUploadedFile('sales.csv', b'item,count\nA,2\n')
        response = self.post(views.TempUploadView, {'file': upload})
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_preview_and_finalize_require_the_issued_reference_for_this_user(self):
        upload = self.upload()
        reference = upload['temp_path']
        own_path = Path(resolve_upload(reference, self.user))
        self.assertEqual(own_path.read_bytes(), b'item,count\nA,2\n')
        self.assertIsNone(resolve_upload(str(own_path), self.user))
        self.assertIsNone(resolve_upload(reference, self.second_user))
        self.assertEqual(self.post(views.XlsxTempPreviewView, {'temp_path': reference}, self.second_user).status_code, 404)
        self.assertEqual(self.post(views.FinalizeUploadView, {**upload, 'name': 'Sales'}, self.second_user).status_code, 404)
        self.assertTrue(own_path.exists())

    def test_finalize_resolves_connection_in_the_current_users_queryset(self):
        upload = self.upload()
        with patch.object(Connection.objects, 'get', side_effect=Connection.DoesNotExist) as lookup:
            response = self.post(views.FinalizeUploadView, {**upload, 'name': 'Sales', 'connection': '42'})
        self.assertEqual(response.status_code, 404)
        lookup.assert_called_once_with(pk='42', owner=self.user)
        self.assertIsNotNone(resolve_upload(upload['temp_path'], self.user))

    def test_update_serializer_limits_connection_choices(self):
        request = self.requests.patch('/')
        request.user = self.user
        serializer = FileUploadSerializer(context={'request': request})
        queryset = serializer.fields['connection'].queryset
        condition, = queryset.query.where.children
        self.assertEqual((condition.lhs.target.name, condition.rhs), ('owner', self.user.pk))

    def test_finalize_without_conversion_can_retry_and_stores_only_requested_sheet(self):
        with BytesIO() as output:
            book = Workbook()
            book.create_sheet('Sales').append(['price'])
            book.save(output)
            book.close()
            file = SimpleUploadedFile('book.xlsx', output.getvalue())
        upload = self.post(views.TempUploadView, {'file': file}).data
        data = {**upload, 'name': 'Sales'}
        with patch.object(views, 'convert_to_binary', return_value=False), patch.object(FileUpload, 'save') as insert:
            invalid = self.post(views.FinalizeUploadView, {**data, 'sheet': 'Absent'})
            self.assertEqual(invalid.status_code, 400)
            insert.assert_not_called()
            self.assertEqual(list(self.media.iterdir()), [])
            self.assertIsNotNone(resolve_upload(upload['temp_path'], self.user))
            result = self.post(views.FinalizeUploadView, {**data, 'sheet': 'Sales'})
            self.assertEqual(result.status_code, 201)
            insert.assert_called_once_with(force_insert=True)
        self.assertIsNone(resolve_upload(upload['temp_path'], self.user))
        with open(result.data['file_path'], 'rb') as stored:
            book = load_workbook(stored, read_only=True)
            try:
                self.assertEqual(book.sheetnames, ['Sales'])
            finally:
                book.close()

    def test_only_preview_creator_can_poll_queued_task(self):
        upload = self.upload()
        with patch.object(process_file_preview, 'apply_async') as enqueue:
            response = self.post(views.XlsxTempPreviewView, {'temp_path': upload['temp_path'], 'async': 'true'})
        self.assertEqual(response.status_code, 202)
        task_id = response.data['task_id']
        self.assertEqual(enqueue.call_args.kwargs['task_id'], task_id)
        for user, expected_status in [(self.second_user, 404), (self.user, 200)]:
            request = self.requests.get('/', {'task_id': task_id})
            force_authenticate(request, user=user)
            with patch('celery.result.AsyncResult', return_value=Mock(state='PENDING')) as result:
                response = views.FilePreviewTaskStatusView.as_view()(request)
            self.assertEqual(response.status_code, expected_status)
            self.assertEqual(result.called, user == self.user)


class FileReplacementTests(SimpleTestCase):
    def setUp(self):
        self.media = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(override_settings(MEDIA_ROOT=str(self.media)))
        self.user = get_user_model()(pk=17)
        self.instance = FileUpload(id=1, name='Report', original_filename='old.csv',
                                   file_type='csv', owner=self.user)
        self.instance.file.save('old.csv', SimpleUploadedFile('old.csv', b'a,b\n1,2'), save=False)
        self.old_path = Path(self.instance.file.path)
        self.enterContext(patch.object(views.FileUploadDetailView, 'get_object', return_value=self.instance))
        self.enterContext(patch.object(views, 'get_object_or_404', return_value=self.instance))
        self.enterContext(patch.object(views.transaction, 'atomic', return_value=nullcontext()))
        self.after_commit = self.enterContext(patch.object(views.transaction, 'on_commit'))
        self.save = self.enterContext(patch.object(FileUpload, 'save'))

    def update(self, **fields):
        request = APIRequestFactory().patch('/', fields, format='multipart')
        force_authenticate(request, user=self.user)
        return views.FileUploadDetailView.as_view()(request, pk=self.instance.pk)

    def workbook(self):
        with BytesIO() as output:
            book = Workbook()
            book.create_sheet('Sales').append(['price'])
            book.save(output)
            book.close()
            return SimpleUploadedFile('sales.xlsx', output.getvalue())

    def test_rename_preserves_type_filename_and_contents(self):
        self.assertEqual(self.update(name='Renamed').status_code, 200)
        self.assertEqual((self.instance.file_type, self.instance.original_filename), ('csv', 'old.csv'))
        self.assertEqual(self.old_path.read_bytes(), b'a,b\n1,2')
        self.after_commit.assert_not_called()

    def test_missing_sheet_rejects_replacement_before_saving(self):
        response = self.update(file=self.workbook(), sheet='Absent')
        self.assertEqual(response.status_code, 400)
        self.save.assert_not_called()
        self.assertEqual(self.old_path.read_bytes(), b'a,b\n1,2')

    def test_keeps_selected_sheet_and_retires_old_file_only_on_commit(self):
        self.assertEqual(self.update(file=self.workbook(), sheet='Sales').status_code, 200)
        self.assertEqual(self.instance.file_type, 'xlsx')
        with open(self.instance.file.path, 'rb') as stored:
            book = load_workbook(stored, read_only=True)
            try:
                self.assertEqual(book.sheetnames, ['Sales'])
            finally:
                book.close()
        self.assertTrue(self.old_path.exists())
        self.after_commit.call_args.args[0]()
        self.assertFalse(self.old_path.exists())

    def test_storage_rolls_back_replacement_if_database_save_fails(self):
        self.save.side_effect = RuntimeError('DB unavailable')
        with self.assertRaisesRegex(RuntimeError, 'DB unavailable'):
            self.update(file=SimpleUploadedFile('new.csv', b'x\n4'))
        self.assertEqual(list(self.old_path.parent.iterdir()), [self.old_path])
        self.after_commit.assert_not_called()
