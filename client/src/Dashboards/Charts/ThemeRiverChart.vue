<template>
  <div class="chart-theme-river">
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
import { ThemeRiverChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  ThemeRiverChart,
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
  ['2024-01-01', 10, 'Категория 1'],
  ['2024-01-02', 15, 'Категория 1'],
  ['2024-01-03', 20, 'Категория 1'],
  ['2024-01-01', 5, 'Категория 2'],
  ['2024-01-02', 8, 'Категория 2'],
  ['2024-01-03', 12, 'Категория 2']
]

const chartOption = computed(() => ({
  title: {
    text: 'Река тем',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'line',
      lineStyle: {
        color: 'rgba(0,0,0,0.2)'
      }
    }
  },
  legend: {
    data: ['Категория 1', 'Категория 2'],
    bottom: 0
  },
  singleAxis: {
    top: 50,
    bottom: 50,
    axisTick: {},
    axisLabel: {},
    type: 'time',
    axisPointer: {
      animation: true,
      label: {
        show: true
      }
    },
    splitLine: {
      show: true,
      lineStyle: {
        type: 'dashed',
        opacity: 0.2
      }
    }
  },
  series: [{
    type: 'themeRiver',
    itemStyle: {
      borderWidth: 1,
      borderColor: '#aaa'
    },
    label: {
      show: false,
      fontSize: 12,
      fontWeight: 'bold'
    },
    data: syntheticData
  }]
}))
</script>

<style scoped lang="scss">
.chart-theme-river {
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
