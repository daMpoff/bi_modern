<template>
  <div class="chart-area">
    <v-chart
      v-if="chartOption"
      :option="chartOption"
      :update-options="{ notMerge: true, lazyUpdate: true }"
      autoresize
      class="chart-component"
    />
  </div>
</template>

<script setup>
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  DataZoomInsideComponent,
  DataZoomSliderComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useChartData } from '@/modules/bi_analysis_modern/client/src/js/useChartData.js'

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  DataZoomInsideComponent,
  DataZoomSliderComponent
])

const props = defineProps({
  block: { type: Object, required: true },
  chartData: { type: Array, default: null }
})

const { chartOption } = useChartData(props, 'area', { smooth: true })
</script>

<style scoped lang="scss">
.chart-area {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.chart-component {
  width: 100%;
  height: 100%;
  min-height: 200px;
}
</style>
