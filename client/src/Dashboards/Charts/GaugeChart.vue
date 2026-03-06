<template>
  <div class="chart-gauge">
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
import { GaugeChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  GaugeChart,
  TitleComponent,
  TooltipComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const chartOption = computed(() => ({
  title: {
    text: 'Измерительный график',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    formatter: '{a} <br/>{b} : {c}%'
  },
  series: [{
    name: 'Значение',
    type: 'gauge',
    progress: {
      show: true
    },
    detail: {
      valueAnimation: true,
      formatter: '{value}%'
    },
    data: [{
      value: 65,
      name: 'Показатель'
    }]
  }]
}))
</script>

<style scoped lang="scss">
.chart-gauge {
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
