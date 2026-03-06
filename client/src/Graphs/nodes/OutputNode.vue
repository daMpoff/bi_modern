<template>
  <div class="output-node" :class="{ selected }">
    <Handle type="target" :position="Position.Top" />
    <div class="node-content">
      <div class="node-icon">
        <LogOut :size="20" />
      </div>
      <div class="node-info">
        <div class="node-label">{{ data?.label || 'Выход' }}</div>
        <div class="node-hint">Конечная точка данных</div>
      </div>
      <button
        v-if="data?.onDelete"
        type="button"
        class="node-delete"
        title="Удалить блок"
        @click.stop="data?.onDelete?.(id)"
      >
        <Trash2 :size="16" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { Handle, Position } from '@vue-flow/core'
import { LogOut, Trash2 } from 'lucide-vue-next'

defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})
</script>

<style scoped lang="scss">
.output-node {
  min-width: 200px;
  background: #fff;
  border: 2px solid #f43f5e;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;

  &.selected {
    border-color: #e11d48;
    box-shadow: 0 4px 16px rgba(244, 63, 94, 0.3);
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
  background: rgba(244, 63, 94, 0.1);
  border-radius: 6px;
  color: #f43f5e;
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

.node-hint {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

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

  &:hover {
    background: rgba(220, 38, 38, 0.1);
    color: #dc2626;
  }
}
</style>
