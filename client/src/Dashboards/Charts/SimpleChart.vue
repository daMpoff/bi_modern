<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import '../../charts/echartsSimpleCharts.js'
import { resolveSimpleChartType, buildSimpleChartOption } from './simpleChartOptions.js'

const props = defineProps({
  block: { type: Object, required: true },
  chartData: { type: Array, default: null }
})

const chartType = computed(() => resolveSimpleChartType(props.block?.config?.chartType))
const chartOption = computed(() => buildSimpleChartOption(props.block?.config || {}, props.chartData, chartType.value))
</script>

<template>
  <div class="simple-chart" :class="'chart-' + chartType">
    <VChart
      v-if="chartOption"
      :option="chartOption"
      :update-options="{ notMerge: true, lazyUpdate: true }"
      autoresize
      class="chart-component"
    />
  </div>
</template>

<style scoped>
.simple-chart,
.chart-component {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
