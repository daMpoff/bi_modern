<template>
  <Teleport to="body">
    <div
      v-if="show"
      class="chart-focus-overlay"
      @click.self="handleClose"
    >
      <div class="chart-focus-modal" @click.stop>
        <div class="chart-focus-header">
          <h2 class="chart-focus-title">{{ focusTitle }}</h2>
          <div class="chart-focus-header-actions">
            <ChartExportDropdown
              :export-api="focusExportApi"
              :chart-title="focusTitle"
            />
            <button
              type="button"
              class="chart-focus-close"
              aria-label="Закрыть"
              @click="handleClose"
            >
              <X :size="24" />
            </button>
          </div>
        </div>
        <div class="chart-focus-body">
          <DashboardBlockChartPreview v-if="block" ref="previewRef" :block="block" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { X } from 'lucide-vue-next'
import DashboardBlockChartPreview from './DashboardBlockChartPreview.vue'
import ChartExportDropdown from './ChartExportDropdown.vue'

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
.chart-focus-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1060;
  padding: 1.5rem;
}

.chart-focus-modal {
  background: var(--bs-body-bg, #fff);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2), 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1200px;
  height: 85vh;
  max-height: 900px;
  overflow: hidden;
}

.chart-focus-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.chart-focus-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-primary-text);
  margin: 0;
  line-height: 1.3;
}

.chart-focus-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chart-focus-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: var(--color-secondary-text);
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.chart-focus-close:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-primary-text);
}

.chart-focus-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
