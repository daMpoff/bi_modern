<script setup>
import { ref, computed, onMounted, nextTick, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from '@/js/utils/toast.js'
import {
  ArrowLeft, Save, Play, Plus, BarChart3,
  Pencil, Trash2, AlertTriangle, GitBranch,
  FileText, Filter, Sigma, Combine, Calculator, Code2, FileOutput
} from 'lucide-vue-next'
import { confirmDelete } from '@/js/utils/confirm.js'
import DataPreviewTable from '@/modules/bi_analysis_modern/client/src/components/DataPreviewTable.vue'
import PipelineCanvas from '@/modules/bi_analysis_modern/client/src/Pipelines/components/PipelineCanvas.vue'
import PipelineChartModal from './PipelineChartModal.vue'
import {
  updatePipeline, executePipeline, getExecuteChunk, fetchPipelineCharts,
  createPipelineChart, savePipelineChart, deletePipelineChart
} from '../js/pipelineApi.js'
import { apiClient } from '@/js/api/manager.js'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'

const lineageNodeIcons = {
  dataSource: FileText,
  filter: Filter,
  aggregation: Sigma,
  join: Combine,
  formula: Calculator,
  pythonScript: Code2,
  chart: BarChart3,
  output: FileOutput
}

const route = useRoute()
const router = useRouter()
const toast = useToast()

const pipelineId = computed(() => route.params.id ? Number(route.params.id) : null)
const pipelineName = ref('')
const pipelineDescription = ref('')
const pipelineIsDashboardOnly = ref(false)
const isEditingName = ref(false)
const pipelineRef = ref(null)

const initialNodes = ref([])
const initialEdges = ref([])
const paramsSchema = ref([])
const paramValues = ref({})

const previewData = ref([])
const previewColumns = ref([])
const previewCollapsed = ref(false)
const previewRowsCount = ref(0)
const resultSetId = ref(null)
const CHUNK_SIZE = parseInt(import.meta.env.VITE_BI_EXECUTE_CHUNK_SIZE || '5000', 10) || 5000
const previewChunks = ref({})
const loadingChunkIndexes = ref(new Set())

const charts = ref([])
const executeLoading = ref(false)
const lastRequestTimeMs = ref(null)
const saveLoading = ref(false)

const showChartModal = ref(false)
const editingChart = ref(null)
const pipelineOutputFields = ref([])

const lineageNodes = ref([])
const lineageError = ref(null)
const lineageLoading = ref(false)
const lineageCollapsed = ref(true)

provide('pipelinePreviewData', previewData)
provide('pipelinePreviewColumns', previewColumns)

const showParamsEditor = ref(false)
const newParamName = ref('')
const newParamLabel = ref('')
const newParamType = ref('string')
const newParamDefault = ref('')

function addParam() {
  let name = (newParamName.value || '').trim().replace(/^\$+/, '')
  if (!name) return
  if (paramsSchema.value.some(p => p.name === name)) {
    toast.warning('Параметр с таким именем уже есть')
    return
  }
  const param = {
    name,
    label: (newParamLabel.value || '').trim() || name,
    type: newParamType.value || 'string',
    default_value: newParamDefault.value
  }
  paramsSchema.value = [...paramsSchema.value, param]
  paramValues.value = { ...paramValues.value, [name]: param.default_value ?? '' }
  newParamName.value = ''
  newParamLabel.value = ''
  newParamDefault.value = ''
  showParamsEditor.value = false
}

function removeParam(name) {
  paramsSchema.value = paramsSchema.value.filter(p => p.name !== name)
  const next = { ...paramValues.value }
  delete next[name]
  paramValues.value = next
}

async function loadPipeline() {
  if (!pipelineId.value) return
  try {
    const { data } = await apiClient.get(biEndpoints.bi.pipelineDetail(pipelineId.value))
    pipelineName.value = data.name || ''
    pipelineDescription.value = data.description || ''
    pipelineIsDashboardOnly.value = data.is_dashboard_only === true
    const graphData = data.graph_data || {}
    initialNodes.value = graphData.nodes || []
    initialEdges.value = graphData.edges || []
    paramsSchema.value = Array.isArray(data.params_schema) ? data.params_schema : []
    paramValues.value = (paramsSchema.value || []).reduce((acc, p) => {
      acc[p.name] = p.default_value !== undefined && p.default_value !== null ? p.default_value : ''
      return acc
    }, {})
    if (initialNodes.value.length > 0) {
      loadLineage()
    } else {
      lineageNodes.value = []
      lineageError.value = null
    }
  } catch (err) {
    toast.error('Ошибка загрузки пайплайна')
    logError(err)
  }
}

async function loadLineage(loadCounts = false) {
  if (!pipelineId.value) return
  lineageLoading.value = true
  lineageError.value = null
  try {
    let url = biEndpoints.bi.pipelineLineage(pipelineId.value)
    if (loadCounts) {
      const q = new URLSearchParams()
      q.set('include_counts', '1')
      Object.entries(paramValues.value || {}).forEach(([k, v]) => {
        if (v !== undefined && v !== null) q.set(`params[${k}]`, String(v))
      })
      url += (url.includes('?') ? '&' : '?') + q.toString()
    }
    const { data } = await apiClient.get(url)
    if (data.error && !data.nodes?.length) {
      lineageError.value = data.error
      lineageNodes.value = []
    } else {
      lineageNodes.value = data.nodes || []
      lineageError.value = data.error || null
    }
  } catch (err) {
    lineageError.value = 'Не удалось загрузить линию данных'
    lineageNodes.value = []
  } finally {
    lineageLoading.value = false
  }
}

async function loadCharts() {
  if (!pipelineId.value) return
  try {
    charts.value = await fetchPipelineCharts(pipelineId.value)
  } catch (err) {
    logError('Charts load error:', err)
  }
}

function getCleanGraphData() {
  return pipelineRef.value?.getCleanGraphData() || { nodes: [], edges: [] }
}

async function handleSave() {
  if (!pipelineId.value) return
  saveLoading.value = true
  try {
    await updatePipeline(pipelineId.value, {
      name: pipelineName.value,
      description: pipelineDescription.value,
      graph_data: getCleanGraphData(),
      params_schema: paramsSchema.value
    })
    toast.success('Пайплайн сохранен')
    loadLineage()
  } catch (err) {
    toast.error('Ошибка сохранения: ' + (err.message || err))
  } finally {
    saveLoading.value = false
  }
}

async function loadChunk(chunkIndex) {
  if (!resultSetId.value || !pipelineId.value || loadingChunkIndexes.value.has(chunkIndex)) return
  if (previewChunks.value[chunkIndex]) return // already loaded
  const offset = chunkIndex * CHUNK_SIZE
  loadingChunkIndexes.value.add(chunkIndex)
  try {
    const rows = await getExecuteChunk(pipelineId.value, resultSetId.value, offset, CHUNK_SIZE)
    previewChunks.value = { ...previewChunks.value, [chunkIndex]: rows }
  } catch (err) {
    toast.error('Ошибка загрузки блока данных: ' + (err.message || err))
  } finally {
    loadingChunkIndexes.value.delete(chunkIndex)
    loadingChunkIndexes.value = new Set(loadingChunkIndexes.value)
  }
}

async function handleExecute() {
  if (!pipelineId.value) {
    toast.warning('Сначала сохраните пайплайн, затем нажмите «Выполнить».')
    return
  }
  executeLoading.value = true
  resultSetId.value = null
  previewChunks.value = {}
  try {
    await handleSave()
    const t0 = performance.now()
    const result = await executePipeline(pipelineId.value, paramValues.value)
    lastRequestTimeMs.value = Math.round(performance.now() - t0)
    const data = Array.isArray(result?.data) ? result.data : (result?.data || [])
    if (result?.error) {
      toast.error(result.error)
      return
    }
    const total = (typeof result?.rows_count === 'number' ? result.rows_count : null) ?? data.length
    const cols = Array.isArray(result?.columns) && result.columns.length ? result.columns : (data.length > 0 ? Object.keys(data[0]) : [])
    previewData.value = data
    previewColumns.value = cols
    previewRowsCount.value = total
    pipelineOutputFields.value = previewColumns.value.map(c => ({ name: c, type: 'auto' }))
    previewCollapsed.value = false
    if (result?.result_set_id && total > data.length) {
      resultSetId.value = result.result_set_id
      previewChunks.value = { 0: data }
    }
    toast.success(`Выполнено: ${previewRowsCount.value} строк`)
    nextTick(() => { loadLineage(true) })
  } catch (err) {
    toast.error('Ошибка выполнения: ' + (err.message || err))
  } finally {
    executeLoading.value = false
  }
}

function openAddChart() {
  if (!previewColumns.value.length) {
    toast.warning('Сначала выполните пайплайн для получения данных')
    return
  }
  editingChart.value = null
  showChartModal.value = true
}

function openEditChart(chart) {
  editingChart.value = chart
  showChartModal.value = true
}

function closeChartModal() {
  showChartModal.value = false
  editingChart.value = null
}

async function handleSaveChart(chartData) {
  try {
    if (editingChart.value?.id) {
      await savePipelineChart(editingChart.value.id, {
        ...chartData, pipeline: pipelineId.value
      })
      toast.success('График обновлен')
    } else {
      await createPipelineChart({
        ...chartData, pipeline: pipelineId.value
      })
      toast.success('График создан')
    }
    await loadCharts()
    closeChartModal()
  } catch (err) {
    toast.error('Ошибка сохранения графика: ' + (err.message || err))
  }
}

async function askDeleteChart(chart) {
  const chartName = chart.name || chart.title || 'без названия'
  const ok = await confirmDelete(
    'Удаление графика',
    `Удалить график «${chartName}»?`,
  )
  if (!ok) return
  try {
    await deletePipelineChart(chart.id)
    toast.success('График удален')
    await loadCharts()
  } catch {
    toast.error('Ошибка удаления')
  }
}

onMounted(() => {
  loadPipeline()
  loadCharts()
})
</script>

<template>
  <div class="pipeline-editor-page">
    <div class="editor-header">
      <button class="header-back-btn" @click="router.push('/bi-modern/pipelines/')" title="К списку">
        <ArrowLeft :size="18" />
      </button>
      <div class="header-title-group">
        <div class="header-title-wrap">
          <input
            v-if="isEditingName"
            class="header-title-input"
            v-model="pipelineName"
            @blur="isEditingName = false"
            @keyup.enter="isEditingName = false"
            autofocus
          />
          <h2 v-else class="header-title" @dblclick="isEditingName = true">
            {{ pipelineName || 'Новый пайплайн' }}
          </h2>
          <div v-if="pipelineIsDashboardOnly" class="header-warning-dashboard-only">
            <AlertTriangle :size="14" class="header-warning-icon" />
            <span>Пайплайн привязан к одному графику</span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <button class="header-btn header-btn-execute" :disabled="executeLoading" @click="handleExecute">
          <Play v-if="!executeLoading" :size="16" />
          <span v-else class="spinner-border spinner-border-sm"></span>
          Выполнить
        </button>
        <button class="header-btn header-btn-primary" :disabled="saveLoading" @click="handleSave">
          <Save :size="16" />
          Сохранить
        </button>
      </div>
    </div>

    <div class="params-section">
      <div v-if="paramsSchema.length > 0" class="params-bar">
        <span class="params-bar-label">Параметры запуска:</span>
        <template v-for="p in paramsSchema" :key="p.name">
          <label class="params-bar-item">
            <span class="params-bar-item-label">{{ p.label || p.name }}</span>
            <input
              v-model="paramValues[p.name]"
              type="text"
              class="params-bar-input"
              :placeholder="String(p.default_value ?? '')"
            />
          </label>
        </template>
      </div>
      <div class="params-schema-edit">
        <button
          type="button"
          class="params-schema-btn"
          @click="showParamsEditor = !showParamsEditor"
        >
          {{ showParamsEditor ? 'Скрыть настройку параметров' : 'Настроить параметры пайплайна' }}
        </button>
        <div v-if="showParamsEditor" class="params-schema-form">
          <div class="params-schema-list">
            <div
              v-for="p in paramsSchema"
              :key="p.name"
              class="params-schema-row"
            >
              <span class="params-schema-name">{{ p.name }}</span>
              <span class="params-schema-meta">({{ p.type }}, по умолчанию: {{ p.default_value ?? '—' }})</span>
              <button type="button" class="params-schema-remove" @click="removeParam(p.name)" title="Удалить">×</button>
            </div>
          </div>
          <div class="params-schema-add">
            <input v-model="newParamName" type="text" placeholder="Имя (например year)" class="params-schema-input" />
            <input v-model="newParamLabel" type="text" placeholder="Подпись" class="params-schema-input" />
            <select v-model="newParamType" class="params-schema-select">
              <option value="string">Строка</option>
              <option value="number">Число</option>
            </select>
            <input v-model="newParamDefault" type="text" placeholder="Значение по умолчанию" class="params-schema-input" />
            <button type="button" class="params-schema-add-btn" @click="addParam">Добавить</button>
          </div>
          <p class="params-schema-hint">В фильтрах укажите значение <code>$имя_параметра</code>, в формулах — <code>$имя_параметра</code>.</p>
        </div>
      </div>
    </div>

    <div class="editor-body">
      <PipelineCanvas
        ref="pipelineRef"
        context="pipeline"
        :initial-nodes="initialNodes"
        :initial-edges="initialEdges"
        :show-clear-all="true"
        :show-minimap="true"
        :execute-loading="executeLoading"
        :on-execute="handleExecute"
      />

      <div class="editor-right-panel">
        <div class="lineage-section">
          <button
            type="button"
            class="lineage-section-toggle"
            :class="{ 'lineage-section-toggle--expanded': !lineageCollapsed }"
            @click="lineageCollapsed = !lineageCollapsed"
            :aria-expanded="!lineageCollapsed"
          >
            <span class="lineage-section-icon-wrap">
              <GitBranch :size="16" class="lineage-section-icon" />
            </span>
            <span class="lineage-section-title">Линия данных</span>
          </button>
          <div v-show="!lineageCollapsed" class="lineage-section-content">
            <div v-if="lineageLoading" class="lineage-loading">Загрузка…</div>
            <div v-else-if="lineageNodes.length === 0" class="lineage-empty">Добавьте узлы и сохраните пайплайн</div>
            <template v-else>
              <div v-if="lineageError" class="lineage-error lineage-error-inline">{{ lineageError }}</div>
              <div class="lineage-flow">
                <template v-for="(node, idx) in lineageNodes" :key="node.id">
                  <div class="lineage-node-card">
                    <component :is="lineageNodeIcons[node.type] || FileText" :size="14" class="lineage-node-card-icon" />
                    <span>{{ node.label }}</span>
                  </div>
                  <div v-if="idx < lineageNodes.length - 1" class="lineage-arrow-block">
                    <span class="lineage-arrow-count">{{ node.rows_count != null && node.rows_count >= 0 ? node.rows_count.toLocaleString() : '—' }}</span>
                    <span class="lineage-arrow-connector" aria-hidden="true"></span>
                    <span class="lineage-arrow-head" aria-hidden="true"></span>
                  </div>
                </template>
              </div>
            </template>
          </div>
        </div>
        <div class="right-panel-header">
          <h3 class="right-panel-title">Графики</h3>
          <button
            v-if="!pipelineIsDashboardOnly"
            class="right-panel-add-btn"
            @click="openAddChart"
            :disabled="!previewColumns.length"
            :title="!previewColumns.length ? 'Сначала выполните пайплайн' : 'Добавить график'"
          >
            <Plus :size="14" />
            Добавить
          </button>
        </div>
        <div v-if="pipelineIsDashboardOnly" class="right-panel-warning-dashboard-only">
          <AlertTriangle :size="14" class="right-panel-warning-icon" />
          <span>К этому пайплайну привязан один график; добавление других недоступно.</span>
        </div>
        <div class="right-panel-content">
          <div v-if="charts.length === 0" class="right-panel-empty">
            <BarChart3 :size="32" style="opacity: 0.4; margin-bottom: 0.5rem" />
            Выполните пайплайн и создайте графики из полученных данных
          </div>
          <div
            v-for="chart in charts"
            :key="chart.id"
            class="chart-card"
            @click="openEditChart(chart)"
          >
            <div class="chart-card-icon">
              <BarChart3 :size="18" />
            </div>
            <div class="chart-card-info">
              <p class="chart-card-name">{{ chart.name }}</p>
              <p class="chart-card-type">{{ chart.chart_type }}</p>
            </div>
            <div class="chart-card-actions">
              <button class="chart-card-action-btn" @click.stop="openEditChart(chart)" title="Редактировать">
                <Pencil :size="14" />
              </button>
              <button class="chart-card-action-btn danger" @click.stop="askDeleteChart(chart)" title="Удалить">
                <Trash2 :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <DataPreviewTable
      :columns="previewColumns"
      :data="previewData"
      :rows-count="previewRowsCount"
      :request-time-ms="lastRequestTimeMs"
      :collapsed="previewCollapsed"
      :result-set-id="resultSetId"
      :chunk-size="CHUNK_SIZE"
      :chunks="previewChunks"
      :loading-chunk-indexes="loadingChunkIndexes"
      :pipeline-id="pipelineId"
      :load-chunk="loadChunk"
      @update:collapsed="previewCollapsed = $event"
    />

    <PipelineChartModal
      :show="showChartModal"
      :chart="editingChart"
      :available-fields="pipelineOutputFields"
      :preview-data="previewData"
      @close="closeChartModal"
      @save="handleSaveChart"
    />
  </div>
</template>

<style scoped lang="scss">
@import '../scss/pipeline-editor.scss';
</style>
