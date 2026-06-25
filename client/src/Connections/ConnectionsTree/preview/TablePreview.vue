<template>
  <div class="table-preview">
    <div v-if="isLoadingData && currentPage === 1" class="preview-loading">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
      <span>Загрузка данных таблицы...</span>
    </div>

    <div v-else-if="error" class="preview-error">
      <h3>Ошибка загрузки данных</h3>
      <p>{{ error }}</p>
    </div>

    <div v-else-if="columns.length > 0" class="preview-content">
      <div class="preview-header">
        <h3>{{ table.name || table.table_name }}</h3>
        <div class="preview-meta">
          <span v-if="table.schema">Схема: {{ table.schema }}</span>
          <span>Строк: {{ totalRows }}</span>
        </div>
      </div>

      <div class="preview-table-wrapper">
        <table class="preview-table">
          <thead>
            <tr>
              <th v-for="(column, index) in columns" :key="index">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoadingPage && paginatedRows.length === 0">
              <td :colspan="columns.length" style="text-align: center; padding: 2rem;">
                <div class="spinner-border spinner-border-sm" role="status"></div>
                <span style="margin-left: 0.5rem;">Загрузка страницы...</span>
              </td>
            </tr>
            <tr v-else v-for="(row, rowIndex) in paginatedRows" :key="rowIndex">
              <td 
                v-for="(cell, cellIndex) in row" 
                :key="cellIndex" 
                :title="cell"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Пагинация -->
      <div v-if="totalRows > 0 || paginatedRows.length > 0" class="pagination-container">
        <button 
          class="pagination-btn" 
          :disabled="currentPage === 1 || isLoadingPage"
          @click="goToPage(currentPage - 1)"
        >
          <ChevronLeft :size="16" />
        </button>
        
        <div class="pagination-pages">
          <button 
            v-for="page in visiblePages" 
            :key="page"
            class="pagination-page"
            :class="{ 'pagination-page--active': page === currentPage }"
            :disabled="isLoadingPage"
            @click="goToPage(page)"
          >
            {{ page }}
          </button>
        </div>
        
        <button 
          class="pagination-btn" 
          :disabled="currentPage === totalPages || isLoadingPage"
          @click="goToPage(currentPage + 1)"
        >
          <ChevronRight :size="16" />
        </button>
        
        <div class="pagination-goto">
          <input 
            type="number" 
            class="pagination-input"
            v-model.number="pageInput"
            :min="1"
            :max="totalPages"
            :placeholder="String(currentPage)"
            :disabled="isLoadingPage"
            @keydown.enter="goToInputPage"
          />
          <span class="pagination-goto-label">/ {{ totalPages }}</span>
          <button 
            class="pagination-goto-btn"
            :disabled="!pageInput || pageInput < 1 || pageInput > totalPages || isLoadingPage"
            @click="goToInputPage"
          >
            Перейти
          </button>
        </div>
        
        <span class="pagination-info">
          Показано {{ paginationStart }}-{{ paginationEnd }} из {{ totalRows }}
        </span>
      </div>
    </div>

    <div v-else class="preview-empty">
      <p>Таблица пуста или данные не загружены</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'

