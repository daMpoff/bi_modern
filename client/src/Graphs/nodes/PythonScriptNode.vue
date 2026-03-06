<template>
  <div class="python-script-node" :class="{ selected: selected }">
    <Handle type="target" :position="Position.Top" />
    <Handle type="source" :position="Position.Bottom" />
    <div class="node-content">
      <div class="node-icon">
        <Code :size="20" />
      </div>
      <div class="node-info">
        <div class="node-label">{{ data.label || 'Python Script' }}</div>
        <div v-if="data.hasCode" class="node-subtitle">Код задан</div>
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
import { Code, Settings2, Trash2 } from 'lucide-vue-next'

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
</script>

<style scoped lang="scss">
.python-script-node {
  min-width: 200px;
  background: #fff;
  border: 2px solid #6366f1;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  
  &.selected {
    border-color: #4f46e5;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
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
  background: rgba(99, 102, 241, 0.1);
  border-radius: 6px;
  color: #6366f1;
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
  color: #6366f1;
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