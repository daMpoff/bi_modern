<script setup>
import { computed, ref } from 'vue'
import BiEchartsChart from '@/modules/bi_analysis_modern/client/src/components/BiEchartsChart.vue'
import { buildEchartsOption } from '@/modules/bi_analysis_modern/client/src/js/buildEchartsOption.js'
import { normalizeChartConfig } from '@/modules/bi_analysis_modern/client/src/js/chartConfigUtils.js'

const props = defineProps({
  chartData: { type: Array, default: () => [] },
  chartConfig: { type: Object, default: () => ({}) },
  chartType: { type: String, default: 'bar' },
  engine: { type: String, default: 'echarts' }
})

const chartRef = ref(null)

function getChartDataURL() {
  return chartRef.value?.getDataURL?.() ?? null
}

defineExpose({ getChartDataURL })

const echartsOption = computed(() => {
  const config = props.chartConfig || {}
  const { xField, yFields, colorField } = normalizeChartConfig(config)
  const opts = props.chartType === 'heatmap' && colorField ? { colorField } : {}
  const result = buildEchartsOption(
    props.chartData,
    props.chartType,
    xField,
    yFields,
    null,
    opts
  )
  return result
})
</script>

<template>
  <div class="pipeline-chart-renderer">
    <BiEchartsChart
      v-if="echartsOption"
      ref="chartRef"
      :option="echartsOption"
      style="width: 100%; height: 100%;"
    />
    <div v-else class="chart-empty">Нет данных для отображения</div>
  </div>
</template>

<style scoped>
.pipeline-chart-renderer {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--color-text-secondary, #999);
  font-size: 14px;
}
</style>
