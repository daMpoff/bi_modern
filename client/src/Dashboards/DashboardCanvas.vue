<template>
  <div
    ref="canvasRef"
    class="dashboard-canvas"
    :class="{
      'dashboard-canvas--grid': placementMode === 'grid',
      'dashboard-canvas--absolute': placementMode === 'absolute'
    }"
    @drop="handleDrop"
    @dragover.prevent="handleDragOver"
    @dragenter.prevent="handleDragEnter"
    @dragleave="handleDragLeave"
    @click="handleCanvasClick"
  >
    <!-- Grid режим -->
    <div
      v-if="placementMode === 'grid'"
      class="dashboard-canvas-grid-wrapper"
    >
      <!-- Визуальная сетка (только в режиме редактирования) -->
      <div
        v-if="mode === 'edit'"
        class="grid-background"
        :style="gridBackgroundStyle"
      >
        <div
          v-for="row in gridRows"
          :key="`row-${row}`"
          class="grid-row"
          :style="{ display: 'grid', gridTemplateColumns: `repeat(${gridSize}, ${gridCellWidth}px)`, gap: '0.5rem' }"
        >
          <div
            v-for="col in gridSize"
            :key="`cell-${row}-${col}`"
            class="grid-cell"
            :class="{
              'grid-cell--highlighted': getCellDragState(row, col) === 'valid',
              'grid-cell--invalid': getCellDragState(row, col) === 'invalid'
            }"
            :style="{ width: `${gridCellWidth}px`, height: `${gridCellHeight}px` }"
          ></div>
        </div>
      </div>

      <!-- Ghost элемент для grid-перемещения -->
      <div
        v-if="moving && ghostStyle"
        class="grid-drag-ghost"
        :class="{ 'grid-drag-ghost--invalid': !moving.valid }"
        :style="ghostStyle"
      />

      <!-- Блоки на сетке -->
      <div
        class="dashboard-canvas-grid"
        :style="gridStyle"
      >
        <DashboardBlock
          v-for="block in blocks"
          :key="block.id || block._uid || `block-${block.type}`"
          :block="block"
          :placement-mode="placementMode"
          :mode="mode"
          :is-selected="selectedBlockId === block.id"
          :is-ghosted="moving?.blockId === block.id"
          :grid-size="gridSize"
          :grid-cell-width="gridCellWidth"
          :grid-cell-height="gridCellHeight"
          @click="(e) => handleBlockClick(block, e)"
          @settings="handleBlockSettings"
          @delete="handleBlockDelete"
          @resize="handleBlockResize"
          @resize-end="handleResizeEnd"
          @move="handleBlockMove"
          @grid-move-start="startGridMove"
          @focus-mode="(block) => emit('focus-mode', block)"
        >
          <template #header-actions-start v-if="getBlockContentComponentKey(block.type) === CONTENT_KEY_CHART">
            <ChartExportDropdown
              :export-api="getChartExportApi(block)"
              :chart-title="block.config?.title || block.type || 'График'"
              compact
            />
          </template>
          <template #default>
            <component
              :is="blockContentComponentByKey[getBlockContentComponentKey(block.type)]"
              :ref="(el) => setBlockContentRef(block, el)"
              :block="block"
            />
          </template>
        </DashboardBlock>
      </div>
    </div>

    <!-- Absolute режим: ghost как в сетке, коммит по mouseup -->
    <div
      v-else-if="placementMode === 'absolute'"
      class="dashboard-canvas-absolute"
      :style="absoluteStyle"
    >
      <!-- Ghost при перетаскивании в absolute -->
      <div
        v-if="movingAbsolute && ghostStyleAbsolute"
        class="absolute-drag-ghost"
        :style="ghostStyleAbsolute"
      />
      <DashboardBlockAbsolute
        v-for="block in blocks"
        :key="block.id || block._uid || `block-${block.type}`"
        :block="block"
        :mode="mode"
        :is-selected="selectedBlockId === block.id"
        :is-ghosted="movingAbsolute?.blockId === block.id"
        @click="(e) => handleBlockClick(block, e)"
        @settings="handleBlockSettings"
        @delete="handleBlockDelete"
        @resize="handleBlockResize"
        @resize-end="handleResizeEnd"
        @absolute-move-start="startAbsoluteMove"
        @focus-mode="(block) => emit('focus-mode', block)"
      >
        <template #header-actions-start v-if="getBlockContentComponentKey(block.type) === CONTENT_KEY_CHART">
          <ChartExportDropdown
            :export-api="getChartExportApi(block)"
            :chart-title="block.config?.title || block.type || 'График'"
            compact
          />
        </template>
        <template #default>
          <component
            :is="blockContentComponentByKey[getBlockContentComponentKey(block.type)]"
            :ref="(el) => setBlockContentRef(block, el)"
            :block="block"
          />
        </template>
      </DashboardBlockAbsolute>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import DashboardBlock from './DashboardBlock.vue'
