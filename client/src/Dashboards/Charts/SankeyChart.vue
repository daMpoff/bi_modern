<template>
  <div class="chart-sankey">
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
import { SankeyChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  SankeyChart,
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
    { name: 'Узел 1' },
    { name: 'Узел 2' },
    { name: 'Узел 3' },
    { name: 'Узел 4' },
    { name: 'Узел 5' }
  ],
  links: [
    { source: 'Узел 1', target: 'Узел 2', value: 10 },
    { source: 'Узел 1', target: 'Узел 3', value: 15 },
    { source: 'Узел 2', target: 'Узел 4', value: 20 },
    { source: 'Узел 3', target: 'Узел 5', value: 25 }
  ]
}

const chartOption = computed(() => ({
  title: {
    text: 'Диаграмма Санкей',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item',
    triggerOn: 'mousemove'
  },
  series: [{
    type: 'sankey',
    data: syntheticData.nodes,
    links: syntheticData.links,
    emphasis: {
      focus: 'adjacency'
    },
    lineStyle: {
      color: 'gradient',
      curveness: 0.5
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-sankey {
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
