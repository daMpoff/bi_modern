<template>
  <ModalCenter
    modal-id="pipelineChartSettingsModal"
    standalone
    :visible="show"
    :dialog-style="{ maxWidth: '600px' }"
    :z-index="10050"
    body-class="p-0"
    @close="$emit('close')"
  >
    <template #title>
      <div class="pm-header-icon" style="background: rgba(6, 182, 212, 0.12); color: #06b6d4">
        <BarChart3 :size="20" />
      </div>
      <span>Настройки графика</span>
    </template>

    <div class="pm-body pm-body--chart-settings">
      <ChartSettingsPreview
        ref="chartSettingsRef"
        :available-fields="availableFieldsFormatted"
        :preview-data="effectivePreviewData"
        :config="configForPreview"
        :require-chart-name="false"
      />
    </div>

    <template #footer>
      <button class="pm-btn pm-btn--secondary" @click="$emit('close')">Отмена</button>
      <button class="pm-btn pm-btn--primary" :disabled="!canApply" @click="handleApply">Применить</button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, computed, inject } from 'vue'
import { BarChart3 } from 'lucide-vue-next'
import ModalCenter from '@/components/ModalCenter.vue'
import ChartSettingsPreview from '@/modules/bi_analysis_modern/client/src/components/ChartSettingsPreview.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  initialConfig: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] },
  previewData: { type: Array, default: () => [] },
  previewColumns: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'apply'])

const injectedPreviewData = inject('pipelinePreviewData', null)
const injectedPreviewColumns = inject('pipelinePreviewColumns', null)

const chartSettingsRef = ref(null)

const availableFieldsFormatted = computed(() =>
  (props.availableFields || []).map((f) => (typeof f === 'object' ? f : { name: String(f), type: 'auto' }))
)

const effectivePreviewData = computed(() => {
  const fromInject = injectedPreviewData?.value
  if (fromInject !== undefined && fromInject !== null) return Array.isArray(fromInject) ? fromInject : []
  return props.previewData || []
})

const configForPreview = computed(() => {
  const c = props.initialConfig
  if (!c) return null
  return {
    chartType: c.chartType || 'bar',
    title: c.title || '',
    xField: c.xField || '',
    yFields: c.yFields || [],
    colorField: c.colorField || ''
  }
})

const canApply = computed(() => chartSettingsRef.value?.canSave ?? false)

function handleApply() {
  const comp = chartSettingsRef.value
  if (!comp?.canSave) return
  const p = comp.getPayload()
  const fields = []
  if (p.xField) fields.push({ name: p.xField, role: 'x', aggregation: 'none' })
  for (const yf of p.yFields || []) {
    if (yf) fields.push({ name: yf, role: 'y', aggregation: 'none' })
  }
  if (p.colorField) fields.push({ name: p.colorField, role: 'color', aggregation: 'none' })

  emit('apply', {
    chartType: p.chartType || 'bar',
    fields,
    title: p.chartName || '',
    showLegend: true,
    showLabels: false,
    xField: p.xField,
    yFields: p.yFields || [],
    colorField: p.colorField || ''
  })
}
</script>

<style scoped lang="scss">
@import '../scss/pipeline-modals.scss';

.pm-body--chart-settings {
  max-height: 70vh;
  overflow-y: auto;
}
</style>