import DashboardBlockAbsolute from './DashboardBlockAbsolute.vue'
import DashboardBlockChartPreview from './DashboardBlockChartPreview.vue'
import DashboardBlockSelector from './DashboardBlockSelector.vue'
import DashboardBlockText from './DashboardBlockText.vue'
import BlockContentPlaceholder from './BlockContentPlaceholder.vue'
import ChartExportDropdown from './ChartExportDropdown.vue'
import { getBlockContentComponentKey, CONTENT_KEY_CHART, CONTENT_KEY_PLACEHOLDER, CONTENT_KEY_SELECTOR, CONTENT_KEY_TEXT } from './js/blockTypesRegistry.js'

const props = defineProps({
  blocks: {
    type: Array,
    default: () => []
  },
  placementMode: {
    type: String,
    required: true,
    validator: (value) => ['grid', 'absolute'].includes(value)
  },
  mode: {
    type: String,
    default: 'edit',
    validator: (value) => ['edit', 'view'].includes(value)
  },
  selectedBlockId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['block-add', 'block-update', 'block-update-local', 'block-delete', 'block-click', 'block-settings', 'canvas-click', 'focus-mode'])

/** Реестр компонентов контента по ключу (из blockTypesRegistry). Добавление нового типа блока: зарегистрировать ключ в реестре и добавить сюда компонент. */
const blockContentComponentByKey = {
  [CONTENT_KEY_CHART]: DashboardBlockChartPreview,
  [CONTENT_KEY_SELECTOR]: DashboardBlockSelector,
  [CONTENT_KEY_TEXT]: DashboardBlockText,
  [CONTENT_KEY_PLACEHOLDER]: BlockContentPlaceholder
}

const chartPreviewRefs = ref({})

function blockKey(block) {
  return block.id ?? block._uid ?? `block-${block.type}`
}

function getChartExportApi(block) {
  const key = blockKey(block)
  return {
    getChartDataURL: () => chartPreviewRefs.value[key]?.getChartDataURL?.() ?? null,
    getChartData: () => chartPreviewRefs.value[key]?.getChartData?.() ?? []
  }
}

function setBlockContentRef(block, el) {
  const key = blockKey(block)
  if (getBlockContentComponentKey(block.type) === CONTENT_KEY_CHART) {
    if (el) chartPreviewRefs.value[key] = el
    else delete chartPreviewRefs.value[key]
  }
}

const canvasRef = ref(null)
const gridSize = ref(12) // Bootstrap grid: 12 колонок
const gridCellWidth = ref(0)
const gridCellHeight = ref(50) // Высота ячейки сетки
const gridRows = ref(12) // Начальное количество строк

// Константа для gap между ячейками
const GRID_GAP = 8 // 0.5rem = 8px

// Состояние для подсветки ячеек при перетаскивании
const isDraggingOver = ref(false)
const dragOverPosition = ref({ row: null, col: null, cols: 4, rows: 3, valid: true })

// Состояние для перемещения блока в grid режиме
const isBlockMoving = ref(false)
const moving = ref(null)

// Состояние для перемещения блока в absolute режиме (ghost + коммит по mouseup)
const movingAbsolute = ref(null)

// Стили для grid режима
const gridStyle = computed(() => {
  return {
    display: 'grid',
    gridTemplateColumns: `repeat(${gridSize.value}, ${gridCellWidth.value}px)`,
    gridAutoRows: `${gridCellHeight.value}px`,
    gap: '0.5rem',
    width: '100%',
    position: 'relative',
    zIndex: 1
  }
})

// Стили для фоновой сетки
const gridBackgroundStyle = computed(() => {
  const totalWidth = gridCellWidth.value * gridSize.value + (gridSize.value - 1) * 8 // gap между колонками
  const totalHeight = gridCellHeight.value * gridRows.value + (gridRows.value - 1) * 8 // gap между строками
  
  return {
    width: `${totalWidth}px`,
    height: `${totalHeight}px`,
    minHeight: `${totalHeight}px`
  }
})

// Стили для absolute режима
const absoluteStyle = computed(() => {
  return {
    position: 'relative',
    width: '100%',
    minHeight: '100%'
  }
})

// Стили для ghost элемента при grid-перемещении
const ghostStyle = computed(() => {
  if (!moving.value) return null
  const cellW = gridCellWidth.value + GRID_GAP
  const cellH = gridCellHeight.value + GRID_GAP

  const left = (moving.value.startCol - 1) * cellW
  const top = (moving.value.startRow - 1) * cellH

  const width = moving.value.cols * gridCellWidth.value + (moving.value.cols - 1) * GRID_GAP
  const height = moving.value.rows * gridCellHeight.value + (moving.value.rows - 1) * GRID_GAP

  return {
    position: 'absolute',
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`
  }
})

// Стили для ghost при перетаскивании в absolute (как в сетке — только позиция в px)
const ghostStyleAbsolute = computed(() => {
  if (!movingAbsolute.value) return null
  const m = movingAbsolute.value
  return {
    position: 'absolute',
    left: `${Math.max(0, m.left)}px`,
    top: `${Math.max(0, m.top)}px`,
    width: `${m.width}px`,
    height: `${m.height}px`
  }
})

// Обработка drop
function handleDrop(event) {
  if (props.mode !== 'edit') return
  event.preventDefault()
  event.stopPropagation()

  // Сбрасываем подсветку
  isDraggingOver.value = false
  dragOverPosition.value = { row: null, col: null, cols: 4, rows: 3, valid: true }

  try {
    const data = JSON.parse(event.dataTransfer.getData('application/json'))
    if (!data || !data.type) return

    const rect = canvasRef.value?.getBoundingClientRect()
    if (!rect) return

    // Учитываем прокрутку канваса для правильного вычисления координат
    const scrollLeft = canvasRef.value?.scrollLeft || 0
    const scrollTop = canvasRef.value?.scrollTop || 0

    // Вычисляем координаты относительно канваса с учетом прокрутки
    // Используем Math.max чтобы гарантировать неотрицательные координаты
    let x = Math.max(0, event.clientX - rect.left + scrollLeft)
    let y = Math.max(0, event.clientY - rect.top + scrollTop)

    // В режиме grid вычисляем позицию в колонках
    let blockWidth = 200
    let blockHeight = 150
    
    if (props.placementMode === 'grid') {
      // Вычисляем колонку и строку под указателем мыши
      const colIndex = Math.max(0, Math.floor(x / (gridCellWidth.value + GRID_GAP)))
      const rowIndex = Math.max(0, Math.floor(y / (gridCellHeight.value + GRID_GAP)))

      // Размер по умолчанию: 4 колонки, 3 строки
      const defaultCols = 4
      const defaultRows = 3

      // Изначально пробуем разместить блок прямо под указателем мыши
      const target = {
        startCol: colIndex + 1,
        startRow: rowIndex + 1,
        cols: defaultCols,
        rows: defaultRows
      }

      // Если позиция занята, сдвигаем блок вниз до первой свободной строки
      // Это позволяет гарантировать добавление блока даже возле нижней границы экрана
      while (hasCollision(target, null)) {
        target.startRow += 1
      }

      // При необходимости расширяем количество строк сетки
      gridRows.value = Math.max(gridRows.value, target.startRow + defaultRows + 2)

      // Позиция в пикселях для сохранения (верхний левый угол блока)
      x = (target.startCol - 1) * (gridCellWidth.value + GRID_GAP)
      y = (target.startRow - 1) * (gridCellHeight.value + GRID_GAP)

      blockWidth = gridCellWidth.value * defaultCols + GRID_GAP * (defaultCols - 1)
      blockHeight = gridCellHeight.value * defaultRows + GRID_GAP * (defaultRows - 1)
    }

    const blockConfig = {}
    if (data.pipelineChartId) {
      blockConfig.pipelineChartId = data.pipelineChartId
      blockConfig.chartType = data.chartType
      blockConfig.chartConfig = data.chartConfig
      blockConfig.engine = data.engine || 'echarts'
    }

    const newBlock = {
      type: data.type,
      x: Math.max(0, Math.round(x)),
      y: Math.max(0, Math.round(y)),
      width: Math.round(blockWidth),
      height: Math.round(blockHeight),
      config: blockConfig,
      order: props.blocks.length,
      _uid: crypto.randomUUID ? crypto.randomUUID() : `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }

    emit('block-add', newBlock)
  } catch (error) {
    console.error('Ошибка при добавлении блока:', error)
  }
}

// Обработка drag over
function handleDragOver(event) {
  if (props.mode !== 'edit') return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'copy'
  
  // Подсвечиваем ячейки при перетаскивании в grid режиме
  if (props.placementMode === 'grid' && gridCellWidth.value > 0) {
    const rect = canvasRef.value?.getBoundingClientRect()
    if (rect) {
      // Учитываем прокрутку канваса
      const scrollLeft = canvasRef.value?.scrollLeft || 0
      const scrollTop = canvasRef.value?.scrollTop || 0
      
      const x = event.clientX - rect.left + scrollLeft
      const y = event.clientY - rect.top + scrollTop
      
      const colIndex = Math.max(0, Math.floor(x / (gridCellWidth.value + GRID_GAP)))
      const rowIndex = Math.max(0, Math.floor(y / (gridCellHeight.value + GRID_GAP)))
      
      // Размер по умолчанию: 4 колонки, 3 строки
      const defaultCols = 4
      const defaultRows = 3
      
      const target = {
        startCol: colIndex + 1,
        startRow: rowIndex + 1,
        cols: defaultCols,
        rows: defaultRows
      }
      
      // Проверяем коллизии
      const valid = !hasCollision(target, null)
      
      dragOverPosition.value = {
        row: rowIndex + 1,
        col: colIndex + 1,
        cols: defaultCols,
        rows: defaultRows,
        valid
      }
      isDraggingOver.value = true
    }
  }
}

// Обработка drag enter
function handleDragEnter() {
  if (props.mode !== 'edit') return
  isDraggingOver.value = true
}

// Обработка drag leave
function handleDragLeave(event) {
  // Проверяем, что мы действительно покинули канвас, а не перешли на дочерний элемент
  const relatedTarget = event.relatedTarget
  if (!relatedTarget || !canvasRef.value?.contains(relatedTarget)) {
    isDraggingOver.value = false
    dragOverPosition.value = { row: null, col: null, cols: 4, rows: 3, valid: true }
  }
}

// Получение состояния ячейки для drag (valid/invalid)
function getCellDragState(row, col) {
  if (!isDraggingOver.value || dragOverPosition.value.row == null || dragOverPosition.value.col == null) {
    return 'none'
  }

  const { row: startRow, col: startCol, cols, rows: rowSpan, valid } = dragOverPosition.value

  const inside =
    row >= startRow &&
    row < startRow + rowSpan &&
    col >= startCol &&
    col < startCol + cols

  if (!inside) return 'none'
  return valid === false ? 'invalid' : 'valid'
}

// Вспомогательные функции для вычисления позиций
function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v))
}

