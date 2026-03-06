<template>
  <div class="connection-preview">
    <div v-if="!node" class="preview-empty">
      <div class="preview-empty-content">
        <Database :size="64" class="preview-empty-icon" />
        <h3>Выберите элемент для предпросмотра</h3>
        <p>Кликните на подключение, таблицу, файл или колонку в дереве слева для просмотра данных</p>
      </div>
    </div>

    <!-- Предпросмотр файла -->
    <FilePreviewPanel
      v-else-if="nodeType === 'file'"
      :file="node"
      :isLoading="isLoading"
    />

    <!-- Предпросмотр таблицы БД -->
    <TablePreview
      v-else-if="nodeType === 'table'"
      :table="node"
      :isLoading="isLoading"
    />

    <!-- Предпросмотр колонки -->
    <ColumnPreview
      v-else-if="nodeType === 'column'"
      :column="node"
      :isLoading="isLoading"
    />

    <!-- Информация о подключении -->
    <ConnectionInfo
      v-else-if="nodeType === 'connection'"
      :connection="node"
      @deleted="$emit('connection-deleted', $event)"
    />

    <!-- Загрузка -->
    <div v-else-if="isLoading" class="preview-loading">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
      <span>Загрузка данных...</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Database } from 'lucide-vue-next'
import FilePreviewPanel from '../Files/FilePreviewPanel.vue'
import TablePreview from './preview/TablePreview.vue'
import ColumnPreview from './preview/ColumnPreview.vue'
import ConnectionInfo from './preview/ConnectionInfo.vue'

const props = defineProps({
  node: {
    type: Object,
    default: null
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['connection-deleted'])

// Определение типа узла
const nodeType = computed(() => {
  if (!props.node) return null
  
  // Используем поле type, которое добавляется в ConnectionTreeNode
  if (props.node.type) {
    return props.node.type
  }
  
  // Fallback для обратной совместимости
  if (props.node.connector_type) {
    return 'connection'
  } else if (props.node.file_type || props.node.name?.endsWith('.csv') || props.node.name?.endsWith('.xlsx')) {
    return 'file'
  } else if (props.node.table_name || props.node.schema !== undefined) {
    return 'table'
  } else if (props.node.data_type || props.node.type) {
    return 'column'
  }
  
  return null
})
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.connection-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 3rem 2rem;
  position: relative;

  // Декоративные элементы для пустого состояния
  &::before,
  &::after {
    content: '';
    position: absolute;
    pointer-events: none;
    opacity: 0.12;
    border-radius: 50%;
    filter: blur(40px);
  }

  &::before {
    top: 20%;
    left: 10%;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(var(--bs-info-rgb), 0.4) 0%, transparent 70%);
  }

  &::after {
    bottom: 20%;
    right: 15%;
    width: 180px;
    height: 180px;
    background: radial-gradient(circle, rgba(var(--bs-primary-rgb), 0.3) 0%, transparent 70%);
  }
}

.preview-empty-content {
  text-align: center;
  max-width: 450px;
  padding: 2.5rem;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  position: relative;
}

.preview-empty-icon {
  color: var(--color-secondary-text);
  margin-bottom: 1.5rem;
  opacity: 0.4;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.preview-empty-content h3 {
  color: var(--color-primary-text);
  margin-bottom: 0.75rem;
  font-size: 1.375rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.preview-empty-content p {
  color: var(--color-secondary-text);
  margin: 0;
  line-height: 1.7;
  font-size: 0.95rem;
  opacity: 0.8;
}

.preview-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1.25rem;
  color: var(--color-secondary-text);

  .spinner-border {
    border-color: rgba(var(--bs-info-rgb), 0.2);
    border-right-color: rgba(var(--bs-info-rgb), 1);
  }

  span {
    font-size: 0.95rem;
    opacity: 0.8;
  }
}
</style>
