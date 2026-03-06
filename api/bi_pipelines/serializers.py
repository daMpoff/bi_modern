from rest_framework import serializers

from .models import Pipeline, PipelineChart


class PipelineSerializer(serializers.ModelSerializer):
    charts_count = serializers.SerializerMethodField()

    class Meta:
        model = Pipeline
        fields = [
            'id', 'name', 'description', 'graph_data', 'params_schema',
            'is_dashboard_only', 'charts_count', 'owner', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at', 'charts_count']

    def get_charts_count(self, obj):
        return obj.charts.count()


class PipelineChartSerializer(serializers.ModelSerializer):
    pipeline_name = serializers.SerializerMethodField()
    pipeline_is_dashboard_only = serializers.SerializerMethodField()

    class Meta:
        model = PipelineChart
        fields = [
            'id', 'pipeline', 'pipeline_name', 'pipeline_is_dashboard_only', 'name',
            'chart_type', 'chart_config', 'engine', 'owner', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'created_at', 'updated_at',
            'pipeline_name', 'pipeline_is_dashboard_only'
        ]

    def get_pipeline_name(self, obj):
        return obj.pipeline.name if obj.pipeline else None

    def get_pipeline_is_dashboard_only(self, obj):
        return getattr(obj.pipeline, 'is_dashboard_only', False) if obj.pipeline else False