function posToCell(clientX, clientY, offsetX, offsetY) {
  const rect = canvasRef.value?.getBoundingClientRect()
  if (!rect) return { col: 1, row: 1 }

  const scrollLeft = canvasRef.value?.scrollLeft || 0
  const scrollTop = canvasRef.value?.scrollTop || 0

  const cellW = gridCellWidth.value + GRID_GAP
  const cellH = gridCellHeight.value + GRID_GAP

  // координата верхнего-левого угла блока в системе контента канваса (с учётом прокрутки)
  const x = clientX - rect.left + scrollLeft - offsetX
  const y = clientY - rect.top + scrollTop - offsetY

  // "привязка" к сетке
  const col = Math.round(x / cellW) + 1
  const row = Math.round(y / cellH) + 1

  return { col, row }
}

function calcStartColFromX(xPx) {
  const cellW = gridCellWidth.value + GRID_GAP
  return Math.floor((xPx || 0) / cellW) + 1
}

function calcStartRowFromY(yPx) {
  const cellH = gridCellHeight.value + GRID_GAP
  return Math.floor((yPx || 0) / cellH) + 1
}

function calcColsFromWidth(widthPx) {
  if (gridCellWidth.value <= 0) return 4
  const cols = Math.round((widthPx + GRID_GAP) / (gridCellWidth.value + GRID_GAP))
  return Math.max(1, Math.min(cols, gridSize.value))
}

