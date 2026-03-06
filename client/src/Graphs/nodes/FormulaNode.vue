<template>
  <div class="formula-node" :class="{ selected: selected }">
    <Handle type="target" :position="Position.Top" />
    <Handle type="source" :position="Position.Bottom" />
    <div class="node-content">
      <div class="node-icon">
        <SquareFunction :size="20" />
      </div>
      <div class="node-info">
        <div class="node-label">{{ data.label || 'Формула' }}</div>
        <div v-if="data.formula" class="node-subtitle">{{ truncateFormula(data.formula) }}</div>
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
import { Handle, Position } from '@vue-flow/core'
import { SquareFunction, Settings2, Trash2 } from 'lucide-vue-next'

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

function truncateFormula(formula) {
  if (!formula) return ''
  return formula.length > 20 ? formula.substring(0, 20) + '...' : formula
}
</script>

<style scoped lang="scss">
.formula-node {
  min-width: 200px;
  background: #fff;
  border: 2px solid #8b5cf6;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  
  &.selected {
    border-color: #7c3aed;
    box-shadow: 0 4px 16px rgba(139, 92, 246, 0.3);
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
  background: rgba(139, 92, 246, 0.1);
  border-radius: 6px;
  color: #8b5cf6;
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
  color: #8b5cf6;
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