from rest_framework import serializers

from .models import Dashboard, DashboardPage, DashboardItem


class DashboardItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardItem
        fields = ['id', 'type', 'x', 'y', 'width', 'height', 'config', 'order']


class DashboardPageSerializer(serializers.ModelSerializer):
    items = DashboardItemSerializer(many=True, read_only=True)

    class Meta:
        model = DashboardPage
        fields = ['id', 'name', 'order', 'items']


class DashboardPageWriteSerializer(serializers.ModelSerializer):
    items = DashboardItemSerializer(many=True, required=False)

    class Meta:
        model = DashboardPage
        fields = ['id', 'name', 'order', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        page = DashboardPage.objects.create(**validated_data)
        for idx, item_data in enumerate(items_data):
            item_data_copy = {k: v for k, v in item_data.items() if k != 'order'}
            DashboardItem.objects.create(page=page, order=idx, **item_data_copy)
        return page

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        instance.name = validated_data.get('name', instance.name)
        instance.order = validated_data.get('order', instance.order)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            for idx, item_data in enumerate(items_data):
                item_data_copy = {k: v for k, v in item_data.items() if k != 'order'}
                DashboardItem.objects.create(page=instance, order=idx, **item_data_copy)
        return instance


class DashboardSerializer(serializers.ModelSerializer):
    pages = DashboardPageSerializer(many=True, read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    charts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'owner', 'owner_username',
            'created_at', 'updated_at', 'pages', 'charts_count', 'placement_mode',
            'version', 'version_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'charts_count', 'version', 'version_at']


class DashboardWriteSerializer(serializers.ModelSerializer):
    pages = DashboardPageWriteSerializer(many=True, required=False)

    class Meta:
        model = Dashboard
        fields = ['id', 'name', 'description', 'pages', 'placement_mode']
        read_only_fields = ['id']

    def create(self, validated_data):
        from django.utils import timezone
        pages_data = validated_data.pop('pages', [])
        now = timezone.now()
        validated_data['version'] = 1
        validated_data['version_at'] = now
        dashboard = Dashboard.objects.create(**validated_data)
        for idx, page_data in enumerate(pages_data):
            items_data = page_data.pop('items', [])
            page_data.pop('order', None)
            page = DashboardPage.objects.create(dashboard=dashboard, order=idx, **page_data)
            for item_idx, item_data in enumerate(items_data):
                item_data_copy = {k: v for k, v in item_data.items() if k != 'order'}
                DashboardItem.objects.create(page=page, order=item_idx, **item_data_copy)
        return dashboard

    def update(self, instance, validated_data):
        from django.utils import timezone
        pages_data = validated_data.pop('pages', None)
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        if 'placement_mode' in validated_data:
            instance.placement_mode = validated_data.get('placement_mode')
        instance.version = (instance.version or 1) + 1
        instance.version_at = timezone.now()
        instance.save()
        if pages_data is not None:
            instance.pages.all().delete()
            for idx, page_data in enumerate(pages_data):
                items_data = page_data.pop('items', [])
                page_data.pop('order', None)
                page = DashboardPage.objects.create(dashboard=instance, order=idx, **page_data)
                for item_idx, item_data in enumerate(items_data):
                    item_data_copy = {k: v for k, v in item_data.items() if k != 'order'}
                    DashboardItem.objects.create(page=page, order=item_idx, **item_data_copy)
        return instance


class DashboardShortSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    charts_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Dashboard
        fields = [
            'id', 'name', 'description', 'owner_username',
            'created_at', 'updated_at', 'charts_count', 'placement_mode',
            'version', 'version_at'
        ]