function calcRowsFromHeight(heightPx) {
  if (gridCellHeight.value <= 0) return 3
  const rows = Math.round((heightPx + GRID_GAP) / (gridCellHeight.value + GRID_GAP))
  return Math.max(1, rows)
}

const blocksGridBounds = computed(() => {
  if (props.placementMode !== 'grid') return []
  return props.blocks.map(b => ({
    id: b.id,
    startCol: calcStartColFromX(b.x),
    startRow: calcStartRowFromY(b.y),
    cols: calcColsFromWidth(b.width || gridCellWidth.value * 4 + GRID_GAP * 3),
    rows: calcRowsFromHeight(b.height || gridCellHeight.value * 3 + GRID_GAP * 2)
  }))
})

function hasCollision(target, exceptId) {
  const t = target
  for (const b of blocksGridBounds.value) {
    if (b.id === exceptId) continue
    const overlap =
      t.startCol < b.startCol + b.cols &&
      t.startCol + t.cols > b.startCol &&
      t.startRow < b.startRow + b.rows &&
      t.startRow + t.rows > b.startRow
    if (overlap) return true
  }
  return false
}

// Обновление preview при перемещении
function updateMovePreview(clientX, clientY) {
  if (!moving.value) return
  if (gridCellWidth.value <= 0 || gridCellHeight.value <= 0) return

  const { col, row } = posToCell(
    clientX,
    clientY,
    moving.value.offsetX,
    moving.value.offsetY
  )

  const maxColStart = gridSize.value - moving.value.cols + 1

  const startCol = clamp(col, 1, Math.max(1, maxColStart))
  const startRow = clamp(row, 1, 9999)

  const target = {
    startCol,
    startRow,
    cols: moving.value.cols,
    rows: moving.value.rows
  }

  const valid = !hasCollision(target, moving.value.blockId)

  moving.value.startCol = startCol
  moving.value.startRow = startRow
  moving.value.valid = valid

  // Включаем подсветку ячеек
  isDraggingOver.value = true
  dragOverPosition.value = {
    row: startRow,
    col: startCol,
    cols: moving.value.cols,
    rows: moving.value.rows,
    valid
  }

  // При необходимости увеличиваем gridRows
  gridRows.value = Math.max(gridRows.value, startRow + moving.value.rows + 2)
}

