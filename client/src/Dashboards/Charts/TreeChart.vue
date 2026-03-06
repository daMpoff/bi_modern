<template>
  <div class="chart-tree">
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
import { TreeChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  TreeChart,
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
      name: 'Ветвь 1',
      children: [
        { name: 'Лист 1.1', value: 10 },
        { name: 'Лист 1.2', value: 20 }
      ]
    },
    {
      name: 'Ветвь 2',
      children: [
        { name: 'Лист 2.1', value: 15 },
        { name: 'Лист 2.2', value: 25 }
      ]
    }
  ]
}

const chartOption = computed(() => ({
  title: {
    text: 'Дерево',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item',
    triggerOn: 'mousemove'
  },
  series: [{
    type: 'tree',
    data: [syntheticData],
    top: '10%',
    left: '7%',
    bottom: '10%',
    right: '20%',
    symbolSize: 7,
    label: {
      position: 'left',
      verticalAlign: 'middle',
      align: 'right'
    },
    leaves: {
      label: {
        position: 'right',
        verticalAlign: 'middle',
        align: 'left'
      }
    },
    emphasis: {
      focus: 'descendant'
    },
    expandAndCollapse: true,
    animationDuration: 550,
    animationDurationUpdate: 750
  }]
}))
</script>

<style scoped lang="scss">
.chart-tree {
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
