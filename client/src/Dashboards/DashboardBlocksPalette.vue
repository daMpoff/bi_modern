<template>
  <div ref="paletteRef" class="dashboard-blocks-palette">
    <div class="palette-header">
      <h3 class="palette-title">Блоки</h3>
    </div>
    <div class="palette-content">
      <!-- Блок "График" - один пункт без выпадающего списка -->
      <div
        class="palette-item"
        draggable="true"
        @dragstart="handleChartDragStart($event)"
        @dragend="handleDragEnd"
        title="График"
      >
        <component :is="BarChart3" :size="20" class="palette-item-icon" />
        <span class="palette-item-label">График</span>
      </div>

      <!-- Остальные блоки -->
      <div
        v-for="blockType in otherBlockTypes"
        :key="blockType.type"
        class="palette-item"
        draggable="true"
        @dragstart="handleDragStart(blockType, $event)"
        @dragend="handleDragEnd"
        :title="blockType.label"
      >
        <component :is="blockType.icon" :size="20" class="palette-item-icon" />
        <span class="palette-item-label">{{ blockType.label }}</span>
      </div>
    </div>

    <!-- Сохраненные графики из пайплайнов -->
    <div class="palette-saved-section">
      <div class="palette-saved-header">
        <h3 class="palette-title">Сохраненные графики</h3>
      </div>
      <div v-if="savedChartsLoading" class="palette-saved-loading">
        <span class="spinner-border spinner-border-sm"></span>
      </div>
      <div v-else-if="savedCharts.length === 0" class="palette-saved-empty">
        Нет сохраненных графиков
      </div>
      <div v-else class="palette-saved-content">
        <input
          v-if="savedCharts.length > 5"
          type="text"
          class="palette-search-input"
          placeholder="Поиск..."
          v-model="chartSearch"
        />
        <div
          v-for="chart in filteredSavedCharts"
          :key="chart.id"
          class="palette-item palette-item-saved"
          draggable="true"
          @dragstart="handleSavedChartDragStart(chart, $event)"
          @dragend="handleDragEnd"
          :title="`${chart.name} (${chart.chart_type})`"
        >
          <component :is="BarChart3" :size="18" class="palette-item-icon palette-item-icon-saved" />
          <div class="palette-item-saved-info">
            <span class="palette-item-label">{{ chart.name }}</span>
            <span class="palette-item-sublabel">{{ chart.pipeline_name }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  BarChart3,
  Type,
  Image,
  Video,
  Table,
  FileText,
  ListFilter
} from 'lucide-vue-next'
import { BLOCK_TYPES_PALETTE } from './js/blockTypesRegistry.js'
import { fetchPipelineCharts } from '@/modules/bi_analysis_modern/client/src/Pipelines/js/pipelineApi.js'

const emit = defineEmits(['drag-start', 'drag-end'])

const iconByKey = {
  BarChart3,
  Type,
  Image,
  Video,
  Table,
  FileText,
  ListFilter
}

const otherBlockTypes = computed(() =>
  BLOCK_TYPES_PALETTE.map((bt) => ({
    ...bt,
    icon: iconByKey[bt.iconKey] || Type
  }))
)

const draggedBlockType = ref(null)

const savedCharts = ref([])
const savedChartsLoading = ref(false)
const chartSearch = ref('')

const filteredSavedCharts = computed(() => {
  const term = chartSearch.value.toLowerCase()
  if (!term) return savedCharts.value
  return savedCharts.value.filter(c =>
    c.name?.toLowerCase().includes(term) ||
    c.pipeline_name?.toLowerCase().includes(term)
  )
})

async function loadSavedCharts() {
  savedChartsLoading.value = true
  try {
    savedCharts.value = await fetchPipelineCharts()
  } catch (err) {
    logError('Failed to load saved charts:', err)
  } finally {
    savedChartsLoading.value = false
  }
}

function handleChartDragStart(event) {
  draggedBlockType.value = {
    type: 'График',
    label: 'График'
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/json', JSON.stringify({
    type: 'График',
    label: 'График'
  }))
  emit('drag-start', draggedBlockType.value, event)
}

function handleDragEnd() {
  draggedBlockType.value = null
  emit('drag-end')
}

function handleDragStart(blockType, event) {
  draggedBlockType.value = blockType
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/json', JSON.stringify({
    type: blockType.type,
    label: blockType.label
  }))
  emit('drag-start', blockType, event)
}

function handleSavedChartDragStart(chart, event) {
  const payload = {
    type: 'График',
    label: chart.name,
    pipelineChartId: chart.id,
    chartType: chart.chart_type,
    chartConfig: chart.chart_config,
    engine: chart.engine
  }
  draggedBlockType.value = payload
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/json', JSON.stringify(payload))
  emit('drag-start', payload, event)
}

onMounted(() => {
  loadSavedCharts()
})
</script>

<style scoped lang="scss">
.dashboard-blocks-palette {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 255, 255, 0.92) 100%);
  border-right: 1px solid rgba(0, 0, 0, 0.08);
}

.palette-header {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.palette-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--color-primary-text);
}

.palette-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  cursor: grab;
  transition: all 0.2s ease;
  user-select: none;
  position: relative;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
    border-color: var(--color-accent, #6D001A);
    transform: translateX(4px);
  }

  &:active {
    cursor: grabbing;
  }
}

.palette-item-icon {
  color: var(--color-secondary-text);
  flex-shrink: 0;
}

.palette-item-label {
  font-size: 14px;
  color: var(--color-primary-text);
  font-weight: 500;
  flex: 1;
}

.palette-saved-section {
  border-top: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  max-height: 50%;
}

.palette-saved-header {
  padding: 0.75rem 1rem 0.5rem;
}

.palette-saved-loading,
.palette-saved-empty {
  padding: 1rem;
  text-align: center;
  font-size: 12px;
  color: var(--color-secondary-text);
}

.palette-saved-content {
  overflow-y: auto;
  padding: 0 0.75rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.palette-search-input {
  width: 100%;
  padding: 0.4rem 0.6rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 0.4rem;
  &:focus {
    border-color: rgba(var(--bs-warning-rgb), 0.4);
    outline: none;
  }
}

.palette-item-saved {
  padding: 0.5rem 0.75rem;
  flex-direction: row;
}

.palette-item-icon-saved {
  color: rgb(var(--bs-info-rgb));
}

.palette-item-saved-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.palette-item-sublabel {
  font-size: 11px;
  color: var(--color-secondary-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
