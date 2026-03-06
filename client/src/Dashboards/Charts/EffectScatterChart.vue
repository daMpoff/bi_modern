<template>
  <div class="chart-effect-scatter">
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
import { EffectScatterChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  GeoComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  EffectScatterChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  GeoComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = [
  [120, 32, 100],
  [121, 31, 200],
  [104, 30, 150],
  [113, 28, 80],
  [108, 34, 120]
]

const chartOption = computed(() => ({
  title: {
    text: 'Эффект рассеяния',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item'
  },
  grid: {
    left: '5%',
    right: '5%',
    bottom: '15%',
    top: '15%'
  },
  xAxis: {
    type: 'value',
    scale: true
  },
  yAxis: {
    type: 'value',
    scale: true
  },
  series: [{
    name: 'Значения',
    type: 'effectScatter',
    data: syntheticData,
    symbolSize: (data) => Math.sqrt(data[2]) / 5,
    showEffectOn: 'render',
    rippleEffect: {
      brushType: 'stroke'
    },
    itemStyle: {
      color: '#3b82f6',
      shadowBlur: 10,
      shadowColor: '#93c5fd'
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-effect-scatter {
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
