<template>
  <component :is="chartComponent" :block="block" :chart-data="chartData" />
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'

const props = defineProps({
  block: {
    type: Object,
    required: true
  },
  chartData: {
    type: Array,
    default: null
  }
})

// ---------------------------------------------------------------------------
// Smart engine selection (Phase 5)
// When data length exceeds UPLOT_THRESHOLD and the chart type is time-series
// compatible (line / area), we swap to the lightweight uPlot renderer which
// can handle millions of points at 60 fps.
// ---------------------------------------------------------------------------
const UPLOT_THRESHOLD = 50_000

const useUPlot = computed(() => {
  const type = props.block?.config?.chartType
  const dataLen = props.chartData?.length ?? 0
  const isTimeSeries = type === 'line' || type === 'area'
  return isTimeSeries && dataLen > UPLOT_THRESHOLD
})

// Маппинг типов графиков на компоненты (ECharts-based)
const chartComponents = {
  line: defineAsyncComponent(() => import('./LineChart.vue')),
  bar: defineAsyncComponent(() => import('./BarChart.vue')),
  pie: defineAsyncComponent(() => import('./PieChart.vue')),
  doughnut: defineAsyncComponent(() => import('./DoughnutChart.vue')),
  scatter: defineAsyncComponent(() => import('./ScatterChart.vue')),
  radar: defineAsyncComponent(() => import('./RadarChart.vue')),
  heatmap: defineAsyncComponent(() => import('./HeatmapChart.vue')),
  area: defineAsyncComponent(() => import('./AreaChart.vue')),
  candlestick: defineAsyncComponent(() => import('./CandlestickChart.vue')),
  gauge: defineAsyncComponent(() => import('./GaugeChart.vue')),
  funnel: defineAsyncComponent(() => import('./FunnelChart.vue')),
  tree: defineAsyncComponent(() => import('./TreeChart.vue')),
  treemap: defineAsyncComponent(() => import('./TreemapChart.vue')),
  sunburst: defineAsyncComponent(() => import('./SunburstChart.vue')),
  parallel: defineAsyncComponent(() => import('./ParallelChart.vue')),
  sankey: defineAsyncComponent(() => import('./SankeyChart.vue')),
  graph: defineAsyncComponent(() => import('./GraphChart.vue')),
  boxplot: defineAsyncComponent(() => import('./BoxplotChart.vue')),
  map: defineAsyncComponent(() => import('./MapChart.vue')),
  lines: defineAsyncComponent(() => import('./LinesChart.vue')),
  effectScatter: defineAsyncComponent(() => import('./EffectScatterChart.vue')),
  pictorialBar: defineAsyncComponent(() => import('./PictorialBarChart.vue')),
  themeRiver: defineAsyncComponent(() => import('./ThemeRiverChart.vue')),
  calendar: defineAsyncComponent(() => import('./CalendarChart.vue'))
}

// uPlot component — lazy loaded only when needed
const UPlotChartComponent = defineAsyncComponent(() => import('./UPlotChart.vue'))

// Выбор компонента на основе chartType + smart engine selection
const chartComponent = computed(() => {
  if (useUPlot.value) return UPlotChartComponent

  const chartType = props.block?.config?.chartType || 'bar'
  return chartComponents[chartType] || chartComponents.bar
})
</script>
