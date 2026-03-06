<template>
  <div class="chart-map">
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
import { MapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  GeoComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  MapChart,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
  GeoComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = [
  { name: 'Регион 1', value: 100 },
  { name: 'Регион 2', value: 200 },
  { name: 'Регион 3', value: 150 },
  { name: 'Регион 4', value: 80 },
  { name: 'Регион 5', value: 120 }
]

const chartOption = computed(() => ({
  title: {
    text: 'Карта',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item'
  },
  visualMap: {
    min: 0,
    max: 200,
    left: 'left',
    top: 'bottom',
    text: ['Высокий', 'Низкий'],
    calculable: true,
    inRange: {
      color: ['#e0f2fe', '#0ea5e9']
    }
  },
  series: [{
    name: 'Данные',
    type: 'map',
    map: 'world',
    roam: true,
    emphasis: {
      label: {
        show: true
      }
    },
    data: syntheticData
  }]
}))
</script>

<style scoped lang="scss">
.chart-map {
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
