<template>
  <div class="table-picker">
    <div class="picker-header">
      <h4 class="picker-title">Выберите таблицу</h4>
      <input
        v-model="searchQuery"
        type="text"
        class="form-control form-control-sm picker-search"
        placeholder="Поиск..."
      />
    </div>

    <div class="picker-content">
      <div v-if="loading" class="picker-loading">
        <div class="spinner-border spinner-border-sm" role="status">
          <span class="visually-hidden">Загрузка...</span>
        </div>
        <span class="loading-text">Загрузка таблиц...</span>
      </div>

      <div v-else-if="!connectionId" class="picker-empty">
        <Database :size="32" class="empty-icon" />
        <span class="empty-text">Сначала выберите подключение</span>
      </div>

      <div v-else-if="filteredItems.length === 0" class="picker-empty">
        <Table :size="32" class="empty-icon" />
        <span class="empty-text">Таблицы не найдены</span>
      </div>

      <ul v-else class="table-list">
        <li
          v-for="item in filteredItems"
          :key="getSourceItemKey(item)"
          class="table-item"
          :class="{ selected: isSelected(item) }"
          @click="selectItem(item)"
        >
          <div class="table-icon">
            <FileSpreadsheet v-if="item.file_id || item.file_upload_id" :size="20" />
            <Table v-else :size="20" />
          </div>
          <div class="table-info">
            <span class="table-name">{{ getSourceItemDisplayName(item) }}</span>
            <span v-if="item.schema" class="table-schema">{{ item.schema }}</span>
          </div>
          <div v-if="isSelected(item)" class="table-check">
            <Check :size="18" />
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, toRef } from 'vue'
import { Database, Table, FileSpreadsheet, Check } from 'lucide-vue-next'
import { getSourceItemKey, getSourceItemDisplayName } from './js/sourceItemUtils.js'
import { useConnectionItems } from './js/useConnectionItems.js'

const props = defineProps({
  modelValue: {
    type: Object,
    default: null
  },
  connectionId: {
    type: [Number, String],
    default: null
  },
  connectionType: {
    type: String,
    default: ''
  },
  excludeTableIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'select', 'tablesLoaded'])

const searchQuery = ref('')

const { items, loading, loadItems } = useConnectionItems(
  toRef(props, 'connectionId'),
  toRef(props, 'connectionType')
)

watch(items, (val) => {
  emit('tablesLoaded', val)
}, { immediate: true })

const filteredItems = computed(() => {
  let result = items.value

  if (props.excludeTableIds.length > 0) {
    const excludeSet = new Set(props.excludeTableIds.map(id => String(id)))
    result = result.filter(t => !excludeSet.has(String(getSourceItemKey(t))))
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      getSourceItemDisplayName(t).toLowerCase().includes(query) ||
      (t.schema && t.schema.toLowerCase().includes(query))
    )
  }

  return result
})

function isSelected(item) {
  if (!props.modelValue) return false
  return getSourceItemKey(item) === getSourceItemKey(props.modelValue)
}

function selectItem(item) {
  emit('update:modelValue', item)
  emit('select', item)
}

defineExpose({
  tables: items,
  refresh: loadItems
})
</script>

<style scoped lang="scss">
.table-picker {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 300px;
}

.picker-header {
  padding: 0 0 1rem 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.picker-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a1a1a);
  margin: 0 0 0.75rem 0;
}

.picker-search {
  font-size: 13px;
}

.picker-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.picker-loading,
.picker-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: var(--color-text-secondary, #666);
  gap: 0.75rem;
}

.empty-icon {
  opacity: 0.5;
}

.table-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.table-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;

  &:hover {
    background: rgba(0, 0, 0, 0.04);
  }

  &.selected {
    background: rgba(59, 130, 246, 0.1);
    border-color: #3b82f6;
  }
}

.table-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  flex-shrink: 0;
  color: var(--color-text-secondary, #666);
}

.table-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.table-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary, #1a1a1a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.table-schema {
  font-size: 12px;
  color: var(--color-text-secondary, #666);
}

.table-check {
  color: #3b82f6;
  flex-shrink: 0;
}
</style>
