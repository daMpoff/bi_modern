<template>
  <div
    ref="blockRef"
    class="dashboard-block dashboard-block--absolute"
    :class="{
      'dashboard-block--selected': isSelected,
      'dashboard-block--ghosted': isGhosted,
      'dashboard-block--view': mode === 'view'
    }"
    :style="blockStyle"
  >
    <!-- Invisible drag zone -->
    <div
      v-if="mode === 'edit'"
      class="dashboard-block-drag-zone"
      @mousedown="handleHeaderMouseDown"
    />

    <!-- Floating action buttons -->
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

    <!-- Inline title -->
    <div v-if="blockTitle" class="dashboard-block-inline-title">
      {{ blockTitle }}
      <span v-if="blockSubtitle" class="dashboard-block-inline-subtitle">{{ blockSubtitle }}</span>
    </div>

    <div class="dashboard-block-content">
      <slot>
        <div class="dashboard-block-placeholder">{{ block.type }}</div>
      </slot>
    </div>

    <template v-if="mode === 'edit'">
      <div class="resize-handle resize-handle-nw" @mousedown="(e) => startResize(e, 'nw')" title="Изменить размер"></div>
      <div class="resize-handle resize-handle-ne" @mousedown="(e) => startResize(e, 'ne')" title="Изменить размер"></div>
      <div class="resize-handle resize-handle-sw" @mousedown="(e) => startResize(e, 'sw')" title="Изменить размер"></div>
      <div class="resize-handle resize-handle-se" @mousedown="(e) => startResize(e, 'se')" title="Изменить размер"></div>
      <div class="resize-handle resize-handle-n" @mousedown="(e) => startResize(e, 'n')" title="Изменить высоту"></div>
      <div class="resize-handle resize-handle-s" @mousedown="(e) => startResize(e, 's')" title="Изменить высоту"></div>
      <div class="resize-handle resize-handle-w" @mousedown="(e) => startResize(e, 'w')" title="Изменить ширину"></div>
      <div class="resize-handle resize-handle-e" @mousedown="(e) => startResize(e, 'e')" title="Изменить ширину"></div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { Type, X, Settings, Maximize2 } from 'lucide-vue-next'
import { DASHBOARD_BLOCK_ICONS, BLOCK_TYPE_CHART } from './js/blockTypesRegistry.js'

const props = defineProps({
  block: { type: Object, required: true },
  mode: { type: String, default: 'edit', validator: (v) => ['edit', 'view'].includes(v) },
  isSelected: { type: Boolean, default: false },
  isGhosted: { type: Boolean, default: false }
})

const emit = defineEmits(['click', 'settings', 'delete', 'resize', 'resize-end', 'absolute-move-start', 'focus-mode'])

const blockRef = ref(null)

const blockIcon = computed(() => DASHBOARD_BLOCK_ICONS[props.block.type] || Type)
const blockTitle = computed(() => props.block?.config?.title || props.block?.type || '')
const blockSubtitle = computed(() => props.block?.config?.subtitle || '')
const isChartBlock = computed(() => props.block?.type === BLOCK_TYPE_CHART)

const blockStyle = computed(() => ({
  position: 'absolute',
  left: `${props.block.x ?? 0}px`,
  top: `${props.block.y ?? 0}px`,
  width: `${props.block.width ?? 200}px`,
  height: `${props.block.height ?? 150}px`
}))

function handleSettings(e) {
  e.stopPropagation()
  emit('settings', props.block, e)
}

function handleFocusMode(event) {
  event.stopPropagation()
  emit('focus-mode', props.block)
}

function handleHeaderMouseDown(event) {
  if (props.mode !== 'edit') return
  const rect = blockRef.value?.getBoundingClientRect()
  if (!rect) return
  emit('absolute-move-start', {
    block: props.block,
    pointer: { x: event.clientX, y: event.clientY },
    offset: { x: event.clientX - rect.left, y: event.clientY - rect.top }
  })
  event.preventDefault()
  event.stopPropagation()
}

