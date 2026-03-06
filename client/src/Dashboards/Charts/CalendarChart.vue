<template>
  <div class="chart-calendar">
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
import { HeatmapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  CalendarComponent,
  VisualMapComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([
  CanvasRenderer,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  CalendarComponent,
  VisualMapComponent
])

const props = defineProps({
  block: {
    type: Object,
    required: true
  }
})

// Генерируем данные для календаря
function generateCalendarData() {
  const data = []
  const startDate = new Date('2024-01-01')
  const endDate = new Date('2024-01-31')
  
  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split('T')[0]
    data.push([
      dateStr,
      Math.floor(Math.random() * 100)
    ])
  }
  
  return data
}

const syntheticData = generateCalendarData()

const chartOption = computed(() => ({
  title: {
    text: 'Календарь',
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  },
  tooltip: {
    position: 'top',
    formatter: (p) => {
      const format = (time) => {
        return time.getFullYear() + '-' + (time.getMonth() + 1) + '-' + time.getDate()
      }
      return format(new Date(p.data[0])) + '<br/>' + p.data[1]
    }
  },
  visualMap: {
    min: 0,
    max: 100,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: '5%',
    inRange: {
      color: ['#e0f2fe', '#0ea5e9']
    }
  },
  calendar: {
    top: 60,
    left: 30,
    right: 30,
    cellSize: ['auto', 13],
    range: '2024-01',
    itemStyle: {
      borderWidth: 0.5
    },
    yearLabel: { show: false }
  },
  series: [{
    type: 'heatmap',
    coordinateSystem: 'calendar',
    data: syntheticData
  }]
}))
</script>

<style scoped lang="scss">
.chart-calendar {
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