// Обработчики для grid-перемещения
function onGridMove(e) {
  e.preventDefault()
  updateMovePreview(e.clientX, e.clientY)
}

function onGridMoveEnd(e) {
  e.preventDefault()
  stopGridMove(true)
}

// Остановка grid-перемещения
function stopGridMove(commit) {
  if (!isBlockMoving.value) return

  window.removeEventListener('mousemove', onGridMove, true)
  window.removeEventListener('mouseup', onGridMoveEnd, true)

  const m = moving.value

  isBlockMoving.value = false
  moving.value = null

  // Сбрасываем подсветку
  isDraggingOver.value = false
  dragOverPosition.value = { row: null, col: null, cols: 4, rows: 3, valid: true }

  if (!commit || !m) return
  if (!m.valid) return

  const cellW = gridCellWidth.value + GRID_GAP
  const cellH = gridCellHeight.value + GRID_GAP

  const newX = (m.startCol - 1) * cellW
  const newY = (m.startRow - 1) * cellH

  const block = props.blocks.find(b => b.id === m.blockId)
  if (!block) return

  // ВАЖНО: size не меняем, только позицию
  emit('block-update', { ...block, x: newX, y: newY })
}

// Начало grid-перемещения
function startGridMove(payload) {
  if (props.mode !== 'edit') return
  if (props.placementMode !== 'grid') return

  const { block, pointer, offset, span } = payload

  isBlockMoving.value = true
  moving.value = {
    blockId: block.id,
    cols: span.cols,
    rows: span.rows,
    offsetX: offset.x,
    offsetY: offset.y,
    startCol: null,
    startRow: null,
    valid: true
  }

  updateMovePreview(pointer.x, pointer.y)

  window.addEventListener('mousemove', onGridMove, true)
  window.addEventListener('mouseup', onGridMoveEnd, true)
}

