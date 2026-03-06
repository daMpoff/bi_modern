<template>
  <div class="chart-treemap">
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
import { TreemapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  TreemapChart,
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
  name: 'root',
  children: [
    { name: 'Категория 1', value: 100 },
    { name: 'Категория 2', value: 80 },
    { name: 'Категория 3', value: 60 },
    { name: 'Категория 4', value: 40 },
    { name: 'Категория 5', value: 20 }
  ]
}

const chartOption = computed(() => ({
  title: {
    text: 'Древовидная карта',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c}'
  },
  series: [{
    name: 'Данные',
    type: 'treemap',
    data: [syntheticData],
    roam: false,
    nodeClick: false,
    breadcrumb: {
      show: false
    },
    label: {
      show: true,
      formatter: '{b}'
    },
    upperLabel: {
      show: true,
      height: 30
    },
    itemStyle: {
      borderColor: '#fff'
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-treemap {
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
