<template>
  <div class="chart-boxplot">
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
import { BoxplotChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  BoxplotChart,
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
  [850, 740, 900, 1070, 930, 850, 950, 980, 980, 880, 1000, 980],
  [960, 940, 960, 940, 880, 880, 880, 860, 920, 920, 880, 900],
  [880, 880, 880, 860, 920, 920, 880, 900, 960, 940, 960, 940]
]

const chartOption = computed(() => ({
  title: {
    text: 'Ящик с усами',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item',
    axisPointer: {
      type: 'shadow'
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
    data: ['Категория 1', 'Категория 2', 'Категория 3'],
    boundaryGap: true,
    nameGap: 30,
    splitArea: {
      show: false
    },
    splitLine: {
      show: false
    }
  },
  yAxis: {
    type: 'value',
    name: 'Значение',
    splitArea: {
      show: true
    }
  },
  series: [{
    name: 'boxplot',
    type: 'boxplot',
    data: syntheticData,
    itemStyle: {
      color: '#3b82f6',
      borderColor: '#1e40af'
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-boxplot {
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
