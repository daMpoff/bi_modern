<script setup>
import { ref, computed, watch } from 'vue'
import { X } from 'lucide-vue-next'
import ChartSettingsPreview from '@/modules/bi_analysis_modern/client/src/components/ChartSettingsPreview.vue'

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
  <div v-if="show" class="chart-modal-overlay" @click.self="emit('close')">
    <div class="chart-modal" @click.stop>
      <div class="chart-modal-header">
        <h3 class="chart-modal-title">{{ chart ? 'Редактировать график' : 'Новый график' }}</h3>
        <button class="chart-modal-close" @click="emit('close')">
          <X :size="20" />
        </button>
      </div>

      <div class="chart-modal-body">
        <ChartSettingsPreview
          ref="chartSettingsRef"
          :available-fields="availableFields"
          :preview-data="previewData"
          :config="configForPreview"
        />
      </div>

      <div class="chart-modal-footer">
        <button class="modal-btn modal-btn-secondary" @click="emit('close')">Отмена</button>
        <button
          class="modal-btn modal-btn-primary"
          :disabled="!canSave()"
          @click="handleSave"
        >
          {{ chart ? 'Сохранить' : 'Создать' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chart-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  padding: 2rem;
}

.chart-modal {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  width: 900px;
  max-width: calc(100vw - 4rem);
  max-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.chart-modal-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.chart-modal-close {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary, #666);
  padding: 0.25rem;
  border-radius: 6px;
  display: flex;
  &:hover {
    background: rgba(0, 0, 0, 0.05);
  }
}

.chart-modal-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.chart-modal-body :deep(.chart-settings-preview) {
  width: 100%;
}

.chart-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
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
  color: var(--color-text-primary);
  &:hover:not(:disabled) {
    background: rgba(0, 0, 0, 0.1);
  }
}

.modal-btn-primary {
  background: var(--color-accent, #e53935);
  color: white;
  box-shadow: 0 2px 8px rgba(229, 57, 53, 0.3);
  &:hover:not(:disabled) {
    background: #c62828;
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
