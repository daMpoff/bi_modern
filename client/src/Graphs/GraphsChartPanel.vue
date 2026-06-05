<script setup>
import { ref, computed } from 'vue'
import { BarChart3 } from 'lucide-vue-next'
import ChartSettingsPreview from '@/modules/bi_analysis_modern/client/src/components/ChartSettingsPreview.vue'

const props = defineProps({
  chartConfig: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] },
  previewData: { type: Array, default: () => [] },
  hasChartNode: { type: Boolean, default: false } // true when pipeline has an output node
})

const emit = defineEmits(['apply'])

const chartSettingsRef = ref(null)

const configForPreview = computed(() => props.chartConfig)

function buildPayload() {
  const p = chartSettingsRef.value?.getPayload()
  if (!p) return null
  return {
    chartType: p.chartType,
    title: p.chartName || null,
    xField: p.xField,
    yFields: p.yFields,
    colorField: p.colorField
  }
}

function handleApply() {
  if (!chartSettingsRef.value?.canSave) return
  const p = buildPayload()
  if (p) emit('apply', p)
}

function getCurrentPayload() {
  return buildPayload()
}

defineExpose({ getCurrentPayload })
</script>

<template>
  <div class="graphs-chart-panel">
    <div v-if="!hasChartNode" class="chart-panel-empty">
      <BarChart3 :size="32" style="opacity: 0.4; margin-bottom: 0.5rem" />
      <p>Добавьте блок «Выход» и выполните пайплайн</p>
    </div>

    <ChartSettingsPreview
      v-else
      ref="chartSettingsRef"
      :available-fields="availableFields"
      :preview-data="previewData"
      :config="configForPreview"
    >
      <template #settings-footer="{ canSave }">
        <div class="field-group">
          <button
            type="button"
            class="apply-btn"
            :disabled="!canSave"
            @click="handleApply"
          >
            Применить
          </button>
        </div>
      </template>
    </ChartSettingsPreview>
  </div>
</template>

<style scoped lang="scss">
.graphs-chart-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.chart-panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  color: var(--color-secondary-text);
  font-size: 13px;
  line-height: 1.5;
  opacity: 0.9;
}

.apply-btn {
  width: 100%;
  padding: 0.6rem 0.75rem;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: var(--color-accent, #6D001A);
  color: white;
  transition: opacity 0.2s;

  &:hover:not(:disabled) {
    opacity: 0.9;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
</style>
