<template>
  <div
    ref="blockRef"
    class="dashboard-block"
    :class="{
      'dashboard-block--grid': true,
      'dashboard-block--selected': isSelected,
      'dashboard-block--ghosted': isGhosted,
      'dashboard-block--view': mode === 'view'
    }"
    :style="blockStyle"
  >
    <!-- Invisible drag zone (top area of the block) -->
    <div
      v-if="mode === 'edit'"
      class="dashboard-block-drag-zone"
      @mousedown="handleHeaderMouseDown"
    />

    <!-- Floating action buttons (appear on hover, edit mode) -->
    <div class="dashboard-block-actions">
      <slot name="header-actions-start" />
      <button
        v-if="isChartBlock"
        class="dashboard-block-action-btn"
        @click.stop="handleFocusMode"
        title="Открыть в полном размере"
      >
        <Maximize2 :size="15" />
      </button>
      <button
        v-if="mode === 'edit'"
        class="dashboard-block-action-btn"
        @click.stop="handleSettings"
        title="Настройки блока"
      >
        <Settings :size="15" />
      </button>
      <button
        v-if="mode === 'edit'"
        class="dashboard-block-action-btn dashboard-block-action-btn--danger"
        @click.stop="handleDelete"
        title="Удалить блок"
      >
        <X :size="15" />
      </button>
    </div>

    <!-- Inline title (shown inside content, not in a separate bar) -->
    <div v-if="blockTitle" class="dashboard-block-inline-title">
      {{ blockTitle }}
      <span v-if="blockSubtitle" class="dashboard-block-inline-subtitle">{{ blockSubtitle }}</span>
    </div>

    <!-- Содержимое блока -->
    <div class="dashboard-block-content">
      <slot>
        <div class="dashboard-block-placeholder">
          {{ block.type }}
        </div>
      </slot>
    </div>

    <!-- Ручки для изменения размера (только в режиме редактирования) -->
    <template v-if="mode === 'edit'">
      <!-- Углы -->
      <div
        class="resize-handle resize-handle-nw"
        @mousedown="(e) => startResize(e, 'nw')"
        title="Изменить размер"
      ></div>
      <div
        class="resize-handle resize-handle-ne"
        @mousedown="(e) => startResize(e, 'ne')"
        title="Изменить размер"
      ></div>
      <div
        class="resize-handle resize-handle-sw"
        @mousedown="(e) => startResize(e, 'sw')"
        title="Изменить размер"
      ></div>
      <div
        class="resize-handle resize-handle-se"
        @mousedown="(e) => startResize(e, 'se')"
        title="Изменить размер"
      ></div>
      <!-- Края -->
      <div
        class="resize-handle resize-handle-n"
        @mousedown="(e) => startResize(e, 'n')"
        title="Изменить высоту"
      ></div>
      <div
        class="resize-handle resize-handle-s"
        @mousedown="(e) => startResize(e, 's')"
        title="Изменить высоту"
      ></div>
      <div
        class="resize-handle resize-handle-w"
        @mousedown="(e) => startResize(e, 'w')"
        title="Изменить ширину"
      ></div>
      <div
        class="resize-handle resize-handle-e"
        @mousedown="(e) => startResize(e, 'e')"
        title="Изменить ширину"
      ></div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { Type, X, Settings, Maximize2 } from 'lucide-vue-next'
import { DASHBOARD_BLOCK_ICONS, BLOCK_TYPE_CHART } from './js/blockTypesRegistry.js'

