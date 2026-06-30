<template>
  <ModalCenter
    modal-id="dashboardBlockPipelineModal"
    standalone
    :visible="show"
    :dialog-style="{ width: '95vw', maxWidth: '1600px', height: '90vh', maxHeight: '960px' }"
    :z-index="10000"
    :scrollable="false"
    body-class="p-0"
    @close="handleClose"
  >
    <template #title>
      <component :is="blockIcon" :size="24" class="text-primary" />
      <span>Настройки: {{ block?.type }}</span>
      <div class="pipeline-modal-header-actions ms-auto">
        <button
          v-if="block?.type !== 'График' || isDashboardOnlyPipeline || loadedPipelineId"
          type="button"
          class="header-btn header-btn-execute"
          :disabled="executeLoading || !hasOutputNode"
          :title="!hasOutputNode ? 'Добавьте блок «Выход» и соедините с источником' : undefined"
          @click="handleExecute"
        >
          <Play v-if="!executeLoading" :size="16" />
          <span v-else class="spinner-border spinner-border-sm"></span>
          Выполнить
        </button>
      </div>
    </template>

    <div class="pipeline-modal-body-wrapper">
      <div class="pipeline-modal-body">
        <template v-if="block?.type === 'График' && (isDashboardOnlyPipeline || loadedPipelineId)">
          <div class="pipeline-modal-body-pipeline-wrap">
            <PipelineCanvas
              ref="pipelineRef"
              context="dashboard"
              :initial-nodes="initialPipelineNodes"
              :initial-edges="initialPipelineEdges"
              :show-execute-button="false"
              :show-clear-all="true"
              :preview-data="previewData"
              :preview-columns="previewColumns"
              :execute-loading="executeLoading"
              :on-execute="handleExecute"
              @block-config-update="onBlockConfigUpdate"
              @nodes-update="onNodesUpdate"
            />
            <div
              v-if="!isDashboardOnlyPipeline && loadedPipelineId"
              class="dashboard-pipeline-open-link"
            >
              <a :href="`/bi-modern/pipelines/${loadedPipelineId}`" class="btn btn-sm btn-outline-secondary" target="_blank" rel="noopener">
                Открыть в редакторе пайплайнов
              </a>
            </div>
          </div>
          <div
            class="panel-resize-handle"
            :class="{ resizing: isPanelResizing }"
            @mousedown="startPanelResize"
            title="Изменить ширину панели"
          ></div>
        </template>
        <PipelineCanvas
          v-else-if="block?.type !== 'График'"
          ref="pipelineRef"
          context="dashboard"
          :initial-nodes="initialPipelineNodes"
          :initial-edges="initialPipelineEdges"
          :show-execute-button="false"
          :show-clear-all="true"
          :preview-data="previewData"
          :preview-columns="previewColumns"
          :execute-loading="executeLoading"
          :on-execute="handleExecute"
          @block-config-update="onBlockConfigUpdate"
          @nodes-update="onNodesUpdate"
        />
        <div
          v-if="block?.type === 'График'"
          class="pipeline-modal-right-panel"
          :style="{ width: rightPanelWidth + 'px' }"
        >
          <div class="chart-card-fields">
            <div class="mb-2">
              <label class="form-label small mb-1">Название карточки</label>
              <input
                v-model="chartTitle"
                type="text"
                class="form-control form-control-sm"
                placeholder="Например: Продажи по регионам"
              />
            </div>
            <div class="mb-2">
              <label class="form-label small mb-1">Подзаголовок</label>
              <input
                v-model="chartSubtitle"
                type="text"
                class="form-control form-control-sm"
                placeholder="Необязательно"
              />
            </div>
          </div>
          <GraphsChartPanel
            ref="chartPanelRef"
            :chart-config="selectedChartConfig"
            :available-fields="pipelineOutputFields"
            :preview-data="previewData"
            :has-chart-node="hasOutputNode"
            @apply="handleChartPanelApply"
          />
        </div>
      </div>

      <DataPreviewTable
        :columns="previewColumns"
        :data="previewData"
        :rows-count="previewRowsCount"
        :collapsed="previewCollapsed"
        @update:collapsed="previewCollapsed = $event"
      />
    </div>

    <template #footer>
      <button
        type="button"
        class="btn btn-secondary"
        @click="handleClose"
        :disabled="isLoading"
      >Отмена</button>
      <button
        type="button"
        class="btn btn-primary"
        @click="handleSave"
        :disabled="isLoading"
      >Сохранить</button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useToast } from 'vue-toastification'
