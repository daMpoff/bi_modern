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

const UPLOT_THRESHOLD = 50_000
const UPlotChart = defineAsyncComponent(() => import('./UPlotChart.vue'))
const SimpleChart = defineAsyncComponent(() => import('./SimpleChart.vue'))

const specializedCharts = {
  radar: defineAsyncComponent(() => import('./RadarChart.vue')),
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

const chartComponent = computed(() => {
  const type = props.block?.config?.chartType
  if ((type === 'line' || type === 'area') && props.chartData?.length > UPLOT_THRESHOLD) {
    return UPlotChart
  }
  return Object.hasOwn(specializedCharts, type) ? specializedCharts[type] : SimpleChart
})
</script>
