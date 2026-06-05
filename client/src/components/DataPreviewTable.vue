<template>
  <div
    class="data-preview-panel"
    :class="{ collapsed }"
    :style="panelStyle"
  >
    <!-- Resize drag-handle -->
    <div v-if="!collapsed" class="dp-resize" @mousedown.prevent="startResize">
      <div class="dp-resize__grip" />
    </div>

    <!-- Collapsible header -->
    <div class="dp-header" @click="$emit('update:collapsed', !collapsed)">
      <h3 class="dp-header__title">
        Предпросмотр данных
        <span v-if="totalRows != null" class="dp-badge dp-badge--rows">{{ formatRowCount(totalRows) }} строк</span>
        <span v-if="requestTimeMs != null" class="dp-badge dp-badge--time">{{ formatRequestTime(requestTimeMs) }}</span>
      </h3>
      <button type="button" class="dp-header__chevron" :class="{ rotated: collapsed }">
        <ChevronDown :size="16" />
      </button>
    </div>

    <template v-if="!collapsed">
      <div v-if="!columns.length" class="dp-empty">
        Нажмите «Выполнить» для предпросмотра данных
      </div>

      <template v-else>
        <!-- Fixed table header (horizontal-scroll synced with body) -->
        <div class="dp-thead" ref="theadRef" :style="{ paddingRight: scrollbarW + 'px' }">
          <table class="dp-table">
            <colgroup>
              <col class="dp-col-rn" />
              <col v-for="c in columns" :key="'h'+c" :style="{ width: colW(c) + 'px' }" />
            </colgroup>
            <thead>
              <tr>
                <th class="dp-cell-rn">#</th>
                <th v-for="c in columns" :key="c" :title="c">{{ c }}</th>
              </tr>
            </thead>
          </table>
        </div>

        <!-- Virtual-scroll body -->
        <div class="dp-body" ref="scrollRef" @scroll="onScroll">
          <div :style="{ height: sentinelHeight + 'px', position: 'relative' }">
            <table
              class="dp-table"
              :style="{ transform: `translateY(${tableOffsetY}px)`, willChange: 'transform' }"
            >
              <colgroup>
                <col class="dp-col-rn" />
                <col v-for="c in columns" :key="'b'+c" :style="{ width: colW(c) + 'px' }" />
              </colgroup>
              <tbody>
                <tr
                  v-for="ri in visibleRowIndexes"
                  :key="ri"
                  :class="{ 'dp-row--even': ri % 2 === 0, 'dp-row--loading': isRowLoading(ri) }"
                >
                  <td class="dp-cell-rn">{{ ri + 1 }}</td>
                  <td v-for="c in columns" :key="c" :title="String(getRowCell(ri, c))">
                    <span v-if="isRowLoading(ri)" class="dp-skeleton" />
                    <template v-else>{{ getRowCell(ri, c) }}</template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Bottom status bar -->
        <div class="dp-status">
          <span class="dp-status__pos">
            Строки {{ displayStartRow }}&ndash;{{ displayEndRow }} из {{ formatNumber(totalRows) }}
          </span>
          <label class="dp-status__goto">
            <span>Перейти:</span>
            <input
              v-model.number="goToRowInput"
              type="number"
              min="1"
              :max="totalRows"
              class="dp-status__input"
              placeholder="№"
              @keyup.enter="scrollToRow"
            />
            <button type="button" class="dp-status__btn" @click="scrollToRow">OK</button>
          </label>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

const props = defineProps({
  columns:             { type: Array,     default: () => [] },
  data:                { type: Array,     default: () => [] },
  rowsCount:           { type: Number,    default: null },
  requestTimeMs:       { type: Number,    default: null },
  collapsed:           { type: Boolean,   default: false },
  resultSetId:         { type: String,    default: null },
  chunkSize:           { type: Number,    default: 5000 },
  chunks:              { type: Object,    default: () => ({}) },
  loadingChunkIndexes: { type: [Set, Object], default: null },
  pipelineId:          { type: Number,    default: null },
  loadChunk:           { type: Function,  default: null },
})

defineEmits(['update:collapsed'])

/* ── Constants ── */
const ROW_HEIGHT  = 32
const OVERSCAN    = 10
const MAX_SCROLL  = 10_000_000   // safe scroll-height limit across browsers
const MIN_PANEL   = 140
const DEF_PANEL   = 280
const MAX_VH      = 0.6

