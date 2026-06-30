<template>
  <ModalCenter
    modal-id="chartFocusModal"
    standalone
    :visible="show"
    :dialog-style="{ width: '100%', maxWidth: '1200px', height: '85vh', maxHeight: '900px' }"
    :z-index="1060"
    :close-on-esc="false"
    body-class="p-0"
    @close="handleClose"
  >
    <template #title>
      <span>{{ focusTitle }}</span>
      <div class="chart-focus-header-actions ms-auto">
        <ChartExportDropdown
          :export-api="focusExportApi"
          :chart-title="focusTitle"
        />
      </div>
    </template>

    <div class="chart-focus-body">
      <DashboardBlockChartPreview v-if="block" ref="previewRef" :block="block" />
    </div>
  </ModalCenter>
</template>

<script setup>
import { computed, ref } from 'vue'
import DashboardBlockChartPreview from './DashboardBlockChartPreview.vue'
import ChartExportDropdown from './ChartExportDropdown.vue'
import ModalCenter from '@/components/ModalCenter.vue'

const previewRef = ref(null)

const focusExportApi = computed(() => ({
  getChartDataURL: () => previewRef.value?.getChartDataURL?.() ?? null,
  getChartData: () => previewRef.value?.getChartData?.() ?? []
}))

const props = defineProps({
  show: { type: Boolean, default: false },
  block: { type: Object, default: null }
})

const emit = defineEmits(['close'])

const focusTitle = computed(() => {
  if (!props.block) return 'График'
  return props.block?.config?.title || props.block?.type || 'График'
})

function handleClose() {
  emit('close')
}
</script>

<style scoped lang="scss">
.chart-focus-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chart-focus-body {
  height: 100%;
  min-height: 0;
  overflow: auto;
}
</style>