const props = defineProps({
  table: {
    type: Object,
    required: true
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

// Пагинация
const ITEMS_PER_PAGE = parseInt(import.meta.env.VITE_BI_PREVIEW_ITEMS_PER_PAGE || '200', 10)
const currentPage = ref(1)
const pageInput = ref(null)
const pagesCache = ref(new Map())
const loadingPages = ref(new Set())

// Данные
const columns = ref([])
const error = ref(null)
const isLoadingData = ref(false)
const isLoadingPage = ref(false)
const totalRows = ref(0)

// Загрузка страницы
async function loadPage(page) {
  const connectionId = props.table.connection_id
  const tableName = props.table.table_name || props.table.name
  const schema = props.table.schema || 'public'
  
  if (!connectionId || !tableName) {
    return
  }

  if (pagesCache.value.has(page) || loadingPages.value.has(page)) {
    return
  }
  
  loadingPages.value.add(page)
  isLoadingPage.value = true
  
  try {
    const offset = (page - 1) * ITEMS_PER_PAGE

    const res = await apiClient.get(biEndpoints.bi.connectionTablePreview(connectionId), {
      table_name: tableName,
      schema: schema,
      limit: ITEMS_PER_PAGE,
      offset: offset
    })

    if (res.success && res.data) {
      const responseData = res.data
      
      // Кэшируем данные страницы
      pagesCache.value.set(page, responseData.rows || [])
      
      // Обновляем общее количество строк
      if (responseData.total_count !== undefined) {
        totalRows.value = responseData.total_count
      }
      
      // Устанавливаем колонки только при первой загрузке
      if (page === 1 && responseData.columns && columns.value.length === 0) {
        columns.value = responseData.columns
      }
    } else {
      error.value = res.message || 'Ошибка загрузки данных таблицы'
    }
  } catch (err) {
    logError('Ошибка загрузки страницы:', err)
    error.value = `Ошибка загрузки: ${err.message || 'Неизвестная ошибка'}`
  } finally {
    isLoadingPage.value = false
    loadingPages.value.delete(page)
  }
}

// Переход на страницу
async function goToPage(page) {
  const total = totalPages.value
  if (page >= 1 && page <= total) {
    currentPage.value = page
    
    if (!pagesCache.value.has(page)) {
      await loadPage(page)
    }
  }
}

async function goToInputPage() {
  if (pageInput.value && pageInput.value >= 1 && pageInput.value <= totalPages.value) {
    await goToPage(pageInput.value)
    pageInput.value = null
  }
}

// Пагинированные строки
const paginatedRows = computed(() => {
  const cachedPage = pagesCache.value.get(currentPage.value)
  return cachedPage && Array.isArray(cachedPage) ? cachedPage : []
})

// Вычисляемые свойства пагинации
const totalPages = computed(() => {
  if (totalRows.value === 0) {
    const currentRows = paginatedRows.value.length
    if (currentRows > 0) return 1
    return 1
  }
  return Math.ceil(totalRows.value / ITEMS_PER_PAGE) || 1
})

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = currentPage.value
  
  if (total <= 5) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    if (current <= 3) {
      pages.push(1, 2, 3, 4, 5)
    } else if (current >= total - 2) {
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      for (let i = current - 2; i <= current + 2; i++) pages.push(i)
    }
  }
  
  return pages
})

const paginationStart = computed(() => {
  if (totalRows.value === 0) return 0
  return (currentPage.value - 1) * ITEMS_PER_PAGE + 1
})

const paginationEnd = computed(() => {
  return Math.min(currentPage.value * ITEMS_PER_PAGE, totalRows.value)
})

// Инициализация - загрузка первой страницы
async function initialize() {
  isLoadingData.value = true
  error.value = null
  
  try {
    await loadPage(1)
  } finally {
    isLoadingData.value = false
  }
}

onMounted(() => {
  if (props.table) {
    initialize()
  }
})

watch(() => props.table, (newTable) => {
  if (newTable) {
    // Сбрасываем состояние при смене таблицы
    currentPage.value = 1
    columns.value = []
    totalRows.value = 0
    pagesCache.value.clear()
    loadingPages.value.clear()
    error.value = null
    initialize()
  }
}, { deep: true })
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.table-preview {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  color: var(--color-primary-text);
  font-size: 0.875rem;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: transparent !important;
  position: relative;
}

.preview-loading,
.preview-error,
.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #6b7280;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  gap: 1rem;
}

.preview-error {
  color: var(--color-accent);
  flex-direction: column;

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
  height: 100%;
  overflow: hidden;
  gap: 1.5rem;
  max-width: 1200px;
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
  flex: 0 0 auto;
}

.preview-header h3 {
  margin: 0;
  color: var(--color-primary-text);
  font-size: 1.375rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.preview-meta {
  display: flex;
  gap: 1.5rem;
  color: var(--color-secondary-text);
  font-size: 0.875rem;
  font-weight: 500;

  span {
    padding: 0.5rem 0.875rem;
    background: rgba(255, 255, 255, 0.6);
    backdrop-filter: blur(8px);
    border-radius: 10px;
    box-shadow: 
      0 2px 8px rgba(0, 0, 0, 0.06),
      inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }
}

.preview-table-wrapper {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: 100%;
  position: relative;
  overflow: hidden;
  height: 0;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(12px);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.9) !important;
  overflow-y: auto !important;
  overflow-x: auto !important;
  
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
  
  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
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

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.4) !important;
  table-layout: fixed;
}

