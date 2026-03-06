<template>
  <div class="chart-radar">
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
import { RadarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  RadarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const chartOption = computed(() => ({
  title: {
    text: 'Радарный график',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {},
  legend: {
    data: ['Значения'],
    bottom: 0
  },
  radar: {
    indicator: [
      { name: 'Янв', max: 100 },
      { name: 'Фев', max: 100 },
      { name: 'Мар', max: 100 },
      { name: 'Апр', max: 100 },
      { name: 'Май', max: 100 },
      { name: 'Июн', max: 100 }
    ]
  },
  series: [{
    name: 'Значения',
    type: 'radar',
    data: [{
      value: [45, 52, 38, 67, 55, 72],
      name: 'Значения',
      itemStyle: { color: '#3b82f6' }
    }]
  }]
}))
</script>

<style scoped lang="scss">
.chart-radar {
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