import { apiClient } from '@/js/api/manager.js'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'
import { fetchPipelineChartDetail, fetchPipelineDetail, savePipelineChart, updatePipeline } from '@/modules/bi_analysis_modern/client/src/Pipelines/js/pipelineApi.js'
import { resolveBlockChartConfig } from '@/modules/bi_analysis_modern/client/src/js/chartConfigUtils.js'
import { BarChart3, Code, Database, Play } from 'lucide-vue-next'
import ModalCenter from '@/components/ModalCenter.vue'
import DataPreviewTable from '@/modules/bi_analysis_modern/client/src/components/DataPreviewTable.vue'
import PipelineCanvas from '@/modules/bi_analysis_modern/client/src/Pipelines/components/PipelineCanvas.vue'
import GraphsChartPanel from '@/modules/bi_analysis_modern/client/src/Graphs/GraphsChartPanel.vue'

const toast = useToast()
const props = defineProps({
  show: { type: Boolean, default: false },
  block: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save', 'block-config-update'])

const pipelineRef = ref(null)
const chartPanelRef = ref(null)
const isLoading = ref(false)
const previewData = ref([])
const previewColumns = ref([])
const previewRowsCount = ref(0)
const previewCollapsed = ref(false)
const executeLoading = ref(false)

const initialPipelineNodes = ref([])
const initialPipelineEdges = ref([])
const currentPipelineNodes = ref([])
const loadedPipelineId = ref(null)
const isDashboardOnlyPipeline = ref(false)
const chartTitle = ref('')
const chartSubtitle = ref('')

const localChartConfig = ref(null)
const savedOutputFields = ref([])

const MIN_PANEL_WIDTH = 360
const MAX_PANEL_WIDTH = 800
const DEFAULT_PANEL_WIDTH = 700
const rightPanelWidth = ref(DEFAULT_PANEL_WIDTH)
const isPanelResizing = ref(false)
const panelResizeStartX = ref(0)
const panelResizeStartWidth = ref(0)

function startPanelResize(e) {
  e.preventDefault()
  e.stopPropagation()
  if (isPanelResizing.value) return
  isPanelResizing.value = true
  panelResizeStartX.value = e.clientX
  panelResizeStartWidth.value = rightPanelWidth.value
  document.addEventListener('mousemove', onPanelResize, { passive: false })
  document.addEventListener('mouseup', stopPanelResize, { once: true })
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'ew-resize'
}

function onPanelResize(e) {
  if (!isPanelResizing.value) return
  e.preventDefault()
  const deltaX = panelResizeStartX.value - e.clientX
  let newWidth = panelResizeStartWidth.value + deltaX
  newWidth = Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, newWidth))
  rightPanelWidth.value = newWidth
}