/* ── Refs ── */
const scrollRef    = ref(null)
const theadRef     = ref(null)
const goToRowInput = ref(null)
const panelHeight  = ref(DEF_PANEL)
const scrollbarW   = ref(0)
const startRow     = ref(0)
const visibleCount = ref(30)

/* ── Computed ── */
const dataSource = computed(() => props.data || [])
const isChunked  = computed(() => !!(props.resultSetId && props.loadChunk && props.pipelineId))

const totalRows = computed(() => {
  const n = props.rowsCount
  return (n != null && n >= 0) ? n : dataSource.value.length
})

const panelStyle = computed(() =>
  props.collapsed ? undefined : { height: panelHeight.value + 'px' }
)

// Sentinel holds data rows only (header is outside the scroll container)
const nativeHeight   = computed(() => totalRows.value * ROW_HEIGHT)
const useMapping     = computed(() => nativeHeight.value > MAX_SCROLL)
const sentinelHeight = computed(() => useMapping.value ? MAX_SCROLL : nativeHeight.value)

const visibleRowIndexes = computed(() => {
  const s = Math.max(0, startRow.value - OVERSCAN)
  const e = Math.min(totalRows.value, startRow.value + visibleCount.value + OVERSCAN)
  const a = []
  for (let i = s; i < e; i++) a.push(i)
  return a
})

const tableOffsetY = computed(() => {
  const f = visibleRowIndexes.value.length ? visibleRowIndexes.value[0] : 0
  if (useMapping.value) {
    const st = scrollRef.value ? scrollRef.value.scrollTop : 0
    return st - (startRow.value - f) * ROW_HEIGHT
  }
  return f * ROW_HEIGHT
})

const displayStartRow = computed(() => Math.min(startRow.value + 1, totalRows.value))
const displayEndRow   = computed(() => Math.min(startRow.value + visibleCount.value, totalRows.value))

/* ── Scroll ── */
let raf = null

function onScroll() {
  // Sync header horizontal scroll with body
  if (theadRef.value && scrollRef.value) {
    theadRef.value.scrollLeft = scrollRef.value.scrollLeft
  }
  if (raf) return
  raf = requestAnimationFrame(() => { raf = null; tick() })
}

function tick() {
  const el = scrollRef.value
  if (!el) return
  visibleCount.value = Math.ceil(el.clientHeight / ROW_HEIGHT) + 1

  if (useMapping.value) {
    const mx = sentinelHeight.value - el.clientHeight
    const fr = mx > 0 ? el.scrollTop / mx : 0
    startRow.value = Math.round(fr * Math.max(0, totalRows.value - visibleCount.value))
  } else {
    startRow.value = Math.floor(el.scrollTop / ROW_HEIGHT)
  }

  if (isChunked.value && props.loadChunk) loadVisibleChunks()
}

/* ── Chunks ── */
const _pending = new Set()

function loadVisibleChunks() {
  const idxs  = visibleRowIndexes.value
  const first = idxs[0] ?? 0
  const last  = idxs[idxs.length - 1] ?? 0
  const cs = Math.floor(first / props.chunkSize)
  const ce = Math.floor(last  / props.chunkSize)
  for (let i = cs; i <= ce; i++) enqueueChunk(i)
  // prefetch next chunk
  const nx = ce + 1
  if (nx * props.chunkSize < totalRows.value) enqueueChunk(nx)
}

function enqueueChunk(ci) {
  if (!props.chunks?.[ci] && !chunkLoading(ci) && !_pending.has(ci)) {
    _pending.add(ci)
    props.loadChunk(ci)
  }
}

watch(() => props.chunks, (c) => {
  if (c) for (const k of Object.keys(c)) _pending.delete(+k)
}, { deep: false })

/* ── Cell access ── */
function rowByIndex(i) {
  if (isChunked.value) {
    const ci = Math.floor(i / props.chunkSize)
    const ri = i % props.chunkSize
    const ch = props.chunks?.[ci]
    if (!ch) return { __loading: true }
    return (ri >= 0 && ri < ch.length) ? ch[ri] : {}
  }
  const d = dataSource.value
  return (i >= 0 && i < d.length) ? d[i] : {}
}

