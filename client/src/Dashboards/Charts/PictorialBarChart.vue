<template>
  <div class="chart-pictorial-bar">
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
import { PictorialBarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  PictorialBarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = {
  categories: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн'],
  data: [45, 52, 38, 67, 55, 72]
}

const chartOption = computed(() => ({
  title: {
    text: 'Изобразительный бар',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' }
  },
  legend: {
    data: ['Значения'],
    bottom: 0
  },
  grid: {
    left: '5%',
    right: '5%',
    bottom: '15%',
    top: '15%'
  },
  xAxis: {
    type: 'category',
    data: syntheticData.categories
  },
  yAxis: {
    type: 'value'
  },
  series: [{
    name: 'Значения',
    type: 'pictorialBar',
    data: syntheticData.data,
    symbol: 'rect',
    symbolRepeat: true,
    symbolSize: [20, 4],
    itemStyle: {
      color: '#3b82f6'
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-pictorial-bar {
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
