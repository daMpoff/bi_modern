<template>
  <div class="connection-info">
    <!-- Декоративные элементы -->
    <div class="decorative-elements">
      <div class="decorative-circle decorative-circle-1"></div>
      <div class="decorative-circle decorative-circle-2"></div>
      <div class="decorative-circle decorative-circle-3"></div>
    </div>
    <div class="preview-content">
      <div class="preview-header">
        <h3>{{ connection.name }}</h3>
        <div class="preview-header-actions">
          <span class="preview-badge">{{ connectionBadgeText }}</span>
          <button
            class="btn btn-sm btn-outline-danger delete-btn"
            @click="handleDelete"
            title="Удалить подключение"
          >
            <Trash2 :size="16" />
            Удалить
          </button>
        </div>
      </div>

      <div class="preview-info">
        <div class="info-section">
          <h4>Основная информация</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Тип подключения:</span>
              <span class="info-value">{{ connection.connector_type_display || connection.connector_type }}</span>
            </div>
            <div v-if="connection.created_at" class="info-item">
              <span class="info-label">Дата создания:</span>
              <span class="info-value">{{ formatDate(connection.created_at) }}</span>
            </div>
            <div v-if="connection.connector_type === 'file'" class="info-item">
              <span class="info-label">Количество файлов:</span>
              <span class="info-value">
                <span v-if="filesCountLoading">Загрузка...</span>
                <span v-else>{{ filesCount || 0 }}</span>
              </span>
            </div>
          </div>
        </div>

        <!-- Параметры подключения показываем только для БД подключений, не для файлов -->
        <div v-if="connection.config && connection.connector_type !== 'file'" class="info-section">
          <h4>Параметры подключения</h4>
          <div class="info-grid">
            <div v-if="connection.config.host" class="info-item">
              <span class="info-label">Хост:</span>
              <span class="info-value">{{ connection.config.host }}</span>
            </div>
            <div v-if="connection.config.port" class="info-item">
              <span class="info-label">Порт:</span>
              <span class="info-value">{{ connection.config.port }}</span>
            </div>
            <div v-if="connection.config.database" class="info-item">
              <span class="info-label">База данных:</span>
              <span class="info-value">{{ connection.config.database }}</span>
            </div>
            <div v-if="connection.config.user" class="info-item">
              <span class="info-label">Пользователь:</span>
              <span class="info-value">{{ connection.config.user }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { logError } from '@/js/utils/logError.js'
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { Trash2 } from 'lucide-vue-next'
import { confirmDelete } from '@/js/utils/confirm.js'
import { useToast } from '@/js/utils/toast.js'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'

const props = defineProps({
  connection: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['deleted'])

const toast = useToast()
const isDeleting = ref(false)
const filesCount = ref(null)
const filesCountLoading = ref(false)

const connectionBadgeText = ref('Подключение')

function buildConnectionBadgeText(connection) {
  const typeRaw = connection?.connector_type
  const typeDisplay = connection?.connector_type_display || typeRaw

  // Самый частый UX-конфуз: "Файл" воспринимается как сущность, а не тип подключения
  if (typeRaw === 'file' || (typeof typeDisplay === 'string' && typeDisplay.toLowerCase() === 'файл')) {
    return 'Файловое подключение'
  }

  if (!typeDisplay) {
    return 'Подключение'
  }

  // Для остальных типов делаем явную подпись "подключение", чтобы это не путалось с сущностями дерева
  return `Подключение: ${typeDisplay}`
}

// Загрузка количества файлов для файловых подключений
async function loadFilesCount() {
  if (props.connection?.connector_type !== 'file' || !props.connection?.id) {
    return
  }
  
  filesCountLoading.value = true
  try {
    const endpoint = biEndpoints.bi.connectionFiles(props.connection.id)
    const res = await apiClient.get(endpoint)
    if (res.success && Array.isArray(res.data)) {
      filesCount.value = res.data.length
    } else {
      filesCount.value = 0
    }
  } catch (error) {
    logError('Ошибка загрузки файлов:', error)
    filesCount.value = 0
  } finally {
    filesCountLoading.value = false
  }
}

// Обработка события обновления файлов
function handleFilesReload(event) {
  const { connectionId } = event.detail || {}
  if (connectionId && props.connection?.id === connectionId && props.connection?.connector_type === 'file') {
    loadFilesCount()
  }
}

// Загружаем количество файлов при монтировании и при изменении connection
onMounted(() => {
  connectionBadgeText.value = buildConnectionBadgeText(props.connection)
  if (props.connection?.connector_type === 'file') {
    loadFilesCount()
  }
  
  // Слушаем событие обновления файлов
  window.addEventListener('files-reload', handleFilesReload)
})

onBeforeUnmount(() => {
  window.removeEventListener('files-reload', handleFilesReload)
})

watch(() => props.connection?.id, () => {
  connectionBadgeText.value = buildConnectionBadgeText(props.connection)
  if (props.connection?.connector_type === 'file') {
    loadFilesCount()
  } else {
    filesCount.value = null
  }
})

async function handleDelete() {
  if (!props.connection?.id) {
    logError('Cannot delete: connection.id is missing!', props.connection)
    toast.error('Ошибка: не найден ID подключения')
    return
  }

  const ok = await confirmDelete(
    'Удаление подключения',
    `Удалить подключение «${props.connection.name || ''}»?`,
  )
  if (!ok) {
    return
  }

  isDeleting.value = true

  try {
    const connectionId = parseInt(props.connection.id, 10)

    if (isNaN(connectionId)) {
      logError('Invalid connection ID:', props.connection.id)
      toast.error('Ошибка: неверный ID подключения')
      return
    }

    const endpoint = biEndpoints.bi.connectionDetail(connectionId)
    const res = await apiClient.delete(endpoint)

    if (res && (res.success === true || res.status === 204 || res.status === 200)) {
      toast.success(`Подключение "${props.connection.name}" успешно удалено`)
      emit('deleted', props.connection.id)
      return
    }

    if (res && res.success === false) {
      const errorMsg = res.message || res.error || 'Ошибка при удалении подключения'
      toast.error(errorMsg)
      return
    }

    if (res && (res.status >= 200 && res.status < 300)) {
      toast.success(`Подключение "${props.connection.name}" успешно удалено`)
      emit('deleted', props.connection.id)
      return
    }

    logError('Unexpected delete response format:', res)
    toast.error('Неожиданный формат ответа от сервера')
  } catch (error) {
    logError('Ошибка удаления подключения:', error)
    const errorMsg = error?.response?.data?.message ||
                     error?.response?.data?.detail ||
                     error?.response?.data?.error ||
                     error?.message ||
                     'Ошибка при удалении подключения'
    toast.error(errorMsg)
  } finally {
    isDeleting.value = false
  }
}

function formatDate(dateString) {
  if (!dateString) return 'не указана'
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  } catch {
    return dateString
  }
}
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.connection-info {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;

  // Декоративные элементы через отдельный блок
  .decorative-elements {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
  }

  .decorative-circle {
    position: absolute;
    border-radius: 50%;
    filter: blur(60px);
    opacity: 0.12;
    animation: float 20s ease-in-out infinite;

    &.decorative-circle-1 {
      top: 10%;
      right: 5%;
      width: 320px;
      height: 320px;
      background: radial-gradient(circle, rgba(var(--bs-info-rgb), 0.5) 0%, transparent 70%);
      animation-duration: 18s;
    }

    &.decorative-circle-2 {
      bottom: 15%;
      left: 8%;
      width: 280px;
      height: 280px;
      background: radial-gradient(circle, rgba(var(--bs-primary-rgb), 0.4) 0%, transparent 70%);
      animation-duration: 24s;
      animation-delay: -5s;
    }

    &.decorative-circle-3 {
      top: 60%;
      right: 20%;
      width: 200px;
      height: 200px;
      background: radial-gradient(circle, rgba(var(--bs-success-rgb), 0.3) 0%, transparent 70%);
      animation-duration: 30s;
      animation-delay: -10s;
    }
  }

  @keyframes float {
    0%, 100% {
      transform: translate(0, 0) scale(1);
    }
    25% {
      transform: translate(30px, -30px) scale(1.1);
    }
    50% {
      transform: translate(-20px, 20px) scale(0.9);
    }
    75% {
      transform: translate(20px, 30px) scale(1.05);
    }
  }

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background-color: rgba(0, 0, 0, 0.15);
    border-radius: 4px;

    &:hover {
      background-color: rgba(0, 0, 0, 0.25);
    }
  }
}

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  position: relative;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  position: relative;
  gap: 1rem;
}