function chunkLoading(ci) {
  const s = props.loadingChunkIndexes
  return s instanceof Set ? s.has(ci) : Array.isArray(s) ? s.includes(ci) : false
}

function isRowLoading(i) { return !!rowByIndex(i)?.__loading }

function getRowCell(i, col) {
  const r = rowByIndex(i)
  if (r?.__loading) return ''
  const v = r[col]
  return (v === null || v === undefined) ? '' : v
}

/* ── Navigate ── */
function scrollToRow() {
  const n = goToRowInput.value != null ? Number(goToRowInput.value) : NaN
  if (!Number.isFinite(n) || n < 1 || n > totalRows.value) return
  const t = Math.min(n - 1, totalRows.value - 1)
  const el = scrollRef.value
  if (!el) return
  if (useMapping.value) {
    const maxF = Math.max(1, totalRows.value - visibleCount.value)
    el.scrollTop = Math.round((t / maxF) * (sentinelHeight.value - el.clientHeight))
  } else {
    el.scrollTop = t * ROW_HEIGHT
  }
}

/* ── Resize ── */
let _ry = 0, _rh = 0

function startResize(e) {
  _ry = e.clientY; _rh = panelHeight.value
  document.addEventListener('mousemove', doResize)
  document.addEventListener('mouseup', endResize)
  document.body.style.cursor = 'ns-resize'
  document.body.style.userSelect = 'none'
}
function doResize(e) {
  panelHeight.value = Math.max(MIN_PANEL, Math.min(window.innerHeight * MAX_VH, _rh + _ry - e.clientY))
}
function endResize() {
  document.removeEventListener('mousemove', doResize)
  document.removeEventListener('mouseup', endResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

/* ── Formatting ── */
function formatRowCount(n) {
  if (n == null) return '\u2014'
  if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, '') + ' \u043C\u043B\u0440\u0434'
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + ' \u043C\u043B\u043D'
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + ' \u0442\u044B\u0441'
  return String(n)
}
function formatNumber(n) { return n == null ? '\u2014' : n.toLocaleString('ru-RU') }
function formatRequestTime(ms) {
  if (ms == null) return ''
  return ms >= 1000
    ? (ms / 1000).toFixed(1).replace(/\.0$/, '') + ' \u0441'
    : ms + ' \u043C\u0441'
}

const COL_MIN = 100
const CHAR_W  = 8
function colW(c) { return Math.max(COL_MIN, (c || '').length * CHAR_W + 24) }

/* ── Lifecycle ── */
function measureScrollbar() {
  const el = scrollRef.value
  if (el) scrollbarW.value = el.offsetWidth - el.clientWidth
}

let resizeObs = null

onMounted(() => {
  tick()
  nextTick(measureScrollbar)
  if (scrollRef.value) {
    resizeObs = new ResizeObserver(() => { tick(); measureScrollbar() })
    resizeObs.observe(scrollRef.value)
  }
})

watch(() => props.collapsed, (v) => {
  if (!v) nextTick(() => { tick(); measureScrollbar() })
})

watch(() => props.columns, () => {
  nextTick(() => { tick(); measureScrollbar() })
})

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  resizeObs?.disconnect()
  document.removeEventListener('mousemove', doResize)
  document.removeEventListener('mouseup', endResize)
  _pending.clear()
})
</script>

<style scoped lang="scss">
/* ───── Panel ───── */
.data-preview-panel {
  border-top: 1px solid rgba(0, 0, 0, 0.07);
  background: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.05);
  transition: height 0.2s ease;

  &.collapsed {
    height: 36px !important;
  }
}

/* ───── Resize handle ───── */
.dp-resize {
  height: 7px;
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &:hover .dp-resize__grip {
    background: rgba(0, 0, 0, 0.22);
    width: 48px;
  }
}

.dp-resize__grip {
  width: 36px;
  height: 3px;
  border-radius: 1.5px;
  background: rgba(0, 0, 0, 0.10);
  transition: all 0.15s;
}

/* ───── Header bar ───── */
.dp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.35rem 0.75rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  cursor: pointer;
  flex-shrink: 0;
  user-select: none;

  &:hover {
    background: rgba(0, 0, 0, 0.012);
  }
}

.dp-header__title {
  font-size: 12px;
  font-weight: 600;
  margin: 0;
  color: var(--color-primary-text);
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.dp-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
}