// --- Absolute перемещение (ghost как в сетке, коммит по mouseup) ---
function updateAbsoluteMovePreview(clientX, clientY) {
  if (!movingAbsolute.value || !canvasRef.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const scrollLeft = canvasRef.value.scrollLeft || 0
  const scrollTop = canvasRef.value.scrollTop || 0
  const left = Math.max(0, clientX - rect.left + scrollLeft - movingAbsolute.value.offsetX)
  const top = Math.max(0, clientY - rect.top + scrollTop - movingAbsolute.value.offsetY)
  movingAbsolute.value.left = left
  movingAbsolute.value.top = top
}

function onAbsoluteMove(e) {
  e.preventDefault()
  updateAbsoluteMovePreview(e.clientX, e.clientY)
}

function onAbsoluteMoveEnd(e) {
  e.preventDefault()
  stopAbsoluteMove(true)
}

function stopAbsoluteMove(commit) {
  if (!movingAbsolute.value) return
  window.removeEventListener('mousemove', onAbsoluteMove, true)
  window.removeEventListener('mouseup', onAbsoluteMoveEnd, true)
  const m = movingAbsolute.value
  movingAbsolute.value = null
  if (!commit || !m) return
  const block = props.blocks.find(b => b.id === m.blockId)
  if (!block) return
  emit('block-update', { ...block, x: m.left, y: m.top })
}

function startAbsoluteMove(payload) {
  if (props.mode !== 'edit') return
  if (props.placementMode !== 'absolute') return
  const { block, pointer, offset } = payload
  const width = block.width ?? 200
  const height = block.height ?? 150
  movingAbsolute.value = {
    blockId: block.id,
    offsetX: offset.x,
    offsetY: offset.y,
    left: block.x ?? 0,
    top: block.y ?? 0,
    width,
    height
  }
  updateAbsoluteMovePreview(pointer.x, pointer.y)
  window.addEventListener('mousemove', onAbsoluteMove, true)
  window.addEventListener('mouseup', onAbsoluteMoveEnd, true)
}

// Обработка клика по canvas (для снятия выделения)
function handleCanvasClick(event) {
  // Если клик был не по блоку (не по dashboard-block), снимаем выделение
  const clickedBlock = event.target.closest('.dashboard-block')
  if (!clickedBlock) {
    emit('canvas-click')
  }
}

// Обработка клика по блоку (останавливаем всплытие, чтобы canvas не сбрасывал выделение)
function handleBlockClick(block, event) {
  if (event) event.stopPropagation()
  emit('block-click', block, event)
}

// Обработка открытия настроек блока
function handleBlockSettings(block, event) {
  emit('block-settings', block, event)
}

// Обработка удаления блока
function handleBlockDelete(block) {
  emit('block-delete', block)
}

// Обработка изменения размера блока (во время перетаскивания — только локальное обновление)
function handleBlockResize(updatedBlock) {
  if (props.placementMode === 'grid' && gridCellWidth.value > 0 && gridCellHeight.value > 0) {
    const startCol = calcStartColFromX(updatedBlock.x)
    const startRow = calcStartRowFromY(updatedBlock.y)
    const cols = calcColsFromWidth(updatedBlock.width)
    const rows = calcRowsFromHeight(updatedBlock.height)
    const target = { startCol, startRow, cols, rows }
    if (hasCollision(target, updatedBlock.id)) {
      console.warn('Невозможно изменить размер блока: будет коллизия с другими блоками')
      return
    }
  }
  emit('block-update-local', updatedBlock)
}

// Коммит размера по окончании ресайза (один API + undo)
function handleResizeEnd(updatedBlock) {
  emit('block-update', updatedBlock)
}

// Обработка перемещения блока
function handleBlockMove(updatedBlock) {
  emit('block-update', updatedBlock)
}

// Вычисление ширины ячейки сетки
function calculateGridCellWidth() {
  if (!canvasRef.value || props.placementMode !== 'grid') return

  nextTick(() => {
    const rect = canvasRef.value?.getBoundingClientRect()
    if (rect) {
      // Учитываем gap между колонками (0.5rem = 8px) и padding
      const gap = 8
      const padding = 24 // 1.5rem = 24px с каждой стороны
      const totalGaps = (gridSize.value - 1) * gap
      gridCellWidth.value = Math.floor((rect.width - padding * 2 - totalGaps) / gridSize.value)
    }
  })
}

// Вычисление необходимого количества строк на основе блоков
function calculateGridRows() {
  if (props.placementMode !== 'grid' || props.blocks.length === 0) {
    gridRows.value = 12 // Минимум 12 строк
    return
  }

  let maxRow = 0
  props.blocks.forEach(block => {
    // Вычисляем строку, на которой заканчивается блок
    const blockStartRow = Math.floor((block.y || 0) / (gridCellHeight.value + 8))
    const blockHeightInRows = Math.ceil((block.height || gridCellHeight.value) / (gridCellHeight.value + 8))
    const blockEndRow = blockStartRow + blockHeightInRows
    maxRow = Math.max(maxRow, blockEndRow)
  })

  // Добавляем запас и округляем до минимум 12
  gridRows.value = Math.max(12, maxRow + 2)
}

// Обработка изменения размера окна
function handleResize() {
  calculateGridCellWidth()
  calculateGridRows()
}

// Пересчёт строк только при изменении количества блоков или их позиций/размеров (без deep)
watch(
  () => [props.blocks.length, props.blocks.map(b => `${b.y}-${b.height}`).join('|')],
  () => {
    if (props.placementMode === 'grid') calculateGridRows()
  }
)

// Отслеживание изменения режима размещения
watch(() => props.placementMode, (newMode) => {
  if (newMode === 'grid') {
    nextTick(() => {
      calculateGridCellWidth()
      calculateGridRows()
    })
  }
})

onMounted(() => {
  calculateGridCellWidth()
  calculateGridRows()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.dashboard-canvas {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  background: #f8f9fa;
  position: relative;
  min-height: 100%;

  &--grid {
    // Grid режим
  }

  &--absolute {
    // Absolute режим
  }
}

.dashboard-canvas-grid-wrapper {
  position: relative;
  width: 100%;
  min-height: 100%;
}

.grid-background {
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  pointer-events: none;
  z-index: 0;
  padding: 0;
}

.grid-row {
  display: grid;
  gap: 0.5rem;
}

.grid-cell {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 2px;
  transition: all 0.2s ease;
  
  &:hover {
    background: rgba(0, 0, 0, 0.02);
  }
  
  &--highlighted {
    background: rgba(var(--bs-primary-rgb), 0.15) !important;
    border-color: var(--bs-primary) !important;
    border-width: 2px;
    box-shadow: 0 0 0 2px rgba(var(--bs-primary-rgb), 0.2);
  }

  &--invalid {
    background: rgba(220, 53, 69, 0.12) !important;
    border-color: #dc3545 !important;
    border-width: 2px;
    box-shadow: 0 0 0 2px rgba(220, 53, 69, 0.2);
  }
}

.grid-drag-ghost {
  position: absolute;
  pointer-events: none;
  z-index: 10;
  border: 2px dashed rgba(var(--bs-primary-rgb), 0.6);
  background: rgba(var(--bs-primary-rgb), 0.08);
  border-radius: 8px;
  transition: none;

  &--invalid {
    border-color: rgba(220, 53, 69, 0.7);
    background: rgba(220, 53, 69, 0.08);
  }
}

.dashboard-canvas-grid {
  position: relative;
  z-index: 1;
}

.dashboard-canvas-absolute {
  position: relative;
  width: 100%;
  min-height: 100%;
}

.absolute-drag-ghost {
  position: absolute;
  pointer-events: none;
  z-index: 10;
  border: 2px dashed rgba(var(--bs-primary-rgb), 0.6);
  background: rgba(var(--bs-primary-rgb), 0.08);
  border-radius: 8px;
  transition: none;
}


.block-content-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary, #666);
  font-size: 14px;
}
</style>
