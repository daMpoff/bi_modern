<template>
  <div class="chart-graph">
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
import { GraphChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  GraphChart,
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
  nodes: [
    { id: '1', name: 'Узел 1', symbolSize: 30 },
    { id: '2', name: 'Узел 2', symbolSize: 20 },
    { id: '3', name: 'Узел 3', symbolSize: 25 },
    { id: '4', name: 'Узел 4', symbolSize: 15 }
  ],
  links: [
    { source: '1', target: '2' },
    { source: '1', target: '3' },
    { source: '2', target: '4' },
    { source: '3', target: '4' }
  ]
}

const chartOption = computed(() => ({
  title: {
    text: 'Граф',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {},
  series: [{
    type: 'graph',
    layout: 'force',
    data: syntheticData.nodes,
    links: syntheticData.links,
    roam: true,
    label: {
      show: true,
      position: 'right'
    },
    force: {
      repulsion: 100
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-graph {
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
