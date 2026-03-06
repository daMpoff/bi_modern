<template>
  <div class="column-preview">
    <div v-if="isLoading" class="preview-loading">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
      <span>Загрузка статистики колонки...</span>
    </div>

    <div v-else-if="error" class="preview-error">
      <h3>Ошибка загрузки данных</h3>
      <p>{{ error }}</p>
    </div>

    <div v-else-if="column" class="preview-content">
      <div class="preview-header">
        <h3>{{ column.name || column.column_name }}</h3>
        <span class="preview-badge">{{ column.type || column.data_type || 'unknown' }}</span>
      </div>

      <div class="preview-info">
        <div class="info-section">
          <h4>Основная информация</h4>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Тип данных:</span>
              <span class="info-value">{{ column.type || column.data_type || 'неизвестно' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Nullable:</span>
              <span class="info-value">{{ column.nullable ? 'Да' : 'Нет' }}</span>
            </div>
            <div v-if="column.default" class="info-item">
              <span class="info-label">Значение по умолчанию:</span>
              <span class="info-value">{{ column.default }}</span>
            </div>
          </div>
        </div>

        <div v-if="stats" class="info-section">
          <h4>Статистика</h4>
          <div class="info-grid">
            <div v-if="stats.totalCount !== undefined" class="info-item">
              <span class="info-label">Всего значений:</span>
              <span class="info-value">{{ stats.totalCount }}</span>
            </div>
            <div v-if="stats.uniqueCount !== undefined" class="info-item">
              <span class="info-label">Уникальных:</span>
              <span class="info-value">{{ stats.uniqueCount }}</span>
            </div>
            <div v-if="stats.nullCount !== undefined" class="info-item">
              <span class="info-label">NULL значений:</span>
              <span class="info-value">{{ stats.nullCount }}</span>
            </div>
          </div>
        </div>

        <div v-if="samples && samples.length > 0" class="info-section">
          <h4>Примеры значений</h4>
          <div class="samples-list">
            <span
              v-for="(sample, index) in samples"
              :key="index"
              class="sample-item"
            >
              {{ sample }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="preview-empty">
      <p>Данные колонки не загружены</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  column: {
    type: Object,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const error = ref(null)
const stats = ref(null)
const samples = ref([])

// Загрузка статистики колонки
async function loadColumnStats() {
  // TODO: Создать API endpoint для статистики колонки
  // Пока используем только данные из props
  error.value = null
}

onMounted(() => {
  if (props.column) {
    loadColumnStats()
  }
})

watch(() => props.column, (newColumn) => {
  if (newColumn) {
    loadColumnStats()
  }
}, { deep: true })
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.column-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: 1.5rem;
  position: relative;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;

  // Декоративные элементы фона
  &::before,
  &::after {
    content: '';
    position: absolute;
    pointer-events: none;
    opacity: 0.1;
    border-radius: 50%;
    filter: blur(55px);
    z-index: 0;
  }

  &::before {
    top: 8%;
    right: 4%;
    width: 280px;
    height: 280px;
    background: radial-gradient(circle, rgba(var(--bs-success-rgb), 0.35) 0%, transparent 70%);
    animation: float 24s ease-in-out infinite;
  }

  &::after {
    bottom: 12%;
    left: 6%;
    width: 260px;
    height: 260px;
    background: radial-gradient(circle, rgba(var(--bs-info-rgb), 0.3) 0%, transparent 70%);
    animation: float 30s ease-in-out infinite reverse;
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

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(20px, -20px) scale(1.08);
  }
  66% {
    transform: translate(-18px, 18px) scale(0.92);
  }
}

.preview-loading,
.preview-error,
.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1.25rem;
  color: var(--color-secondary-text);
  padding: 2rem;
}

.preview-error {
  color: var(--color-accent);

  h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
  }

  p {
    margin: 0;
    opacity: 0.8;
  }
}

.preview-empty {
  p {
    margin: 0;
    opacity: 0.7;
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
      rgba(var(--bs-success-rgb), 0.4) 0%,
      rgba(var(--bs-info-rgb), 0.4) 50%,
      rgba(var(--bs-success-rgb), 0.4) 100%);
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
      rgba(var(--bs-success-rgb), 0.6) 0%,
      rgba(var(--bs-info-rgb), 0.6) 100%);
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

.samples-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.sample-item {
  padding: 0.625rem 1.125rem;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-primary-text);
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    transform: translateY(-3px);
    box-shadow: 
      0 8px 20px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.9);
    background: rgba(255, 255, 255, 0.8);
  }
}
</style>
