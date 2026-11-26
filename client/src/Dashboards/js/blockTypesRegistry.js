/**
 * Реестр типов блоков дашборда.
 * Импортирует из единого реестра blocksRegistry.js.
 */
export {
  CHART_TYPES,
  BLOCK_TYPE_CHART,
  CONTENT_KEY_CHART,
  CONTENT_KEY_PLACEHOLDER,
  CONTENT_KEY_SELECTOR,
  CONTENT_KEY_TEXT,
  getBlockContentComponentKey,
  isChartBlock
} from '@/modules/bi_analysis_modern/client/src/Graphs/blocksRegistry.js'

import { BarChart3, Type, Image, Video, Table, FileText, ListFilter } from 'lucide-vue-next'
import { DASHBOARD_PALETTE_TYPES } from '@/modules/bi_analysis_modern/client/src/Graphs/blocksRegistry.js'

/** Типы блоков для палитры (кроме Графика — у него выпадающий список подтипов). */
export const BLOCK_TYPES_PALETTE = DASHBOARD_PALETTE_TYPES

/** Иконки по типу блока дашборда (общий реестр для DashboardBlock и DashboardBlockAbsolute). */
export const DASHBOARD_BLOCK_ICONS = {
  'График': BarChart3,
  'Текст': Type,
  'Фото': Image,
  'Видео': Video,
  'Таблица': Table,
  'Текст + элемент': FileText,
  'Селектор': ListFilter
}
