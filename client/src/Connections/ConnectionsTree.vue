<template>
  <div class="connections-tree">
    <div class="tree-header">
      <div class="tree-header-content">
        <div class="search-wrapper">
          <Search :size="18" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            class="form-control form-control-sm search-input"
            placeholder="Поиск по подключениям..."
            @input="handleSearch"
          />
        </div>
        <button
          class="btn btn-sm btn-primary create-btn"
          @click="$emit('create-connection')"
          title="Создать новое подключение"
        >
          <Plus :size="18" />
          Новое подключение
        </button>
      </div>
    </div>

    <div class="tree-content" v-if="!isLoading && connections.length > 0">
      <ConnectionTreeNode
        v-for="connection in filteredConnections"
        :key="connection.id"
        :node="connection"
        :level="0"
        :expanded-nodes="expandedNodes"
        @toggle-expand="handleToggleExpand"
        @node-click="handleNodeClick"
        @file-deleted="handleFileDeleted"
      />
    </div>

    <div v-else-if="isLoading" class="tree-loading">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
      <span>Загрузка подключений...</span>
    </div>

    <div v-else class="tree-empty">
      <p>Нет подключений</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Plus, Search } from 'lucide-vue-next'
import { apiClient } from '@/js/api/manager'
import { endpoints } from '@/js/api/endpoints'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'
import ConnectionTreeNode from './ConnectionsTree/ConnectionTreeNode.vue'

const emit = defineEmits(['create-connection', 'node-click', 'file-deleted'])

const connections = ref([])
const isLoading = ref(false)
const searchQuery = ref('')
const expandedNodes = ref({})

// Загрузка подключений
async function loadConnections() {
  isLoading.value = true
  try {
    const res = await apiClient.get(biEndpoints.bi.ConnectionsList)
    if (res.success) {
      connections.value = res.data || []
    }
  } catch (error) {
    logError('Ошибка загрузки подключений:', error)
  } finally {
    isLoading.value = false
  }
}

// Фильтрация подключений по поисковому запросу
const filteredConnections = computed(() => {
  if (!searchQuery.value.trim()) {
    return connections.value
  }
  
  const query = searchQuery.value.toLowerCase()
  return connections.value.filter(conn => {
    return conn.name?.toLowerCase().includes(query) ||
           conn.connector_type_display?.toLowerCase().includes(query)
  })
})

// Обработка поиска
function handleSearch() {
  // Поиск уже работает через computed filteredConnections
}

// Обработка удаления файла
function handleFileDeleted({ fileId, connectionId }) {
  // Пробрасываем событие для обновления счетчика файлов в ConnectionInfo
  emit('file-deleted', { fileId, connectionId })
  
  // Диспатчим глобальное событие для обновления дерева
  window.dispatchEvent(new CustomEvent('connections-reload'))
}

// Переключение раскрытия узла
function handleToggleExpand(nodeId, isExpanded) {
  if (isExpanded) {
    expandedNodes.value[nodeId] = true
  } else {
    delete expandedNodes.value[nodeId]
  }
}

// Клик на узел (для предпросмотра)
function handleNodeClick(node) {
  emit('node-click', node)
}

// Обработчик события обновления подключений
function handleConnectionsReload() {
  loadConnections()
}

onMounted(() => {
  loadConnections()
  window.addEventListener('connections-reload', handleConnectionsReload)
})

onBeforeUnmount(() => {
  window.removeEventListener('connections-reload', handleConnectionsReload)
})
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.connections-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-primary-background);
  position: relative;
  z-index: 1;
}

.tree-header {
  padding: 1.25rem 1rem;
  background: var(--color-primary-background);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.tree-header-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 0.875rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-secondary-text);
  opacity: 0.5;
  pointer-events: none;
  z-index: 2;
  transition: opacity 0.2s ease;

  .search-input:focus ~ & {
    opacity: 0.7;
    color: rgba(var(--bs-info-rgb), 1);
  }
}

.search-input {
  padding-left: 2.5rem !important;
  background: var(--color-primary-background);
  color: var(--color-primary-text);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.75rem 0.875rem;
  font-size: 0.9rem;
  transition: all 0.2s ease;

  &:focus {
    border-color: rgba(var(--bi-accent-rgb), 0.5);
    box-shadow: 0 0 0 3px rgba(var(--bi-accent-rgb), 0.12);
    outline: none;
  }

  &::placeholder {
    color: var(--color-secondary-text);
    opacity: 0.6;
  }
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.15);
    border-radius: 3px;

    &:hover {
      background-color: rgba(0, 0, 0, 0.25);
    }
  }
}

.tree-loading,
.tree-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  gap: 1.5rem;
  color: var(--color-secondary-text);
}

.tree-loading {
  flex: 1;

  .spinner-border {
    border-color: rgba(var(--bs-info-rgb), 0.15);
    border-right-color: rgba(var(--bs-info-rgb), 1);
    width: 2.5rem;
    height: 2.5rem;
    border-width: 3px;
  }

  span {
    font-size: 0.95rem;
    opacity: 0.8;
    font-weight: 500;
  }
}

.tree-empty {
  background: var(--color-secondary-background);
  border-radius: 12px;
  border: 1px dashed var(--color-border);
  margin: 1rem;
  padding: 2.5rem 2rem;

  p {
    margin: 0;
    font-size: 1rem;
    color: var(--color-secondary-text);
    opacity: 0.7;
    font-weight: 500;
  }

  .btn-sm {
    margin-top: 0.5rem;
  }
}

.form-control {
  width: 100%;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  transition: all 0.2s ease;

  &:focus {
    border-color: rgba(var(--bs-info-rgb), 0.5);
    box-shadow: 0 0 0 3px rgba(var(--bs-info-rgb), 0.1);
    outline: none;
  }
}

.create-btn {
  border-radius: 10px;
  padding: 0.75rem 1.125rem;
  font-size: 0.875rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
  background: linear-gradient(135deg, rgba(var(--bi-accent-rgb), 1) 0%, rgba(var(--bi-accent-rgb), 0.95) 100%);
  color: white;
  box-shadow: 0 3px 6px rgba(var(--bi-accent-rgb), 0.3), 0 1px 3px rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s ease;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(var(--bi-accent-rgb), 0.4), 0 2px 6px rgba(0, 0, 0, 0.15);
    background: linear-gradient(135deg, rgba(var(--bi-accent-rgb), 0.98) 0%, rgba(var(--bi-accent-rgb), 0.92) 100%);

    &::before {
      left: 100%;
    }
  }

  &:active {
    transform: translateY(0);
    box-shadow: 0 2px 4px rgba(var(--bi-accent-rgb), 0.3);
  }
}

.form-control {
  width: 100%;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 0.625rem 0.875rem;
  font-size: 0.9rem;
  transition: all 0.2s ease;

  &:focus {
    border-color: rgba(var(--bs-info-rgb), 0.5);
    box-shadow: 0 0 0 3px rgba(var(--bs-info-rgb), 0.1);
    outline: none;
  }
}
</style>