.preview-table thead {
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(12px);
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.preview-table thead tr:first-child th:first-child {
  border-top-left-radius: 20px;
}

.preview-table thead tr:first-child th:last-child {
  border-top-right-radius: 20px;
}

.preview-table th {
  padding: 0.875rem 1.125rem 0.875rem 0.5rem;
  text-align: left;
  font-weight: 600;
  color: var(--color-primary-text);
  white-space: nowrap;
  font-size: 0.875rem;
  background: rgba(255, 255, 255, 0.95);
  position: relative;
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 100px;
}

.preview-table td {
  padding: 0.875rem 1.125rem 0.875rem 0.5rem;
  color: var(--color-primary-text);
  transition: all 0.2s ease;
  background: transparent;
  font-size: 0.875rem;
  vertical-align: middle;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 0; /* Для работы text-overflow с table-layout: fixed */
}

.preview-table tbody tr {
  transition: all 0.2s ease;
  position: relative;
  
  // Убран ::before pseudo-element, который создавал визуальный сдвиг
  // &::before {
  //   content: '';
  //   position: absolute;
  //   left: 0;
  //   top: 0;
  //   bottom: 0;
  //   width: 3px;
  //   background: linear-gradient(180deg, 
  //     rgba(var(--bs-info-rgb), 0.5) 0%,
  //     rgba(var(--bs-primary-rgb), 0.5) 100%);
  //   transform: scaleY(0);
  //   transition: transform 0.2s ease;
  //   border-radius: 0 4px 4px 0;
  //   z-index: 1;
  // }
  
  // &:hover::before {
  //   transform: scaleY(1);
  // }
  
  &:hover {
    background: linear-gradient(90deg, rgba(var(--bs-info-rgb), 0.08) 0%, rgba(var(--bs-info-rgb), 0.04) 100%);
  }

  &:nth-child(even) {
    background-color: rgba(0, 0, 0, 0.01);

    &:hover {
      background: linear-gradient(90deg, rgba(var(--bs-info-rgb), 0.1) 0%, rgba(var(--bs-info-rgb), 0.05) 100%);
    }
  }
}

.pagination-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 0;
  margin-top: 1rem;
  border-top: 2px solid #d1d5db;
  flex-shrink: 0;
  background: white;
  border-radius: 0 0 20px 20px;
}

.pagination-btn {
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  color: #2c3e50;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  
  &:hover:not(:disabled) {
    background: var(--color-accent);
    border-color: var(--color-accent);
    color: white;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(109, 0, 26, 0.2);
  }
  
  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    background: #f5f5f5;
  }
}

.pagination-pages {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pagination-page {
  min-width: 35px;
  height: 35px;
  padding: 0 0.6rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  font-size: 0.76rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  
  &:hover:not(.pagination-page--active) {
    background: #f0f4f8;
    border-color: var(--color-accent);
    color: var(--color-accent);
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  }
  
  &--active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
    font-weight: 700;
    cursor: default;
    box-shadow: 0 2px 8px rgba(109, 0, 26, 0.3);
    transform: scale(1.05);
  }
}

.pagination-goto {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-left: 1rem;
  padding-left: 1rem;
  border-left: 2px solid #d1d5db;
}

.pagination-input {
  width: 56px;
  height: 35px;
  padding: 0 0.6rem;
  background: white;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  color: #2c3e50;
  font-size: 0.76rem;
  font-weight: 600;
  text-align: center;
  outline: none;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  
  &:focus {
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px rgba(109, 0, 26, 0.15), 0 2px 4px rgba(0, 0, 0, 0.1);
  }
  
  &::placeholder {
    color: #6b7280;
    font-weight: 400;
  }
  
  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    appearance: none;
    margin: 0;
  }
  
  & {
    -moz-appearance: textfield;
    appearance: textfield;
  }
  
  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    background: #f5f5f5;
  }
}

.pagination-goto-label {
  font-size: 0.76rem;
  font-weight: 600;
  color: #6b7280;
}

.pagination-goto-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  color: var(--color-accent);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  min-width: 72px;
  
  &:hover:not(:disabled) {
    background: var(--color-accent);
    border-color: var(--color-accent);
    color: white;
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(109, 0, 26, 0.2);
  }
  
  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    background: #f5f5f5;
  }
}

.pagination-info {
  margin-left: auto;
  margin-right: 1.25rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #6b7280;
  padding: 0.625rem 1rem;
  background: #f8f9fa;
  border-radius: 10px;
}

@media (max-width: 768px) {
  .pagination-container {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .pagination-info {
    width: 100%;
    text-align: center;
    margin-top: 8px;
  }
}
</style>