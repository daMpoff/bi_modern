/**
 * Единый реестр блоков для дашбордов и пайплайнов.
 * Используется в DashboardBlocksPalette и PipelineCanvas.
 */
import { markRaw } from 'vue'
import {
  BarChart3,
  Type,
  Image,
  Video,
  Table,
  FileText,
  Database,
  Filter,
  SquareFunction,
  GitMerge,
  Code,
  LogOut
} from 'lucide-vue-next'
import { CHART_TYPES } from '@/modules/bi_analysis_modern/client/src/charts/chartTypes.js'
import DataSourceNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/DataSourceNode.vue'
import AggregationNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/AggregationNode.vue'
import FilterNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/FilterNode.vue'
import FormulaNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/FormulaNode.vue'
import JoinNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/JoinNode.vue'
import ChartNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/ChartNode.vue'
import PythonScriptNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/PythonScriptNode.vue'
import OutputNode from '@/modules/bi_analysis_modern/client/src/Graphs/nodes/OutputNode.vue'

/** Реэкспорт */
export { CHART_TYPES }

// --- Dashboard block types (палитра дашборда) ---

/** Тип блока «График» на дашборде */
export const BLOCK_TYPE_CHART = 'График'

/** Ключи компонентов контента для канваса дашборда */
export const CONTENT_KEY_CHART = 'chart'
export const CONTENT_KEY_PLACEHOLDER = 'placeholder'

/** Типы блоков для палитры дашборда (кроме Графика — он в отдельном пункте) */
export const DASHBOARD_PALETTE_TYPES = [
  { type: 'Текст', label: 'Текст', iconKey: 'Type', color: '#10b981' },
  { type: 'Фото', label: 'Фото', iconKey: 'Image', color: '#f59e0b' },
  { type: 'Видео', label: 'Видео', iconKey: 'Video', color: '#8b5cf6' },
  { type: 'Таблица', label: 'Таблица', iconKey: 'Table', color: '#ec4899' },
  { type: 'Текст + элемент', label: 'Текст + элемент', iconKey: 'FileText', color: '#6366f1' },
  { type: 'Селектор', label: 'Селектор', iconKey: 'ListFilter', color: '#0ea5e9' }
]

export const CONTENT_KEY_SELECTOR = 'selector'
export const CONTENT_KEY_TEXT = 'text'

const _contentKeyByType = {
  [BLOCK_TYPE_CHART]: CONTENT_KEY_CHART,
  'Селектор': CONTENT_KEY_SELECTOR,
  'Текст': CONTENT_KEY_TEXT
}

export function getBlockContentComponentKey(blockType) {
  return _contentKeyByType[blockType] ?? CONTENT_KEY_PLACEHOLDER
}

export function isChartBlock(blockType) {
  return blockType === BLOCK_TYPE_CHART
}

// --- Pipeline block types (узлы пайплайна) ---

export const CONTEXT_ALL = 'all'
export const CONTEXT_DASHBOARD = 'dashboard'
export const CONTEXT_GRAPHS = 'graphs'
export const CONTEXT_PIPELINE = 'pipeline'

/** Типы узлов пайплайна (Источник данных, Агрегация, Фильтр, …) */
export const PIPELINE_BLOCK_TYPES = [
  { type: 'dataSource', label: 'Источник данных', icon: Database, color: '#3b82f6', contexts: [CONTEXT_ALL] },
  { type: 'aggregation', label: 'Агрегация', icon: BarChart3, color: '#10b981', contexts: [CONTEXT_ALL] },
  { type: 'filter', label: 'Фильтр', icon: Filter, color: '#f59e0b', contexts: [CONTEXT_ALL] },
  { type: 'formula', label: 'Формула', icon: SquareFunction, color: '#8b5cf6', contexts: [CONTEXT_ALL] },
  { type: 'join', label: 'Соединение', icon: GitMerge, color: '#ec4899', contexts: [CONTEXT_ALL] },
  { type: 'pythonScript', label: 'Python Script', icon: Code, color: '#6366f1', contexts: [CONTEXT_ALL] },
  { type: 'chart', label: 'График', icon: BarChart3, color: '#06b6d4', contexts: [CONTEXT_GRAPHS] },
  { type: 'output', label: 'Выход', icon: LogOut, color: '#22c55e', contexts: [CONTEXT_ALL] }
]

const NODE_COMPONENT_MAP = {
  dataSource: DataSourceNode,
  aggregation: AggregationNode,
  filter: FilterNode,
  formula: FormulaNode,
  join: JoinNode,
  chart: ChartNode,
  pythonScript: PythonScriptNode,
  output: OutputNode
}

export function getBlockTypesForContext(context) {
  return PIPELINE_BLOCK_TYPES.filter(
    bt => bt.contexts.includes(CONTEXT_ALL) || bt.contexts.includes(context)
  )
}

export function getNodeTypesMap(context) {
  const blockTypes = getBlockTypesForContext(context)
  const map = {}
  for (const bt of blockTypes) {
    const component = NODE_COMPONENT_MAP[bt.type]
    if (component) {
      map[bt.type] = markRaw(component)
    }
  }
  return map
}

export function getBlockTypeByType(type) {
  return PIPELINE_BLOCK_TYPES.find(bt => bt.type === type) || null
}

export function getBlockLabel(type, context) {
  const bt = getBlockTypeByType(type)
  return bt?.label || type
}

export function getSingletonTypes(context) {
  if (context === CONTEXT_GRAPHS) return ['output', 'chart']
  return ['output']
}
