<template>
  <div class="chart-candlestick">
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
import { computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  CandlestickChart,
  TitleComponent,
  TooltipComponent,
  GridComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = [
  [20, 34, 10, 38],
  [40, 35, 30, 50],
  [31, 38, 33, 44],
  [38, 15, 5, 16],
  [50, 30, 20, 35],
  [60, 70, 55, 75]
]

const chartOption = computed(() => ({
  title: {
    text: 'Свечной график',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross'
    }
  },
  grid: {
    left: '5%',
    right: '5%',
    bottom: '15%',
    top: '15%'
  },
  xAxis: {
    type: 'category',
    data: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн'],
    boundaryGap: false,
    axisLine: { onZero: false }
  },
  yAxis: {
    scale: true,
    splitArea: {
      show: true
    }
  },
  series: [{
    name: 'Свечи',
    type: 'candlestick',
    data: syntheticData,
    itemStyle: {
      color: '#26a69a',
      color0: '#ef5350',
      borderColor: '#26a69a',
      borderColor0: '#ef5350'
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-candlestick {
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
