<template>
  <div class="chart-parallel">
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
import { ParallelChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  ParallelComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  ParallelChart,
  TitleComponent,
  TooltipComponent,
  ParallelComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = [
  [1, 91, 45, 125, 0.82, 34],
  [2, 65, 27, 78, 0.86, 45],
  [3, 83, 60, 84, 1.09, 73],
  [4, 109, 81, 121, 1.14, 68],
  [5, 106, 77, 114, 1.26, 92]
]

const chartOption = computed(() => ({
  title: {
    text: 'Параллельные координаты',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {},
  parallelAxis: [
    { dim: 0, name: 'Параметр 1' },
    { dim: 1, name: 'Параметр 2' },
    { dim: 2, name: 'Параметр 3' },
    { dim: 3, name: 'Параметр 4' },
    { dim: 4, name: 'Параметр 5' },
    { dim: 5, name: 'Параметр 6' }
  ],
  series: [{
    type: 'parallel',
    lineStyle: {
      width: 4
    },
    data: syntheticData
  }]
}))
</script>

<style scoped lang="scss">
.chart-parallel {
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
