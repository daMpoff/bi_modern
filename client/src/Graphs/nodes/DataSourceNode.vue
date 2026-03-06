<template>
  <div class="data-source-node-wrapper" :class="{ configured: isConfigured }">
    <!-- Заголовок над блоком с названием таблицы -->
    <div class="node-header-title" :class="{ empty: !tableTitle }">
      <Table :size="12" />
      <span>{{ tableTitle || 'Таблица не выбрана' }}</span>
    </div>
    
    <div class="data-source-node" :class="{ selected: selected, configured: isConfigured }">
      <Handle type="source" :position="Position.Bottom" />
      <div class="node-content">
        <div class="node-icon">
          <Database :size="20" />
        </div>
        <div class="node-info">
          <div class="node-label">{{ displayLabel }}</div>
          <div v-if="displaySubtitle" class="node-subtitle">{{ displaySubtitle }}</div>
          <div v-else-if="!isConfigured" class="node-hint">Кликните для настройки</div>
        </div>
        <div v-if="isConfigured" class="node-status configured">
          <Check :size="14" />
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
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Database, Settings2, Check, Table, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean
})

const isConfigured = computed(() => {
  const config = props.data?.config
  if (!config) return false
  return !!(config.sourceMode === 'inline' && config.connection_id)
})

// Заголовок над блоком - название выбранной таблицы
const tableTitle = computed(() => {
  const config = props.data?.config
  if (!config) return null

  if (config.sourceMode === 'inline' && config.main_table) {
    if (config.main_table.name) {
      return config.main_table.name
    }
    if (config.main_table.original_filename) {
      return config.main_table.original_filename
    }
  }
  return null
})

const displayLabel = computed(() => {
  const config = props.data?.config
  if (config?.sourceMode === 'inline' && config?.main_table) {
    if (config.main_table.name) {
      return config.main_table.name
    }
    if (config.main_table.original_filename) {
      return config.main_table.original_filename
    }
  }
  return props.data?.label || 'Источник данных'
})

const displaySubtitle = computed(() => {
  const config = props.data?.config
  if (!config) return null

  if (config.sourceMode === 'inline' && config.connectionName) {
    const relCount = config.relations?.length || 0
    return relCount > 0 
      ? `${config.connectionName} (+${relCount} связей)`
      : config.connectionName
  }
  return props.data?.connectionName || null
})

function handleSettingsClick() {
  if (props.data?.onSettings) {
    props.data.onSettings(props.id)
  }
}
</script>

<style scoped lang="scss">
.data-source-node-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: visible;
}

.node-header-title {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  margin-bottom: 6px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #3b82f6;
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;

  &.empty {
    background: rgba(0, 0, 0, 0.05);
    color: #999;
    font-style: italic;
    font-weight: 500;
  }

  .configured & {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
  }
}

.data-source-node {
  min-width: 200px;
  background: #fff;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  
  &.selected {
    border-color: #1d4ed8;
    box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
  }

  &.configured {
    border-color: #10b981;
  }

  &.configured.selected {
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.3);
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
  background: rgba(59, 130, 246, 0.1);
  border-radius: 6px;
  color: #3b82f6;
  flex-shrink: 0;

  .configured & {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
  }
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

.node-hint {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
  font-style: italic;
}

.node-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  flex-shrink: 0;

  &.configured {
    background: #10b981;
    color: #fff;
  }
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
  color: #3b82f6;
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