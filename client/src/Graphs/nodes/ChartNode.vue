<template>
  <div class="chart-node" :class="{ selected: selected }">
    <Handle type="target" :position="Position.Top" />
    <div class="node-content">
      <div class="node-icon">
        <BarChart3 :size="20" />
      </div>
      <div class="node-info">
        <div class="node-label">{{ data.label || 'Выход' }}</div>
        <div v-if="chartTypeLabel" class="node-subtitle">{{ chartTypeLabel }}</div>
      </div>
      <button
        v-if="data?.onDelete"
        type="button"
        class="node-delete"
        :class="{ 'node-delete--disabled': data?.canDelete === false }"
        :disabled="data?.canDelete === false"
        :title="data?.canDelete === false ? 'Сначала удалите блок «Соединение»' : 'Удалить блок'"
        @click.stop="data?.canDelete !== false && data?.onDelete?.(id)"
      >
        <Trash2 :size="16" />
      </button>
      <button class="node-settings" @click.stop="handleSettingsClick">
        <Settings2 :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { BarChart3, Settings2, Trash2 } from 'lucide-vue-next'
import { CHART_TYPES } from '@/modules/bi_analysis_modern/client/src/js/chartTypes.js'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})

function handleSettingsClick() {
  if (props.data?.onSettings) {
    props.data.onSettings(props.id)
  }
}

const chartTypeLabel = computed(() => {
  const chartType = props.data?.config?.chartType
  if (!chartType) return null
  const found = CHART_TYPES.find(ct => ct.chartType === chartType)
  return found?.label || chartType
})
</script>

<style scoped lang="scss">
.chart-node {
  min-width: 200px;
  background: #fff;
  border: 2px solid #06b6d4;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  
  &.selected {
    border-color: #0891b2;
    box-shadow: 0 4px 16px rgba(6, 182, 212, 0.3);
  }
}

.node-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
}

.node-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: rgba(6, 182, 212, 0.1);
  border-radius: 6px;
  color: #06b6d4;
  flex-shrink: 0;
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-label {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-subtitle {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-settings,
.node-delete {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.node-settings:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #06b6d4;
}

.node-delete:hover:not(:disabled) {
  background: rgba(220, 38, 38, 0.1);
  color: #dc2626;
}

.node-delete--disabled,
.node-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>