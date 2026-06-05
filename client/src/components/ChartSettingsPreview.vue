<script setup>
/**
 * Единый блок настроек графика и превью.
 * Используется в разделе «Данные» (модалка Новый/Редактировать график) и в дашборде (правая панель настроек графика).
 * Стили и разметка одинаковые — правки в одном месте.
 */
import { ref, computed, watch } from 'vue'
import BiEchartsChart from '@/modules/bi_analysis_modern/client/src/components/BiEchartsChart.vue'
import { buildEchartsOption } from '@/modules/bi_analysis_modern/client/src/js/buildEchartsOption.js'
import { CHART_TYPES } from '@/modules/bi_analysis_modern/client/src/js/chartTypes.js'

/** Типы графика для выбора (value/label из единого реестра CHART_TYPES). */
const chartTypes = CHART_TYPES.map((ct) => ({ value: ct.chartType, label: ct.label }))

const props = defineProps({
  /** Поля для осей (массив { name, type } или строки) */
  availableFields: { type: Array, default: () => [] },
  /** Данные для превью графика */
  previewData: { type: Array, default: () => [] },
  /**
   * Начальный конфиг. Поддерживаются форматы:
   * - из Данные (chart): { name, chart_type, chart_config: { xField, yFields, colorField } }
   * - из дашборда: { chartType, title, xField, yFields, colorField }
   */
  config: { type: Object, default: null },
  /** Требовать ли название для canSave (в контексте пайплайна можно опустить) */
  requireChartName: { type: Boolean, default: true }
})

const chartName = ref('')
const chartType = ref('bar')
const xField = ref('')
const yFields = ref([])
const colorField = ref('')

const effectiveAvailableFields = computed(() => {
  const base = [...(props.availableFields || [])].map((f) =>
    typeof f === 'object' ? f : { name: String(f), type: 'auto' }
  )
  const namesSet = new Set(base.map((f) => f.name))
  const cfg = props.config?.chart_config || props.config
  const fromConfig = [
    cfg?.xField,
    ...(Array.isArray(cfg?.yFields) ? cfg.yFields : cfg?.yFields ? [cfg.yFields] : []),
    cfg?.colorField
  ].filter(Boolean)
  for (const name of fromConfig) {
    if (name && !namesSet.has(name)) {
      namesSet.add(name)
      base.push({ name: String(name), type: 'auto' })
    }
  }
  return base
})

const fieldNames = computed(() => effectiveAvailableFields.value.map((f) => f.name))

function toggleYField(field) {
  const idx = yFields.value.indexOf(field)
  if (idx >= 0) yFields.value.splice(idx, 1)
  else yFields.value.push(field)
}

const echartsOption = computed(() =>
  buildEchartsOption(props.previewData, chartType.value, xField.value, yFields.value, null, {
    colorField: chartType.value === 'heatmap' ? colorField.value : undefined
  })
)

const canSave = computed(() => {
  const isHeatmap = chartType.value === 'heatmap'
  const hasRequired = xField.value && yFields.value.length > 0
  const heatmapRequiresColor = !isHeatmap || !!colorField.value
  const ok = hasRequired && heatmapRequiresColor
  if (!props.requireChartName) return !!ok
  return chartName.value.trim() !== '' && ok
})

function getPayload() {
  return {
    chartName: chartName.value.trim(),
    chartType: chartType.value,
    xField: xField.value,
    yFields: [...yFields.value],
    colorField: colorField.value || null
  }
}

watch(
  () => props.config,
  (cfg) => {
    if (!cfg) {
      chartType.value = 'bar'
      xField.value = fieldNames.value[0] || ''
      yFields.value = fieldNames.value.length > 1 ? [fieldNames.value[1]] : []
      colorField.value = ''
      chartName.value = ''
      return
    }
    const type = cfg.chart_type ?? cfg.chartType ?? 'bar'
    const title = cfg.name ?? cfg.title ?? ''
    const inner = cfg.chart_config || cfg
    chartType.value = type
    chartName.value = title
    xField.value = inner.xField || ''
    const rawY = inner.yFields
    yFields.value = Array.isArray(rawY) ? [...rawY] : rawY ? [rawY] : []
    colorField.value = inner.colorField || ''
  },
  { immediate: true, deep: true }
)