.dp-badge--rows {
  color: var(--color-secondary-text);
}

.dp-badge--time {
  color: var(--color-primary, #2563eb);
  background: rgba(37, 99, 235, 0.06);
}

.dp-header__chevron {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-secondary-text);
  display: flex;
  align-items: center;
  padding: 0.15rem;
  transition: transform 0.2s;

  &.rotated {
    transform: rotate(180deg);
  }
}

/* ───── Empty state ───── */
.dp-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #999;
  font-size: 13px;
  padding: 2rem;
}

/* ───── Fixed table header ───── */
.dp-thead {
  flex-shrink: 0;
  overflow: hidden;
  border-bottom: 2px solid rgba(0, 0, 0, 0.07);
  background: #f6f7f9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

/* ───── Scrollable body ───── */
.dp-body {
  flex: 1;
  min-height: 0;
  overflow-y: scroll;
  overflow-x: auto;

  &::-webkit-scrollbar {
    width: 7px;
    height: 7px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.13);
    border-radius: 4px;

    &:hover {
      background: rgba(0, 0, 0, 0.22);
    }
  }

  &::-webkit-scrollbar-corner {
    background: transparent;
  }
}

/* ───── Table (shared by header + body) ───── */
.dp-table {
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 12px;
  min-width: 100%;

  th,
  td {
    padding: 0 0.6rem;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    height: 32px;
    line-height: 32px;
    box-sizing: border-box;
  }

  th {
    font-weight: 600;
    font-size: 11px;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 0.025em;
    background: #f6f7f9;
  }

  td {
    border-bottom: 1px solid rgba(0, 0, 0, 0.04);
    color: var(--color-primary-text);
    font-variant-numeric: tabular-nums;
  }

  /* Row-number column */
  .dp-col-rn {
    width: 52px;
    min-width: 52px;
  }

  .dp-cell-rn {
    width: 52px;
    min-width: 52px;
    max-width: 52px;
    text-align: right;
    color: #b0b0b0;
    font-size: 10px;
    font-weight: 400;
    background: #fafbfc;
    border-right: 1px solid rgba(0, 0, 0, 0.05);
    user-select: none;
    position: sticky;
    left: 0;
    z-index: 1;
  }

  th.dp-cell-rn {
    z-index: 2;
    background: #eff0f3;
    color: #999;
  }

  /* Zebra striping */
  .dp-row--even td {
    background: rgba(0, 0, 0, 0.012);
  }

  .dp-row--even .dp-cell-rn {
    background: #f5f6f8;
  }

  /* Hover */
  tbody tr:hover td {
    background: rgba(37, 99, 235, 0.035);
  }

  tbody tr:hover .dp-cell-rn {
    background: rgba(37, 99, 235, 0.06);
    color: var(--color-primary, #2563eb);
  }
}

/* ───── Skeleton loading ───── */
.dp-skeleton {
  display: inline-block;
  width: 55%;
  height: 11px;
  border-radius: 3px;
  background: linear-gradient(
    90deg,
    rgba(0, 0, 0, 0.05) 25%,
    rgba(0, 0, 0, 0.09) 50%,
    rgba(0, 0, 0, 0.05) 75%
  );
  background-size: 200% 100%;
  animation: dp-shimmer 1.4s ease-in-out infinite;
  vertical-align: middle;
}

@keyframes dp-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ───── Status bar ───── */
.dp-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.2rem 0.75rem;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: #fafbfc;
  flex-shrink: 0;
  font-size: 11px;
  color: #888;
  font-variant-numeric: tabular-nums;
}

.dp-status__pos {
  white-space: nowrap;
}

.dp-status__goto {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  white-space: nowrap;
}

.dp-status__input {
  width: 5.5rem;
  padding: 0.12rem 0.3rem;
  font-size: 11px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 3px;
  background: #fff;
  font-variant-numeric: tabular-nums;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:focus {
    border-color: var(--color-primary, #2563eb);
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.08);
  }
}

.dp-status__btn {
  padding: 0.12rem 0.45rem;
  font-size: 11px;
  font-weight: 500;
  background: var(--color-primary, #2563eb);
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: opacity 0.15s;

  &:hover {
    opacity: 0.85;
  }
}
</style>
