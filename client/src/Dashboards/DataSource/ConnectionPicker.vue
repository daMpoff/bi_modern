<template>
  <div class="connection-picker">
    <div class="picker-header">
      <h4 class="picker-title">Выберите подключение</h4>
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
        <span class="loading-text">Загрузка подключений...</span>
      </div>

      <div v-else-if="filteredConnections.length === 0" class="picker-empty">
        <Database :size="32" class="empty-icon" />
        <span class="empty-text">Подключения не найдены</span>
        <button type="button" class="btn btn-primary go-to-connections-btn" @click="goToConnections">
          <ArrowRight :size="16" />
          Перейти к подключениям
        </button>
      </div>

      <ul v-else class="connection-list">
        <li
          v-for="conn in filteredConnections"
          :key="conn.id"
          class="connection-item"
          :class="{ selected: isSelected(conn), disabled: conn.hasProblems }"
          @click="selectConnection(conn)"
        >
          <div class="connection-icon">
            <img v-if="getConnectionIcon(conn)" :src="getConnectionIcon(conn)" alt="" class="connector-img" />
            <Database v-else :size="20" />
          </div>
          <div class="connection-info">
            <span class="connection-name">{{ conn.name }}</span>
            <span class="connection-type">{{ getConnectionTypeLabel(getConnectionType(conn)) }}</span>
          </div>
          <div v-if="isSelected(conn)" class="connection-check">
            <Check :size="18" />
          </div>
          <div v-if="conn.hasProblems" class="connection-warning" :title="conn.problemText">
            <AlertTriangle :size="16" />
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Database, Check, AlertTriangle, ArrowRight } from 'lucide-vue-next'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'
import { getConnectionType, getConnectionTypeLabel, isFileConnection } from './js/connectionType.js'

import ClickHouseIcon from '@/modules/bi_analysis_modern/client/src/assets/icons/clickhouse.svg'
import PostgresIcon from '@/modules/bi_analysis_modern/client/src/assets/icons/postgres.svg'
import MssqlIcon from '@/modules/bi_analysis_modern/client/src/assets/icons/mssql.svg'
import FileIcon from '@/modules/bi_analysis_modern/client/src/assets/icons/folder_windows_style.svg'

const props = defineProps({
  modelValue: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'select'])

const router = useRouter()
const connections = ref([])
const loading = ref(false)
const searchQuery = ref('')

const filteredConnections = computed(() => {
  if (!searchQuery.value) return connections.value
  const query = searchQuery.value.toLowerCase()
  return connections.value.filter(c =>
    c.name?.toLowerCase().includes(query) ||
    getConnectionTypeLabel(getConnectionType(c)).toLowerCase().includes(query)
  )
})

function isSelected(conn) {
  return props.modelValue?.id === conn.id
}

function getConnectionIcon(conn) {
  const type = (getConnectionType(conn) || '').toLowerCase().trim()
  if (type.includes('clickhouse')) return ClickHouseIcon
  if (type.includes('postgres')) return PostgresIcon
  if (type.includes('mssql') || type.includes('sql server')) return MssqlIcon
  if (type.includes('file') || type.includes('файл')) return FileIcon
  return null
}

function selectConnection(conn) {
  if (conn.hasProblems) return
  emit('update:modelValue', conn)
  emit('select', conn)
}

function goToConnections() {
  router.push({ name: 'ConnectionsModern' })
}

async function loadConnections() {
  loading.value = true
  try {
    const res = await apiClient.get(biEndpoints.bi.ConnectionsList)
    if (res.success && res.data) {
      connections.value = res.data.map(c => ({
        ...c,
        hasProblems: false,
        problemText: ''
      }))
      await checkFileConnectionsStatus()
    }
  } catch (err) {
    console.error('Ошибка загрузки подключений:', err)
  } finally {
    loading.value = false
  }
}

async function checkFileConnectionsStatus() {
  const fileConns = connections.value.filter(c => isFileConnection(getConnectionType(c)))

  for (const conn of fileConns) {
    try {
      const res = await apiClient.get(biEndpoints.bi.connectionFiles(conn.id))
      if (res.success && res.data) {
        const files = Array.isArray(res.data) ? res.data : []
        const hasMissing = files.length === 0
        const hasProblematic = files.some(f => f.missing || !f.exists || f.status === 'error')
        
        if (hasMissing || hasProblematic) {
          conn.hasProblems = true
          conn.problemText = hasMissing ? 'Нет файлов' : 'Проблемы с файлами'
        }
      }
    } catch (err) {
      console.warn(`Ошибка проверки файлов для ${conn.id}:`, err)
    }
  }
}

onMounted(() => {
  loadConnections()
})
</script>

<style scoped lang="scss">
.connection-picker {
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
  color: var(--color-primary-text);
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
  color: var(--color-secondary-text);
  gap: 0.75rem;
}

.empty-icon {
  opacity: 0.5;
}

.go-to-connections-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 1rem;
  padding: 0.625rem 1.25rem;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.2s ease;

  svg {
    display: flex;
    align-items: center;
  }

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  }

  &:active {
    transform: translateY(0);
  }
}

.connection-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.connection-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;

  &:hover:not(.disabled) {
    background: rgba(0, 0, 0, 0.04);
  }

  &.selected {
    background: rgba(59, 130, 246, 0.1);
    border-color: #3b82f6;
  }

  &.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.connection-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  flex-shrink: 0;

  .connector-img {
    width: 24px;
    height: 24px;
  }
}

.connection-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.connection-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.connection-type {
  font-size: 12px;
  color: var(--color-secondary-text);
}

.connection-check {
  color: #3b82f6;
  flex-shrink: 0;
}

.connection-warning {
  color: #f59e0b;
  flex-shrink: 0;
}
</style>
