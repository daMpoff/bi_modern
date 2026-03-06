<script setup>
import { ref, computed, inject, watch } from 'vue'
import '@/modules/bi_analysis_modern/client/src/js/echartsSimpleCharts.js'
import VChart from 'vue-echarts'

const props = defineProps({
  option: { type: Object, default: null },
  autoresize: { type: Boolean, default: true },
  /** Use notMerge for option updates — avoids stale series when data changes drastically */
  notMerge: { type: Boolean, default: true },
  /** Delay internal ECharts update until idle — reduces jank on rapid option changes */
  lazyUpdate: { type: Boolean, default: true }
})

const chartRef = ref(null)
const dashboardExportCapturing = inject('dashboardExportCapturing', ref(false))

// Use the normal device pixel ratio (do NOT change on export — html2canvas
// already handles scale via its own `scale` parameter).  Previously the
// component was re-keyed on export which caused a full destroy/recreate
// cycle and visible chart flickering.
const DEFAULT_DPR = typeof window !== 'undefined' ? window.devicePixelRatio || 2 : 2
const chartInitOpts = { devicePixelRatio: DEFAULT_DPR }

const DEFAULT_EXPORT_OPTS = {
  type: 'png',
  pixelRatio: 3,
  backgroundColor: '#fff'
}

function getDataURL(opts = {}) {
  const v = chartRef.value
  if (!v) return null
  const ec = typeof v.getEchartsInstance === 'function' ? v.getEchartsInstance() : (v.echartsInstance ?? v)
  if (ec && typeof ec.getDataURL === 'function') {
    return ec.getDataURL({ ...DEFAULT_EXPORT_OPTS, ...opts })
  }
  return null
}

/**
 * Returns the underlying ECharts instance for advanced operations
 * (e.g. appendData, dispatchAction, dispose).
 */
function getEchartsInstance() {
  const v = chartRef.value
  if (!v) return null
  return typeof v.getEchartsInstance === 'function' ? v.getEchartsInstance() : (v.echartsInstance ?? v)
}

defineExpose({ getDataURL, getEchartsInstance })
</script>

<template>
  <VChart
    ref="chartRef"
    v-bind="$attrs"
    :option="option"
    :autoresize="autoresize"
    :init-options="chartInitOpts"
    :update-options="{ notMerge, lazyUpdate }"
  />
</template>
