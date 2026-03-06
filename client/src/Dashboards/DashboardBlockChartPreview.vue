<template>
  <div ref="rootRef" class="dashboard-block-chart-preview">
    <div class="chart-preview-inner">
      <!-- Skeleton placeholder when out of viewport (virtualization) -->
      <div v-if="!isVisible && !hasFetched" class="chart-skeleton">
        <div class="chart-skeleton-bar" />
        <div class="chart-skeleton-bar short" />
        <div class="chart-skeleton-area" />
      </div>
      <div v-else-if="loading" class="chart-loading">
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
      </div>
      <div v-else-if="chartError" class="chart-error">
        <span class="chart-error-text">{{ chartError }}</span>
        <button type="button" class="btn btn-sm btn-outline-primary mt-2" @click="retryFetch">
          Обновить
        </button>
      </div>
      <div v-else-if="isPipelineChart" class="chart-preview-chart">
        <PipelineChartRenderer
          ref="pipelineChartRef"
          :chart-data="pipelineChartResult.data"
          :chart-config="pipelineChartResult.chart_config"
          :chart-type="pipelineChartResult.chart_type"
          :engine="pipelineChartResult.engine"
        />
      </div>
      <div v-else-if="block?.type === 'График' && !block?.config?.pipelineChartId" class="chart-placeholder">
        Настройте график
      </div>
      <div v-else class="chart-preview-chart">
        <ChartRouter :block="block" :chart-data="chartData" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed, inject } from 'vue'
import { useToast } from 'vue-toastification'
import { apiClient } from '@/js/api/manager.js'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'
import { resolveBlockChartConfig } from '@/modules/bi_analysis_modern/client/src/js/chartConfigUtils.js'
import { fetchPipelineChartData } from '@/modules/bi_analysis_modern/client/src/Pipelines/js/pipelineApi.js'
import ChartRouter from './Charts/ChartRouter.vue'
import PipelineChartRenderer from './PipelineChartRenderer.vue'

const toast = useToast()
const pipelineChartRef = ref(null)
const rootRef = ref(null)

// ---------------------------------------------------------------------------
// Viewport-aware lazy rendering (Phase 9: Virtualization)
// ---------------------------------------------------------------------------
const isVisible = ref(false)
const hasFetched = ref(false)
let observer = null

function setupIntersectionObserver() {
  if (!rootRef.value || typeof IntersectionObserver === 'undefined') {
    isVisible.value = true // fallback: always visible
    return
  }
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        isVisible.value = entry.isIntersecting
        // First time in viewport → trigger data fetch
        if (entry.isIntersecting && !hasFetched.value) {
          fetchBlockData()
        }
      }
    },
    { rootMargin: '200px 0px', threshold: 0 } // 200px prefetch margin
  )
  observer.observe(rootRef.value)
}

function teardownObserver() {
  if (observer) {
    observer.disconnect()
    observer = null
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
function getChartDataURL() {
  return pipelineChartRef.value?.getChartDataURL?.() ?? null
}

function getChartData() {
  const data = isPipelineChart.value
    ? (pipelineChartResult.value?.data ?? [])
    : (chartData.value ?? [])
  return Array.isArray(data) ? data : []
}

defineExpose({ getChartDataURL, getChartData })

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const dashboardParams = inject('dashboardParams', ref({}))

const chartData = ref(null)
const loading = ref(false)
const chartError = ref(null)
const pipelineChartResult = ref({})

const isPipelineChart = computed(() => !!props.block?.config?.pipelineChartId)

const configDataKey = computed(() => {
  const c = props.block?.config
  if (!c) return ''
  const r = resolveBlockChartConfig(c)
  return JSON.stringify({
    pipelineChartId: c.pipelineChartId,
    chartType: r.chartType,
    xField: r.xField,
    yFields: r.yFields,
    colorField: r.colorField
  })
})

let fetchDebounceTimer = null
function scheduleFetch() {
  if (fetchDebounceTimer) clearTimeout(fetchDebounceTimer)
  fetchDebounceTimer = setTimeout(() => {
    fetchDebounceTimer = null
    fetchBlockData()
  }, 200)
}

async function fetchBlockData() {
  hasFetched.value = true

  if (isPipelineChart.value) {
    loading.value = true
    chartError.value = null
    const params = (dashboardParams && typeof dashboardParams.value === 'object') ? dashboardParams.value : {}
    try {
      const chartId = props.block.config.pipelineChartId
      pipelineChartResult.value = await fetchPipelineChartData(chartId, params)
    } catch (err) {
      pipelineChartResult.value = {}
      const message = err?.message || err?.response?.data?.detail || 'Ошибка загрузки данных графика'
      chartError.value = message
      toast.error(message)
    } finally {
      loading.value = false
    }
    return
  }
  if (!props.block?.id) {
    chartData.value = null
    chartError.value = null
    return
  }
  if (props.block?.type === 'График' && !props.block?.config?.pipelineChartId) {
    return
  }
  loading.value = true
  chartError.value = null
  const params = (dashboardParams && typeof dashboardParams.value === 'object') ? dashboardParams.value : {}
  try {
    const { data } = await apiClient.get(biEndpoints.bi.dashboardItemData(props.block.id), { params })
    const rows = (data && typeof data === 'object' && !Array.isArray(data) && Array.isArray(data.chartData))
      ? data.chartData
      : (Array.isArray(data) ? data : [])
    chartData.value = rows
  } catch (err) {
    chartData.value = null
    const message = err?.message || err?.response?.data?.detail || 'Ошибка загрузки данных'
    chartError.value = message
    toast.error(message)
  } finally {
    loading.value = false
  }
}

function retryFetch() {
  chartError.value = null
  fetchBlockData()
}

onMounted(() => {
  setupIntersectionObserver()
})

onBeforeUnmount(() => {
  teardownObserver()
  if (fetchDebounceTimer) clearTimeout(fetchDebounceTimer)
})

watch(() => props.block?.id, () => { if (isVisible.value || hasFetched.value) fetchBlockData() })
watch(configDataKey, () => { if (isVisible.value || hasFetched.value) scheduleFetch() })
watch(() => dashboardParams?.value, () => { if (isVisible.value || hasFetched.value) scheduleFetch() }, { deep: true })
</script>

<style scoped lang="scss">
.dashboard-block-chart-preview {
  width: 100%;
  height: 100%;
  min-height: 200px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.chart-preview-inner {
  flex: 1;
  min-height: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.chart-preview-chart {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chart-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 168px;
}

.chart-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 168px;
  padding: 1rem;
  text-align: center;
  color: var(--bs-danger, #dc3545);
}

.chart-error-text {
  font-size: 0.9rem;
}

.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 168px;
  color: var(--bs-secondary, #6c757d);
  font-size: 0.95rem;
}

/* Skeleton placeholder for virtualized lazy-render */
.chart-skeleton {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  min-height: 168px;
}

.chart-skeleton-bar {
  height: 14px;
  width: 60%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: 4px;

  &.short {
    width: 40%;
  }
}

.chart-skeleton-area {
  flex: 1;
  min-height: 100px;
  background: linear-gradient(90deg, #f5f5f5 25%, #ececec 50%, #f5f5f5 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
  border-radius: 8px;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
