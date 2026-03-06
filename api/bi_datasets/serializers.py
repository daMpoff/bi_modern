from rest_framework import serializers
import os

from .models import FileUpload


class FileUploadSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_path = serializers.SerializerMethodField()
    exists = serializers.SerializerMethodField()
    missing = serializers.SerializerMethodField()
    file_not_found = serializers.SerializerMethodField()
    error = serializers.SerializerMethodField()

    class Meta:
        model = FileUpload
        fields = [
            'id', 'name', 'file', 'file_url', 'file_path', 'uploaded_at',
            'owner', 'original_filename', 'file_type', 'connection', 'columns_info',
            'file_uuid', 'exists', 'missing', 'file_not_found', 'error'
        ]
        read_only_fields = ['id', 'uploaded_at', 'file_uuid']
        extra_kwargs = {
            'owner': {'read_only': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_exists_cache = {}

    def get_file_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None

    def get_file_path(self, obj):
        try:
            return obj.file.path if obj.file else None
        except ValueError:
            return None

    def get_exists(self, obj):
        cache_key = obj.id if obj.id else id(obj)
        if cache_key not in self._file_exists_cache:
            try:
                if obj.file and hasattr(obj.file, 'path'):
                    self._file_exists_cache[cache_key] = os.path.exists(obj.file.path)
                else:
                    self._file_exists_cache[cache_key] = False
            except (ValueError, AttributeError):
                self._file_exists_cache[cache_key] = False
        return self._file_exists_cache[cache_key]

    def get_missing(self, obj):
        return not self.get_exists(obj)

    def get_file_not_found(self, obj):
        return self.get_missing(obj)

    def get_error(self, obj):
        if self.get_missing(obj):
            return "Файл не найден на диске"
        return None
