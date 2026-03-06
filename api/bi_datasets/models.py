from django.db import models
from django.contrib.auth import get_user_model
import uuid

from ..bi_connections.models import Connection


class FileUpload(models.Model):
    objects: models.Manager['FileUpload']

    name = models.CharField(max_length=255)
    connection = models.ForeignKey(Connection, null=True, blank=True, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='uploaded_files')
    columns_info = models.JSONField(null=True, blank=True, default=dict)

    original_filename = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)
    file_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.file_uuid:
            self.file_uuid = uuid.uuid4()
        super().save(*args, **kwargs)
