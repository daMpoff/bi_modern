<template>
  <div class="chart-sunburst">
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
import { SunburstChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  SunburstChart,
  TitleComponent,
  TooltipComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = {
  name: 'Корень',
  children: [
    {
      name: 'Уровень 1',
      children: [
        { name: 'Элемент 1.1', value: 10 },
        { name: 'Элемент 1.2', value: 20 }
      ]
    },
    {
      name: 'Уровень 2',
      children: [
        { name: 'Элемент 2.1', value: 15 },
        { name: 'Элемент 2.2', value: 25 }
      ]
    }
  ]
}

const chartOption = computed(() => ({
  title: {
    text: 'Солнечная диаграмма',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item'
  },
  series: [{
    type: 'sunburst',
    data: [syntheticData],
    radius: [0, '90%'],
    label: {
      rotate: 'radial'
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-sunburst {
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
