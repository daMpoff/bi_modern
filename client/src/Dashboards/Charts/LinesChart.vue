<template>
  <div class="chart-lines">
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
import { LinesChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  GeoComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  LinesChart,
  TitleComponent,
  TooltipComponent,
  GeoComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

const syntheticData = [
  {
    coords: [
      [116.7, 39.53],
      [121.48, 31.22]
    ],
    lineStyle: {
      color: '#3b82f6'
    }
  },
  {
    coords: [
      [104.06, 30.67],
      [120.15, 30.27]
    ],
    lineStyle: {
      color: '#10b981'
    }
  }
]

const chartOption = computed(() => ({
  title: {
    text: 'Линии на карте',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'item'
  },
  geo: {
    map: 'world',
    roam: true,
    itemStyle: {
      areaColor: '#f3f4f6',
      borderColor: '#e5e7eb'
    },
    emphasis: {
      itemStyle: {
        areaColor: '#dbeafe'
      }
    }
  },
  series: [{
    type: 'lines',
    coordinateSystem: 'geo',
    data: syntheticData,
    lineStyle: {
      width: 2,
      curveness: 0.3
    }
  }]
}))
</script>

<style scoped lang="scss">
.chart-lines {
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
