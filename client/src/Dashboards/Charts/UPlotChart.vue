<template>
  <div ref="containerRef" class="uplot-chart-container" />
</template>

<script setup>
/**
 * UPlotChart — lightweight time-series chart powered by uPlot.
 *
 * Used automatically by ChartRouter when:
 *   - chartType is "line" or "area"
 *   - dataLength > UPLOT_THRESHOLD (50 000 rows)
 *
 * Props API is compatible with the rest of the ECharts-based chart components
 * so ChartRouter can swap them transparently.
 */
import { ref, watch, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import { resolveBlockChartConfig } from '@/modules/bi_analysis_modern/client/src/js/chartConfigUtils.js'

const props = defineProps({
  block: { type: Object, required: true },
  chartData: { type: Array, default: null }
})

const containerRef = ref(null)
let chart = null

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PALETTE = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de',
  '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f'
]

function resolveConfig() {
  const c = props.block?.config
  if (!c) return { xField: '', yFields: [] }
  const r = resolveBlockChartConfig(c)
  return { xField: r.xField || '', yFields: r.yFields || [] }
}

function buildUPlotData(rows) {
  if (!rows?.length) return null
  const { xField, yFields } = resolveConfig()
  const keys = Object.keys(rows[0] || {})
  if (!keys.length) return null

  const xKey = (xField && keys.includes(xField)) ? xField : keys[0]
  let valueKeys = yFields.filter(f => keys.includes(f))
  if (!valueKeys.length) valueKeys = keys.filter(k => k !== xKey)
  if (!valueKeys.length) return null

  // X axis: attempt to parse as timestamps (epoch seconds) or sequential index
  const xRaw = rows.map(r => r[xKey])
  let xArr
  const firstX = xRaw[0]
  if (typeof firstX === 'number') {
    // If numbers are likely epoch ms (>1e12) convert to seconds
    xArr = firstX > 1e12
      ? Float64Array.from(xRaw, v => (Number(v) || 0) / 1000)
      : Float64Array.from(xRaw, v => Number(v) || 0)
  } else {
    // Try parsing dates
    const ts = Date.parse(firstX)
    if (!Number.isNaN(ts)) {
      xArr = Float64Array.from(xRaw, v => {
        const d = Date.parse(v)
        return Number.isNaN(d) ? 0 : d / 1000
      })
    } else {
      // Sequential index fallback
      xArr = Float64Array.from({ length: rows.length }, (_, i) => i)
    }
  }

  const series = valueKeys.map(k =>
    Float64Array.from(rows, r => {
      const v = r[k]
      return typeof v === 'number' ? v : Number(v) || 0
    })
  )

  return { data: [xArr, ...series], labels: valueKeys }
}

// ---------------------------------------------------------------------------
// Render
// ---------------------------------------------------------------------------

function createChart() {
  if (!containerRef.value) return
  destroyChart()

  const parsed = buildUPlotData(props.chartData)
  if (!parsed) return

  const { data, labels } = parsed
  const isArea = (props.block?.config?.chartType || '').includes('area')

  const seriesOpts = [
    { label: 'X' }, // x-axis placeholder
    ...labels.map((label, i) => ({
      label,
      stroke: PALETTE[i % PALETTE.length],
      width: 1.5,
      fill: isArea ? (PALETTE[i % PALETTE.length] + '30') : undefined
    }))
  ]

  const width = containerRef.value.clientWidth || 400
  const height = containerRef.value.clientHeight || 300

  const opts = {
    width,
    height,
    cursor: { show: true, drag: { x: true, y: false } },
    scales: { x: { time: true } },
    axes: [
      { stroke: '#888', grid: { stroke: '#eee' } },
      { stroke: '#888', grid: { stroke: '#eee' } }
    ],
    series: seriesOpts,
    legend: { show: labels.length > 1 }
  }

  chart = new uPlot(opts, data, containerRef.value)
}

function destroyChart() {
  if (chart) {
    chart.destroy()
    chart = null
  }
}

function handleResize() {
  if (!chart || !containerRef.value) return
  const w = containerRef.value.clientWidth || 400
  const h = containerRef.value.clientHeight || 300
  chart.setSize({ width: w, height: h })
}

let resizeObs = null

onMounted(() => {
  nextTick(() => createChart())
  if (typeof ResizeObserver !== 'undefined' && containerRef.value) {
    resizeObs = new ResizeObserver(() => handleResize())
    resizeObs.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  destroyChart()
  if (resizeObs) { resizeObs.disconnect(); resizeObs = null }
})

watch(() => props.chartData, () => nextTick(() => createChart()), { deep: true })
watch(() => props.block?.config, () => nextTick(() => createChart()), { deep: true })

// Expose for export
function getChartDataURL() {
  const canvas = containerRef.value?.querySelector('canvas')
  return canvas?.toDataURL('image/png') ?? null
}
defineExpose({ getChartDataURL })
</script>

<style scoped>
.uplot-chart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
  position: relative;
}
.uplot-chart-container :deep(.u-wrap) {
  width: 100% !important;
}
</style>