.preview-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.preview-header h3 {
  margin: 0;
  color: var(--color-primary-text);
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.preview-badge {
  padding: 0.5rem 1.125rem;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-primary-text);
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.preview-info {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.info-section {
  background: rgba(255, 255, 255, 0.5);
  backdrop-filter: blur(12px);
  border-radius: 20px;
  padding: 1.5rem;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  // Декоративный градиентный фон
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, 
      rgba(var(--bs-info-rgb), 0.4) 0%,
      rgba(var(--bs-primary-rgb), 0.4) 50%,
      rgba(var(--bs-info-rgb), 0.4) 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    box-shadow: 
      0 12px 48px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.95);
    transform: translateY(-4px);
    background: rgba(255, 255, 255, 0.7);

    &::before {
      opacity: 1;
    }
  }
}

.info-section h4 {
  margin: 0 0 1.25rem 0;
  color: var(--color-primary-text);
  font-size: 1.0625rem;
  font-weight: 600;
  letter-spacing: -0.01em;
  position: relative;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.4);
  backdrop-filter: blur(8px);
  border-radius: 16px;
  box-shadow: 
    0 4px 16px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  // Декоративный элемент при наведении
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, 
      rgba(var(--bs-info-rgb), 0.6) 0%,
      rgba(var(--bs-primary-rgb), 0.6) 100%);
    transform: scaleY(0);
    transition: transform 0.3s ease;
    border-radius: 0 4px 4px 0;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.7);
    transform: translateX(6px);
    box-shadow: 
      0 8px 24px rgba(0, 0, 0, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);

    &::before {
      transform: scaleY(1);
    }
  }
}

.info-label {
  color: var(--color-secondary-text);
  font-size: 0.875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.7;
}

.info-value {
  color: var(--color-primary-text);
  font-size: 1rem;
  font-weight: 500;
  line-height: 1.5;
}

.delete-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border-color: var(--bs-danger);
  color: var(--bs-danger);
  transition: all 0.3s ease;
  
  &:hover {
    background-color: var(--bs-danger);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(var(--bs-danger-rgb), 0.3);
  }
  
  &:active {
    transform: translateY(0);
  }
}
</style>
