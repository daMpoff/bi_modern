<template>
  <div class="dashboard-block-selector">
    <template v-if="!isConfigured">
      <div class="selector-placeholder">
        <span class="selector-placeholder-text">Настроить селектор</span>
      </div>
    </template>
    <template v-else>
      <div v-if="optionsError" class="selector-error">
        {{ optionsError }}
      </div>
      <div v-else class="selector-control">
        <label v-if="displayLabel" class="selector-label">{{ displayLabel }}</label>
        <select
          :value="currentValue"
          class="form-select form-select-sm selector-select"
          :disabled="loading"
          @change="onSelectChange"
        >
          <option value="">— Все —</option>
          <option
            v-for="opt in options"
            :key="String(opt.value)"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, inject } from 'vue'
import { fetchPipelineFieldValues } from '@/modules/bi_analysis_modern/client/src/Pipelines/js/pipelineApi.js'

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const dashboardParams = inject('dashboardParams', ref({}))
const updateDashboardParams = inject('updateDashboardParams', () => {})

const pipelineId = computed(() => props.block?.config?.pipelineId ?? null)
const fieldName = computed(() => props.block?.config?.fieldName ?? '')
const paramName = computed(() => (props.block?.config?.paramName ?? fieldName.value) || '')
const displayLabel = computed(() => props.block?.config?.label ?? paramName.value)

const isConfigured = computed(() => pipelineId.value && fieldName.value)

const options = ref([])
const optionsError = ref(null)
const loading = ref(false)

const currentValue = computed(() => {
  const name = paramName.value
  if (!name) return ''
  const v = dashboardParams?.value?.[name]
  return v === undefined || v === null ? '' : String(v)
})

async function loadOptions() {
  if (!pipelineId.value || !fieldName.value) {
    options.value = []
    optionsError.value = null
    return
  }
  loading.value = true
  optionsError.value = null
  try {
    const allParams = (dashboardParams && typeof dashboardParams.value === 'object') ? dashboardParams.value : {}
    const name = paramName.value
    const paramsForOptions = name ? { ...allParams } : allParams
    if (name && name in paramsForOptions) delete paramsForOptions[name]
    const { values, error } = await fetchPipelineFieldValues(
      pipelineId.value,
      fieldName.value,
      paramsForOptions,
      200
    )
    if (error) {
      optionsError.value = error
      options.value = []
    } else {
      options.value = (values || []).map((v) => ({
        value: v === null || v === undefined ? '' : String(v),
        label: String(v === null || v === undefined ? '' : v)
      }))
    }
  } catch (e) {
    optionsError.value = e?.message || 'Ошибка загрузки вариантов'
    options.value = []
  } finally {
    loading.value = false
  }
}

function onSelectChange(e) {
  const name = paramName.value
  if (!name) return
  const val = e.target.value
  updateDashboardParams({ [name]: val || undefined })
}

onMounted(() => loadOptions())
watch([pipelineId, fieldName], () => loadOptions())
watch(() => dashboardParams?.value, () => loadOptions(), { deep: true })
</script>

<style scoped lang="scss">
.dashboard-block-selector {
  width: 100%;
  height: 100%;
  min-height: 60px;
  display: flex;
  align-items: center;
  padding: 0.5rem;
}

.selector-placeholder {
  width: 100%;
  text-align: center;
  color: var(--bs-secondary, #6c757d);
  font-size: 0.9rem;
}

.selector-placeholder-text {
  display: inline-block;
}

.selector-error {
  color: var(--bs-danger, #dc3545);
  font-size: 0.85rem;
}

.selector-control {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.selector-label {
  font-size: 0.8rem;
  font-weight: 500;
  margin: 0;
}

.selector-select {
  max-width: 100%;
}
</style>
