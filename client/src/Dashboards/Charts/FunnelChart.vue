<template>
  <div class="chart-funnel">
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
import { FunnelChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  FunnelChart,
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

const syntheticData = [
  { value: 100, name: 'Этап 1' },
  { value: 80, name: 'Этап 2' },
  { value: 60, name: 'Этап 3' },
  { value: 40, name: 'Этап 4' },
  { value: 20, name: 'Этап 5' }
]

const chartOption = computed(() => ({
  title: {
    text: 'Воронка',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item',
    formatter: '{a} <br/>{b} : {c}%'
  },
  legend: {
    data: ['Значения'],
    bottom: 0
  },
  series: [{
    name: 'Воронка',
    type: 'funnel',
    left: '10%',
    top: 60,
    bottom: 60,
    width: '80%',
    min: 0,
    max: 100,
    minSize: '0%',
    maxSize: '100%',
    sort: 'descending',
    gap: 2,
    label: {
      show: true,
      position: 'inside'
    },
    labelLine: {
      length: 10,
      lineStyle: {
        width: 1,
        type: 'solid'
      }
    },
    itemStyle: {
      borderColor: '#fff',
      borderWidth: 1
    },
    emphasis: {
      label: {
        fontSize: 20
      }
    },
    data: syntheticData
  }]
}))
</script>

<style scoped lang="scss">
.chart-funnel {
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
