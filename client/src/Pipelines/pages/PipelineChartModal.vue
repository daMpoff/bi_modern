<script setup>
import { ref, computed, watch } from 'vue'
import ChartSettingsPreview from '@/modules/bi_analysis_modern/client/src/components/ChartSettingsPreview.vue'
import ModalCenter from '@/components/ModalCenter.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  chart: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] },
  previewData: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'save'])

const chartSettingsRef = ref(null)

const configForPreview = computed(() => {
  if (!props.chart) return null
  return {
    name: props.chart.name,
    chart_type: props.chart.chart_type,
    chart_config: props.chart.chart_config || {}
  }
})

watch(
  () => props.show,
  (isOpen) => {
    if (!isOpen) return
    if (!props.chart) {
      chartSettingsRef.value = null
      return
    }
    chartSettingsRef.value = null
  }
)

function handleSave() {
  const comp = chartSettingsRef.value
  if (!comp?.canSave) return
  const p = comp.getPayload()
  emit('save', {
    name: p.chartName,
    chart_type: p.chartType,
    engine: 'echarts',
    chart_config: {
      xField: p.xField,
      yFields: p.yFields,
      colorField: p.colorField
    }
  })
}

function canSave() {
  return chartSettingsRef.value?.canSave ?? false
}
</script>

<template>
  <ModalCenter
    modal-id="pipelineChartModal"
    standalone
    :visible="show"
    :title="chart ? 'Редактировать график' : 'Новый график'"
    :dialog-style="{ width: '900px', maxWidth: 'calc(100vw - 4rem)', maxHeight: 'calc(100vh - 4rem)' }"
    :z-index="10001"
    :close-on-esc="false"
    body-class="p-0"
    @close="emit('close')"
  >
    <div class="chart-modal-body">
      <ChartSettingsPreview
        ref="chartSettingsRef"
        :available-fields="availableFields"
        :preview-data="previewData"
        :config="configForPreview"
      />
    </div>

    <template #footer>
      <button class="modal-btn modal-btn-secondary" @click="emit('close')">Отмена</button>
      <button
        class="modal-btn modal-btn-primary"
        :disabled="!canSave()"
        @click="handleSave"
      >
        {{ chart ? 'Сохранить' : 'Создать' }}
      </button>
    </template>
  </ModalCenter>
</template>

<style scoped lang="scss">
.chart-modal-body {
  display: flex;
  overflow: hidden;
  min-height: 60vh;
}

.chart-modal-body :deep(.chart-settings-preview) {
  width: 100%;
}

.modal-btn {
  padding: 0.6rem 1.5rem;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.modal-btn-secondary {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-primary-text);
  &:hover:not(:disabled) {
    background: rgba(0, 0, 0, 0.1);
  }
}

.modal-btn-primary {
  background: var(--color-accent, #6D001A);
  color: white;
  box-shadow: 0 2px 8px rgba(109, 0, 26, 0.3);
  &:hover:not(:disabled) {
    background: #50000F;
  }
}

@media (max-width: 768px) {
  .chart-modal-body :deep(.chart-settings-preview) {
    flex-direction: column;
  }
  .chart-modal-body :deep(.chart-modal-settings) {
    width: 100%;
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }
}
</style>