function stopPanelResize() {
  if (!isPanelResizing.value) return
  isPanelResizing.value = false
  document.removeEventListener('mousemove', onPanelResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

const pipelineOutputFields = computed(() => {
  const cols = previewColumns.value.length > 0
    ? previewColumns.value
    : savedOutputFields.value
  return cols.map((c) => ({ name: c, type: 'auto' }))
})

const hasOutputNode = computed(() => {
  const nodes = currentPipelineNodes.value
  return Array.isArray(nodes) && nodes.some((n) => n.type === 'output')
})

function onNodesUpdate(nodes) {
  currentPipelineNodes.value = Array.isArray(nodes) ? nodes : []
}

const selectedChartConfig = computed(() => localChartConfig.value ?? props.block?.config ?? null)

const blockIcon = computed(() => {
  const icons = {
    'График': BarChart3,
    'Текст': Code,
    'Фото': Database,
    'Видео': Database,
    'Таблица': Database,
    'Текст + элемент': Code
  }
  return icons[props.block?.type] || BarChart3
})

function normalizeNode(n) {
  if (n.type === 'chart') {
    return { ...n, type: 'output', data: { ...n.data, label: 'Выход', nodeType: 'output' } }
  }
  return n
}

async function loadPipeline() {
  const chartId = props.block?.config?.pipelineChartId
  if (!chartId) {
    initialPipelineNodes.value = []
    initialPipelineEdges.value = []
    loadedPipelineId.value = null
    isDashboardOnlyPipeline.value = false
    return
  }
  try {
    const chartData = await fetchPipelineChartDetail(chartId)
    const pipelineId = chartData?.pipeline
    isDashboardOnlyPipeline.value = chartData?.pipeline_is_dashboard_only ?? false
    loadedPipelineId.value = pipelineId ?? null
    if (!pipelineId) {
      initialPipelineNodes.value = []
      initialPipelineEdges.value = []
      return
    }
    const pipelineData = await fetchPipelineDetail(pipelineId)
    const graphData = pipelineData?.graph_data || {}
    initialPipelineNodes.value = (graphData.nodes || []).map(normalizeNode)
    initialPipelineEdges.value = graphData.edges || []
    const chartConfig = chartData?.chart_config || {}
    if (chartConfig && Object.keys(chartConfig).length > 0) {
      emit('block-config-update', {
        ...props.block,
        config: { ...props.block?.config, ...chartConfig }
      })
    }
  } catch (err) {
    logError('Dashboard load pipeline by chartId error:', err)
    toast.error('Ошибка загрузки пайплайна: ' + (err?.message || err))
    initialPipelineNodes.value = []
    initialPipelineEdges.value = []
    loadedPipelineId.value = null
    isDashboardOnlyPipeline.value = false
  }
}

function buildBlockConfig() {
  const blockConfig = props.block?.config || {}
  const chartCfg = localChartConfig.value || {}
  const outputFields = previewColumns.value.length > 0
    ? previewColumns.value
    : savedOutputFields.value
  const resolved = { ...resolveBlockChartConfig(blockConfig), ...chartCfg }
  const config = {
    ...blockConfig,
    chartType: resolved.chartType,
    chartConfig: { xField: resolved.xField, yFields: resolved.yFields, colorField: resolved.colorField },
    outputFields,
    title: chartTitle.value?.trim() || undefined,
    subtitle: chartSubtitle.value?.trim() || undefined
  }
  if (props.block?.type !== 'График' && pipelineRef.value) {
    config.pipeline = pipelineRef.value.getCleanGraphData()
  }
  return config
}

function onBlockConfigUpdate(chartConfig) {
  emit('block-config-update', { ...props.block, config: buildBlockConfig() })
}

function handleChartPanelApply(config) {
  localChartConfig.value = { ...(localChartConfig.value || {}), ...config }
  const base = buildBlockConfig()
  emit('block-config-update', {
    ...props.block,
    config: { ...base, ...config }
  })
}

async function handleExecute() {
  const canvas = pipelineRef.value
  if (!canvas) {
    toast.warning('Добавьте блоки на канвас (например, «Источник данных» и «Выход») и соедините их, затем нажмите «Выполнить».')
    return
  }
  const graphData = canvas.getCleanGraphData()
  const nodesList = graphData.nodes || []
  const edgesList = graphData.edges || []
  const hasOutput = nodesList.some((n) => n.type === 'output')
  if (!hasOutput) {
    toast.warning('Добавьте блок «Выход» и соедините с источником, затем нажмите «Выполнить».')
    return
  }
  if (nodesList.length === 0) {
    toast.warning('Добавьте блоки на канвас (например, «Источник данных» и «Выход») и соедините их, затем нажмите «Выполнить».')
    return
  }
  executeLoading.value = true
  try {
    const payloadNodes = nodesList.map(n => ({
      id: n.id,
      type: n.type,
      data: { config: n.type === 'output' ? {} : (n.data?.config ?? {}) }
    }))
    const payloadEdges = edgesList.map(e => ({
      source: e.source,
      target: e.target
    }))
    const { data } = await apiClient.post(biEndpoints.bi.graphExecute, {
      nodes: payloadNodes,
      edges: payloadEdges
    })
    if (data?.error) {
      toast.error(data.error)
      return
    }
    const chartData = data?.chartData || []
    const rows = Array.isArray(chartData) ? chartData : []
    const totalRows = data?.rows_count ?? rows.length
    const cols = Array.isArray(data?.columns) && data.columns.length
      ? data.columns
      : (rows.length > 0 ? Object.keys(rows[0]) : [])
    previewData.value = rows
    previewColumns.value = cols
    previewRowsCount.value = totalRows
    previewCollapsed.value = false
    if (rows.length) {
      toast.success(`Выполнено: ${totalRows.toLocaleString()} строк` + (totalRows > rows.length ? ` (показано ${rows.length.toLocaleString()})` : ''))
    }
  } catch (err) {
    logError('Dashboard pipeline execute error:', err)
    toast.error('Ошибка выполнения: ' + (err?.message || err))
    previewData.value = []
    previewColumns.value = []
    previewRowsCount.value = 0
  } finally {
    executeLoading.value = false
  }
}

async function handleSave() {
  const livePayload = chartPanelRef.value?.getCurrentPayload?.()
  if (livePayload) {
    localChartConfig.value = { ...(localChartConfig.value || {}), ...livePayload }
  }
  const builtConfig = buildBlockConfig()

  if (loadedPipelineId.value && pipelineRef.value) {
    try {
      const graphData = pipelineRef.value.getCleanGraphData()
      await updatePipeline(loadedPipelineId.value, { graph_data: graphData })
    } catch (err) {
      logError('Failed to sync Pipeline:', err)
      toast.error('Не удалось сохранить пайплайн: ' + (err?.message || err))
      return
    }
  }

  const chartId = builtConfig.pipelineChartId
  if (chartId && builtConfig.chartConfig) {
    try {
      await savePipelineChart(chartId, {
        chart_type: builtConfig.chartType || 'bar',
        chart_config: { ...builtConfig.chartConfig }
      })
    } catch (err) {
      logError('Failed to sync PipelineChart:', err)
    }
  }

  emit('save', { ...props.block, config: builtConfig })
}

function handleClose() {
  emit('close')
}

watch(() => props.show, async (isOpen) => {
  if (isOpen) {
    const cfg = props.block?.config || {}
    chartTitle.value = cfg.title ?? ''
    chartSubtitle.value = cfg.subtitle ?? ''
    const resolved = resolveBlockChartConfig(cfg)
    localChartConfig.value = {
      ...resolved,
      showLegend: cfg.showLegend,
      showLabels: cfg.showLabels
    }
    savedOutputFields.value = Array.isArray(cfg.outputFields) ? cfg.outputFields : []

    const pipelineChartId = cfg.pipelineChartId
    if (pipelineChartId) {
      try {
        const chartDetail = await fetchPipelineChartDetail(pipelineChartId)
        const fresh = resolveBlockChartConfig(chartDetail)
        localChartConfig.value = { ...localChartConfig.value, ...fresh }
      } catch (err) {
        logError('Failed to fetch fresh PipelineChart config:', err)
      }
    }

    previewData.value = []
    previewColumns.value = []
    previewRowsCount.value = 0
    previewCollapsed.value = false
    currentPipelineNodes.value = []
    rightPanelWidth.value = DEFAULT_PANEL_WIDTH
    loadPipeline()
  }
})

onBeforeUnmount(() => {
  stopPanelResize()
})
</script>

<style scoped lang="scss">
@import '@/modules/bi_analysis_modern/client/src/Pipelines/scss/pipeline-editor.scss';

.pipeline-modal-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pipeline-modal-body-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.pipeline-modal-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  min-height: 0;
  min-width: 0;
}

.pipeline-modal-body > :first-child {
  min-width: 0;
}

.pipeline-modal-body-pipeline-wrap {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-pipeline-open-link {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 5;
}

.panel-resize-handle {
  width: 8px;
  flex-shrink: 0;
  cursor: ew-resize;
  background: transparent;
  transition: background 0.15s ease;

  &:hover,
  &.resizing {
    background: rgba(0, 0, 0, 0.06);
  }
}

.pipeline-modal-right-panel {
  min-width: 360px;
  max-width: 800px;
  background: rgba(255, 255, 255, 0.98);
  border-left: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.chart-card-fields {
  padding: 0.75rem 1rem 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}
</style>