watch(
  () => props.availableFields,
  () => {
    const names = fieldNames.value
    if (!xField.value && names.length) xField.value = names[0]
    if (!yFields.value.length && names.length > 1) yFields.value = [names[1]]
  },
  { deep: true }
)

defineExpose({ getPayload, canSave })
</script>

<template>
  <div class="chart-settings-preview">
    <div class="chart-modal-settings">
      <div class="field-group">
        <label class="field-label">Название</label>
        <input
          v-model="chartName"
          type="text"
          class="field-input"
          placeholder="Название графика"
        />
      </div>

      <div class="field-group">
        <label class="field-label">Тип графика</label>
        <div class="chart-type-options">
          <button
            v-for="ct in chartTypes"
            :key="ct.value"
            type="button"
            class="chart-type-btn"
            :class="{ active: chartType === ct.value }"
            @click="chartType = ct.value"
          >
            {{ ct.label }}
          </button>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">Ось X / Категория</label>
        <select v-model="xField" class="field-select">
          <option value="" disabled>Выберите поле</option>
          <option v-for="f in fieldNames" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>

      <div class="field-group">
        <label class="field-label">{{ chartType === 'heatmap' ? 'Значение (мера)' : 'Ось Y / Значения' }}</label>
        <div class="y-fields-list">
          <label
            v-for="f in fieldNames"
            :key="f"
            class="y-field-checkbox"
            :class="{ checked: yFields.includes(f) }"
          >
            <input
              type="checkbox"
              :checked="yFields.includes(f)"
              @change="toggleYField(f)"
            />
            {{ f }}
          </label>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">{{ chartType === 'heatmap' ? 'Ось Y / Категория' : 'Поле цвета (опционально)' }}</label>
        <select v-model="colorField" class="field-select">
          <option value="">{{ chartType === 'heatmap' ? 'Выберите поле' : 'Нет' }}</option>
          <option v-for="f in fieldNames" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>

      <slot name="settings-footer" :can-save="canSave" :get-payload="getPayload" />
    </div>

    <div class="chart-modal-preview">
      <div v-if="echartsOption" class="chart-preview-container">
        <BiEchartsChart :option="echartsOption" style="height: 100%; width: 100%" />
      </div>
      <div v-else class="chart-preview-empty">
        Выберите поля для предпросмотра графика
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
/* Общие стили — как в модалке «Новый график» (Данные). Один источник правок. */
.chart-settings-preview {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.chart-modal-settings {
  width: 300px;
  padding: 1.25rem;
  overflow-y: auto;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.field-group {
  margin-bottom: 1.25rem;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary-text);
  margin-bottom: 0.5rem;
}

.field-input,
.field-select {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  font-size: 13px;
  transition: border-color 0.2s;

  &:focus {
    border-color: rgba(var(--bs-warning-rgb), 0.5);
    outline: none;
    box-shadow: 0 0 0 2px rgba(var(--bs-warning-rgb), 0.1);
  }
}

.chart-type-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.4rem;
}

.chart-type-btn {
  padding: 0.5rem;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba(var(--bs-warning-rgb), 0.4);
  }

  &.active {
    background: var(--color-accent, #6D001A);
    color: white;
    border-color: var(--color-accent, #6D001A);
  }
}

.y-fields-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 150px;
  overflow-y: auto;
}

.y-field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.6rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 0, 0, 0.02);
  }

  &.checked {
    background: rgba(var(--bs-warning-rgb), 0.08);
    border-color: rgba(var(--bs-warning-rgb), 0.3);
  }

  input {
    accent-color: var(--color-accent, #6D001A);
  }
}

.chart-modal-preview {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  padding: 1rem;
  min-width: 0;
  min-height: 0;
}

.chart-preview-container {
  flex: 1;
  width: 100%;
  min-height: 200px;
  min-width: 0;
}

.chart-preview-empty {
  color: var(--color-secondary-text);
  font-size: 14px;
  text-align: center;
}
</style>