const isResizing = ref(false)
const resizeStart = ref({ x: 0, y: 0, width: 0, height: 0, left: 0, top: 0 })
const resizeDirection = ref('')
const lastEmittedResizeBlock = ref(null)

function getResizeCursor(direction) {
  const cursors = { nw: 'nwse-resize', ne: 'nesw-resize', sw: 'nesw-resize', se: 'nwse-resize', n: 'ns-resize', s: 'ns-resize', w: 'ew-resize', e: 'ew-resize' }
  return cursors[direction] || 'default'
}

function startResize(event, direction) {
  if (props.mode !== 'edit') return
  if (isResizing.value) return
  isResizing.value = true
  resizeDirection.value = direction
  resizeStart.value = {
    x: event.clientX,
    y: event.clientY,
    width: props.block.width ?? 200,
    height: props.block.height ?? 150,
    left: props.block.x ?? 0,
    top: props.block.y ?? 0
  }
  document.body.style.userSelect = 'none'
  document.body.style.cursor = getResizeCursor(direction)
  document.documentElement.style.cursor = getResizeCursor(direction)
  window.addEventListener('mousemove', onResize, { passive: false, capture: true })
  window.addEventListener('mouseup', stopResize, { passive: false, capture: true })
  document.addEventListener('mousemove', onResize, { passive: false, capture: true })
  document.addEventListener('mouseup', stopResize, { passive: false, capture: true })
  event.preventDefault()
  event.stopPropagation()
}

const minWidth = 100
const minHeight = 80

function onResize(event) {
  if (!isResizing.value) return
  event.preventDefault()
  event.stopPropagation()
  const deltaX = event.clientX - resizeStart.value.x
  const deltaY = event.clientY - resizeStart.value.y
  const direction = resizeDirection.value
  let newWidth = resizeStart.value.width
  let newHeight = resizeStart.value.height
  let newLeft = resizeStart.value.left
  let newTop = resizeStart.value.top

  if (direction.includes('e')) newWidth = resizeStart.value.width + deltaX
  else if (direction.includes('w')) {
    newWidth = resizeStart.value.width - deltaX
    newLeft = resizeStart.value.left + deltaX
  }
  if (direction.includes('s')) newHeight = resizeStart.value.height + deltaY
  else if (direction.includes('n')) {
    newHeight = resizeStart.value.height - deltaY
    newTop = resizeStart.value.top + deltaY
  }

  newWidth = Math.max(minWidth, newWidth)
  newHeight = Math.max(minHeight, newHeight)
  if (direction.includes('w') && newWidth < minWidth) {
    newWidth = minWidth
    newLeft = resizeStart.value.left + (resizeStart.value.width - minWidth)
  }
  if (direction.includes('n') && newHeight < minHeight) {
    newHeight = minHeight
    newTop = resizeStart.value.top + (resizeStart.value.height - minHeight)
  }

  const payload = { ...props.block, width: newWidth, height: newHeight, x: newLeft, y: newTop }
  lastEmittedResizeBlock.value = payload
  emit('resize', payload)
}

function stopResize(event) {
  if (!isResizing.value) return
  if (lastEmittedResizeBlock.value) {
    emit('resize-end', lastEmittedResizeBlock.value)
    lastEmittedResizeBlock.value = null
  }
  isResizing.value = false
  window.removeEventListener('mousemove', onResize, { capture: true })
  window.removeEventListener('mouseup', stopResize, { capture: true })
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
    &:hover { box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04); }
  }

  &--selected {
    border-color: var(--bs-primary);
    box-shadow: 0 0 0 1px var(--bs-primary), 0 2px 8px rgba(var(--bs-primary-rgb), 0.12);
  }

  &--ghosted { opacity: 0.35; }
}

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
  .dashboard-block--view & { opacity: 0; }
  .dashboard-block--view:hover & { opacity: 1; pointer-events: auto; }
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

  &:hover { background: #fff; color: var(--bs-primary, #0d6efd); box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12); }
  &--danger:hover { color: #dc3545; }
}

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

  &:hover { background-color: rgba(var(--bs-primary-rgb), 0.25); }
  &:active { background-color: rgba(var(--bs-primary-rgb), 0.35); }

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