const props = defineProps({
  block: {
    type: Object,
    required: true
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
  isSelected: {
    type: Boolean,
    default: false
  },
  isGhosted: {
    type: Boolean,
    default: false
  },
  gridSize: {
    type: Number,
    default: 12
  },
  gridCellWidth: {
    type: Number,
    default: 0
  },
  gridCellHeight: {
    type: Number,
    default: 50
  }
})

const emit = defineEmits(['update:block', 'click', 'settings', 'delete', 'resize', 'resize-end', 'grid-move-start', 'focus-mode'])

const blockRef = ref(null)

const blockIcon = computed(() => DASHBOARD_BLOCK_ICONS[props.block.type] || Type)
const blockTitle = computed(() => props.block?.config?.title || props.block?.type || '')
const blockSubtitle = computed(() => props.block?.config?.subtitle || '')
const isChartBlock = computed(() => props.block?.type === BLOCK_TYPE_CHART)

// Константа для gap между ячейками
const GRID_GAP = 8 // 0.5rem = 8px

// Вычисление количества колонок для блока на основе width
function calculateColsFromWidth(width) {
  if (props.gridCellWidth <= 0) return 4
  // width = cols * cellWidth + (cols - 1) * gap
  // width = cols * (cellWidth + gap) - gap
  // cols = (width + gap) / (cellWidth + gap)
  const cols = Math.round((width + GRID_GAP) / (props.gridCellWidth + GRID_GAP))
  return Math.max(1, Math.min(cols, props.gridSize))
}

// Вычисление количества строк для блока на основе height
function calculateRowsFromHeight(height) {
  if (props.gridCellHeight <= 0) return 3
  // height = rows * cellHeight + (rows - 1) * gap
  // height = rows * (cellHeight + gap) - gap
  // rows = (height + gap) / (cellHeight + gap)
  const rows = Math.round((height + GRID_GAP) / (props.gridCellHeight + GRID_GAP))
  return Math.max(1, rows)
}

// Вычисление width на основе количества колонок
function calculateWidthFromCols(cols) {
  if (props.gridCellWidth <= 0) return 200
  return cols * props.gridCellWidth + (cols - 1) * GRID_GAP
}

// Вычисление height на основе количества строк
function calculateHeightFromRows(rows) {
  if (props.gridCellHeight <= 0) return 150
  return rows * props.gridCellHeight + (rows - 1) * GRID_GAP
}

// Вычисление количества колонок для блока
const blockColSpan = computed(() => {
  if (props.placementMode !== 'grid') return 4
  return calculateColsFromWidth(props.block.width || calculateWidthFromCols(4))
})

// Вычисление количества строк для блока
const blockRowSpan = computed(() => {
  if (props.placementMode !== 'grid') return 3
  return calculateRowsFromHeight(props.block.height || calculateHeightFromRows(3))
})

// Вычисление начальной колонки и строки для блока
const blockStartCol = computed(() => {
  if (props.placementMode !== 'grid' || props.gridCellWidth <= 0) return 1
  const x = props.block.x || 0
  // x = (col - 1) * (cellWidth + gap)
  // col = x / (cellWidth + gap) + 1
  const col = Math.floor(x / (props.gridCellWidth + GRID_GAP)) + 1
  return Math.max(1, Math.min(col, props.gridSize))
})

const blockStartRow = computed(() => {
  if (props.placementMode !== 'grid' || props.gridCellHeight <= 0) return 1
  const y = props.block.y || 0
  // y = (row - 1) * (cellHeight + gap)
  // row = y / (cellHeight + gap) + 1
  const row = Math.floor(y / (props.gridCellHeight + GRID_GAP)) + 1
  return Math.max(1, row)
})

// Стили блока (только grid)
const blockStyle = computed(() => {
  const startCol = blockStartCol.value
  const colSpan = blockColSpan.value
  const startRow = blockStartRow.value
  const rowSpan = blockRowSpan.value
  const finalStartCol = Math.max(1, Math.min(startCol, props.gridSize))
  const finalColSpan = Math.max(1, Math.min(colSpan, props.gridSize - finalStartCol + 1))
  return {
    gridColumn: `${finalStartCol} / span ${finalColSpan}`,
    gridRow: `${startRow} / span ${rowSpan}`
  }
})

// Состояние для изменения размера
const isResizing = ref(false)
const resizeStart = ref({ 
  x: 0, 
  y: 0, 
  width: 0, 
  height: 0, 
  left: 0, 
  top: 0,
  initialCols: 0,
  initialRows: 0,
  initialStartCol: 0,
  initialStartRow: 0
})
const resizeDirection = ref('')
const lastEmittedResizeBlock = ref(null)

function handleSettings(event) {
  event.stopPropagation()
  emit('settings', props.block, event)
}

function handleFocusMode(event) {
  event.stopPropagation()
  emit('focus-mode', props.block)
}

// Начало перетаскивания за шапку (grid: ghost в Canvas, коммит по mouseup)
function handleHeaderMouseDown(event) {
  if (props.mode !== 'edit') return
  const rect = blockRef.value?.getBoundingClientRect()
  if (!rect) return
  emit('grid-move-start', {
    block: props.block,
    pointer: { x: event.clientX, y: event.clientY },
    offset: { x: event.clientX - rect.left, y: event.clientY - rect.top },
    span: { cols: blockColSpan.value, rows: blockRowSpan.value }
  })
  event.preventDefault()
  event.stopPropagation()
}

// Начало изменения размера
function startResize(event, direction) {
  if (props.mode !== 'edit') return
  
  // Если уже идет изменение размера, сначала останавливаем его
  if (isResizing.value) {
    stopResize()
  }

  isResizing.value = true
  resizeDirection.value = direction
  
  // Сохраняем начальные значения в колонках/строках для grid режима
  const initialCols = blockColSpan.value
  const initialRows = blockRowSpan.value
  const initialStartCol = blockStartCol.value
  const initialStartRow = blockStartRow.value

  resizeStart.value = {
    x: event.clientX,
    y: event.clientY,
    width: props.block.width || 200,
    height: props.block.height || 150,
    left: props.block.x || 0,
    top: props.block.y || 0,
    // Для grid режима сохраняем начальные колонки/строки
    initialCols,
    initialRows,
    initialStartCol,
    initialStartRow
  }

  // Блокируем выделение текста и изменение курсора на всем body
  document.body.style.userSelect = 'none'
  document.body.style.cursor = getResizeCursor(direction)
  // Устанавливаем курсор на весь документ для надежного отслеживания
  document.documentElement.style.cursor = getResizeCursor(direction)
  
  // Используем window с capture phase для максимально надежного захвата мыши
  // window гарантирует обработку событий даже когда мышь выходит за пределы viewport
  window.addEventListener('mousemove', onResize, { passive: false, capture: true })
  window.addEventListener('mouseup', stopResize, { passive: false, capture: true })
  // Также добавляем на document для дополнительной надежности
  document.addEventListener('mousemove', onResize, { passive: false, capture: true })
  document.addEventListener('mouseup', stopResize, { passive: false, capture: true })
  // Обрабатываем mouseleave на window для предотвращения потери захвата
  window.addEventListener('mouseleave', handleWindowMouseLeave, { passive: false, capture: true })
  
  // Предотвращаем стандартное поведение
  event.preventDefault()
  event.stopPropagation()
}

// Получение курсора для направления изменения размера
function getResizeCursor(direction) {
  const cursors = {
    'nw': 'nwse-resize',
    'ne': 'nesw-resize',
    'sw': 'nesw-resize',
    'se': 'nwse-resize',
    'n': 'ns-resize',
    's': 'ns-resize',
    'w': 'ew-resize',
    'e': 'ew-resize'
  }
  return cursors[direction] || 'default'
}

// Изменение размера
function onResize(event) {
  if (!isResizing.value) return

  // Всегда предотвращаем стандартное поведение
  event.preventDefault()
  event.stopPropagation()

  // Используем clientX/clientY для получения координат относительно viewport
  // Это работает даже когда мышь выходит за пределы блока
  const deltaX = event.clientX - resizeStart.value.x
  const deltaY = event.clientY - resizeStart.value.y
  const direction = resizeDirection.value

  const minCols = 2
  const minRows = 2

  let newWidth = resizeStart.value.width
  let newHeight = resizeStart.value.height
  let newLeft = props.block.x || 0
  let newTop = props.block.y || 0

  if (props.gridCellWidth > 0 && props.gridCellHeight > 0) {
    // Используем начальные значения колонок/строк
    let newCols = resizeStart.value.initialCols || blockColSpan.value
    let newRows = resizeStart.value.initialRows || blockRowSpan.value
    let newStartCol = resizeStart.value.initialStartCol || blockStartCol.value
    let newStartRow = resizeStart.value.initialStartRow || blockStartRow.value

    // Вычисляем изменение в колонках/строках на основе deltaX/deltaY
    const cellWidthWithGap = props.gridCellWidth + GRID_GAP
    const cellHeightWithGap = props.gridCellHeight + GRID_GAP

    // Изменение ширины
    if (direction.includes('e')) {
      // Увеличиваем количество колонок
      const deltaCols = Math.round(deltaX / cellWidthWithGap)
      newCols = Math.max(minCols, Math.min(resizeStart.value.initialCols + deltaCols, props.gridSize))
    } else if (direction.includes('w')) {
      // Уменьшаем количество колонок и сдвигаем начальную колонку
      const deltaCols = Math.round(deltaX / cellWidthWithGap)
      const proposedCols = resizeStart.value.initialCols - deltaCols
      if (proposedCols >= minCols) {
        newCols = Math.min(proposedCols, props.gridSize)
        newStartCol = Math.max(1, resizeStart.value.initialStartCol + deltaCols)
      } else {
        newCols = minCols
        newStartCol = resizeStart.value.initialStartCol
      }
    }

    // Изменение высоты
    if (direction.includes('s')) {
      // Увеличиваем количество строк
      const deltaRows = Math.round(deltaY / cellHeightWithGap)
      newRows = Math.max(minRows, resizeStart.value.initialRows + deltaRows)
    } else if (direction.includes('n')) {
      // Уменьшаем количество строк и сдвигаем начальную строку
      const deltaRows = Math.round(deltaY / cellHeightWithGap)
      const proposedRows = resizeStart.value.initialRows - deltaRows
      if (proposedRows >= minRows) {
        newRows = Math.max(minRows, proposedRows)
        newStartRow = Math.max(1, resizeStart.value.initialStartRow + deltaRows)
      } else {
        newRows = minRows
        newStartRow = resizeStart.value.initialStartRow
      }
    }

    // Вычисляем новую ширину и высоту на основе колонок и строк
    newWidth = calculateWidthFromCols(newCols)
    newHeight = calculateHeightFromRows(newRows)

    // Вычисляем новую позицию на основе начальной колонки/строки
    newLeft = (newStartCol - 1) * cellWidthWithGap
    newTop = (newStartRow - 1) * cellHeightWithGap
  }

  const payload = { ...props.block, width: newWidth, height: newHeight, x: newLeft, y: newTop }
  lastEmittedResizeBlock.value = payload
  emit('resize', payload)
}

// Обработка mouseleave на window - продолжаем изменение размера даже при выходе мыши
function handleWindowMouseLeave(event) {
  // Не останавливаем изменение размера при выходе мыши за пределы окна
  // Это позволяет продолжать изменение размера даже когда мышь выходит за границы
  // Просто предотвращаем стандартное поведение
  if (isResizing.value) {
    event.preventDefault()
    event.stopPropagation()
  }
}

// Остановка изменения размера
function stopResize(event) {
  if (!isResizing.value) return
  
  if (lastEmittedResizeBlock.value) {
    emit('resize-end', lastEmittedResizeBlock.value)
    lastEmittedResizeBlock.value = null
  }
  isResizing.value = false
  
  window.removeEventListener('mousemove', onResize, { capture: true })
  window.removeEventListener('mouseup', stopResize, { capture: true })
  window.removeEventListener('mouseleave', handleWindowMouseLeave, { capture: true })
  document.removeEventListener('mousemove', onResize, { capture: true })
  document.removeEventListener('mouseup', stopResize, { capture: true })
  
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
  document.documentElement.style.cursor = ''
  
  if (event) {
    event.preventDefault()
    event.stopPropagation()
  }
}

// Удаление блока
function handleDelete(event) {
  event.stopPropagation()
  emit('delete', props.block)
}

onUnmounted(() => {
  stopResize()
})
</script>

<style scoped lang="scss">
.dashboard-block {
  position: relative;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 8px;
  overflow: hidden;
  cursor: default;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  &--view {
    cursor: default;

    &:hover {
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }
  }

  &--selected {
    border-color: var(--bs-primary);
    box-shadow: 0 0 0 1px var(--bs-primary), 0 2px 8px rgba(var(--bs-primary-rgb), 0.12);
  }

  &--ghosted {
    opacity: 0.35;
  }
}

/* Invisible drag zone — top 28px of the block, cursor: move in edit mode */
.dashboard-block-drag-zone {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 28px;
  z-index: 25;
  cursor: move;
  user-select: none;
}

/* Floating action buttons — top-right corner, visible on hover */
.dashboard-block-actions {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s ease;
  pointer-events: none;

  .dashboard-block:hover &,
  .dashboard-block--selected & {
    opacity: 1;
    pointer-events: auto;
  }

  /* In view mode, only show expand button on hover */
  .dashboard-block--view & {
    opacity: 0;
  }

  .dashboard-block--view:hover & {
    opacity: 1;
    pointer-events: auto;
  }
}

.dashboard-block-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  color: var(--bs-secondary, #6c757d);
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);

  &:hover {
    background: #fff;
    color: var(--bs-primary, #0d6efd);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  }

  &--danger:hover {
    color: #dc3545;
  }
}

/* Inline title — subtle label at the top of the content area */
.dashboard-block-inline-title {
  padding: 10px 14px 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--bs-body-color, #212529);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.dashboard-block-inline-subtitle {
  font-weight: 400;
  color: var(--bs-secondary, #6c757d);
  margin-left: 0.375rem;
  font-size: 0.75rem;
}

.dashboard-block-content {
  flex: 1;
  min-height: 80px;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.dashboard-block-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--bs-secondary, #6c757d);
  font-size: 0.85rem;
  opacity: 0.5;
}

.resize-handle {
  position: absolute;
  z-index: 20;
  background-color: transparent;
  transition: background-color 0.15s ease;
  pointer-events: auto;

  &:hover {
    background-color: rgba(var(--bs-primary-rgb), 0.25);
  }

  &:active {
    background-color: rgba(var(--bs-primary-rgb), 0.35);
  }

  &-nw { top: -4px; left: -4px; width: 14px; height: 14px; cursor: nwse-resize; }
  &-ne { top: -4px; right: -4px; width: 14px; height: 14px; cursor: nesw-resize; }
  &-sw { bottom: -4px; left: -4px; width: 14px; height: 14px; cursor: nesw-resize; }
  &-se { bottom: -4px; right: -4px; width: 14px; height: 14px; cursor: nwse-resize; }
  &-n { top: -4px; left: 10px; right: 10px; height: 10px; cursor: ns-resize; }
  &-s { bottom: -4px; left: 10px; right: 10px; height: 10px; cursor: ns-resize; }
  &-w { left: -4px; top: 10px; bottom: 10px; width: 10px; cursor: ew-resize; }
  &-e { right: -4px; top: 10px; bottom: 10px; width: 10px; cursor: ew-resize; }
}
</style>
