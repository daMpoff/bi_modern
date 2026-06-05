<template>
  <div class="unified-table-preview">
    <div class="toolbar">
      <!-- Настройки для CSV и TXT -->
      <template v-if="fileType === 'csv' || fileType === 'txt'">
        <div class="toolbar-group">
          <label>Кодировка</label>
          <select class="form-select form-select-sm" v-model="encoding">
            <option value="utf-8">utf-8</option>
            <option value="utf-8-sig">utf-8-sig</option>
            <option value="utf16">utf16</option>
            <option value="windows-1251">windows-1251</option>
          </select>
        </div>
        <div class="toolbar-group">
          <label>Разделитель</label>
          <select class="form-select form-select-sm" v-model="delimiter">
            <option value=",">Запятая</option>
            <option value=";">Точка с запятой</option>
            <option value="\t">Табуляция</option>
          </select>
        </div>
      </template>
      
      <!-- Общие настройки -->
      <div class="toolbar-group">
        <label>Заголовок столбцов</label>
        <div class="toggle-group">
          <button :class="{ active: hasHeader }" @click.stop="toggleHasHeader(true)">Да</button>
          <button :class="{ active: !hasHeader }" @click.stop="toggleHasHeader(false)">Нет</button>
        </div>
      </div>
      
      <div class="toolbar-group search-wrapper">
        <input 
          class="form-control" 
          type="text" 
          placeholder="Поиск по таблице"
          v-model="searchQuery" 
        />
      </div>
    </div>

    <div v-if="errorState" class="error-message">
      <h2>Ошибка</h2>
      <p>{{ errorState }}</p>
    </div>

    <div class="table-container" v-if="columns.length > 0 && !errorState">
      <div class="table-header-wrapper" ref="headerWrapperRef">
        <div class="table-header-fixed" ref="headerRef">
          <div 
            class="table-row header-row"
            :style="headerRowStyle"
          >
            <div 
              v-for="(col, index) in columns" 
              :key="index"
              class="table-cell header-cell"
              :style="getHeaderCellStyle(index)"
              :title="'Нажмите, чтобы скопировать столбец в CSV'"
            >
              <div class="col-header">
                <div 
                  v-if="fileType === 'csv' || fileType === 'txt'"
                  class="type-button-wrapper" 
                  @click.stop="toggleMenu(index)" 
                  :title="typeLabels[columnTypes[index]] || 'Тип данных'"
                >
                  <component 
                    :is="typeIcons[columnTypes[index]] || Type" 
                    :size="16" 
                    class="type-icon"
                  />
                  <div v-if="activeMenuIndex === index" class="type-menu">
                    <div
                      v-for="type in getAllowedTypes(index)"
                      :key="type"
                      :class="['type-option', { active: columnTypes[index] === type }]"
                      @click.stop="setType(index, type)"
                    >
                      <component :is="typeIcons[type] || Type" :size="14" />
                      {{ typeLabels[type] }}
                    </div>
                  </div>
                </div>
                <component 
                  v-else 
                  :is="typeIcons[columnTypes[index]] || Type" 
                  :size="16" 
                  class="type-icon-static"
                />
                <span class="col-name" :title="col" @click.stop="copyColumnToCSV(index, $event)">{{ col }}</span>
              </div>
              <!-- Ресайзер столбца -->
              <div 
                class="column-resizer"
                @mousedown.stop="startResize(index, $event)"
                :title="'Перетащите для изменения ширины столбца'"
              ></div>
            </div>
          </div>
        </div>
      </div>
      
      <RecycleScroller
        ref="scrollerRef"
        class="scroller"
        :items="paginatedRows"
        :item-size="rowHeight"
        key-field="__index"
        :page-mode="false"
        :buffer="200"
        :min-item-size="rowHeight"
        v-slot="{ item, index }"
      >
        <div 
          class="table-row" 
          :class="{ 
            selected: selectedRow === index,
            'row-even': index % 2 === 0,
            'row-odd': index % 2 === 1
          }"
          :style="getRowStyle(index)"
          @click="selectRow(index)"
          @mouseenter="handleRowHover($event, index, true)"
          @mouseleave="handleRowHover($event, index, false)"
        >
          <div 
            v-for="(colIndex) in columns.length" 
            :key="colIndex - 1"
            class="table-cell"
            :style="getCellStyle(colIndex - 1)"
          >
            <span 
              style="display: block; width: 100%;" 
              v-html="getHighlightedCellValue(item, colIndex - 1)"
            ></span>
          </div>
        </div>
      </RecycleScroller>
      
      <!-- Пагинация -->
      <div v-if="totalRowsCount > 0 || paginatedRows.length > 0" class="pagination-container">
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
          Показано {{ paginationStart }}-{{ paginationEnd }} из {{ totalRowsCount }}
        </span>
      </div>
      
      <!-- Состояния загрузки и пустых данных -->
      <div v-if="(isLoading || isLoadingPage || isSearchDataLoading) && paginatedRows.length === 0 && !errorState" class="table-loading">
        <div class="spinner-border spinner-border-sm" role="status">
          <span class="visually-hidden">Загрузка...</span>
        </div>
        <span>{{ isSearchDataLoading ? 'Загрузка данных для поиска...' : 'Загрузка данных...' }}</span>
      </div>
      
      <div v-if="!isLoading && !isLoadingPage && paginatedRows.length === 0 && !errorState" class="table-empty">
        <p v-if="debouncedSearchQuery">По запросу "{{ debouncedSearchQuery }}" ничего не найдено</p>
        <p v-else>Нет данных для отображения</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick, watchEffect } from 'vue'
import { ChevronLeft, ChevronRight, Type, Hash, Percent } from 'lucide-vue-next'
import { RecycleScroller } from 'vue-virtual-scroller'
import 'vue-virtual-scroller/dist/vue-virtual-scroller.css'
import { apiClient } from '@/js/api/manager'
import { endpoints } from '@/js/api/endpoints'

const props = defineProps({ 
  file: Object,
  isLoading: Boolean
})

// Определение типа файла
const fileType = computed(() => {
  if (!props.file) return null
  
  // Приоритет: расширение файла > file_type
  if (props.file.name) {
    const ext = props.file.name.toLowerCase().split('.').pop()
    if (ext === 'csv') return 'csv'
    if (ext === 'txt') return 'txt'
    if (ext === 'xlsx' || ext === 'xls') return 'xlsx'
  }
  
  // Проверяем file_type
  if (props.file.file_type) {
    const type = props.file.file_type.toLowerCase()
    if (type === 'csv' || type === 'txt') return type
    if (type === 'xlsx' || type === 'xls') return 'xlsx'
  }
  
  return null
})

// Общие настройки
const hasHeader = ref(true)

// Отслеживание изменений hasHeader для отладки
watch(hasHeader, (newVal, oldVal) => {
  console.log('hasHeader changed:', { oldVal, newVal, stack: new Error().stack })
})
const searchQuery = ref('')
const debouncedSearchQuery = ref('')
const errorState = ref(null)
const selectedRow = ref(null)
// Сохраняем первую строку файла (заголовки) для восстановления при hasHeader = false
const savedFirstRow = ref(null)
const rowHeight = 44
const scrollerRef = ref(null)
const headerRef = ref(null)
const headerWrapperRef = ref(null)
const isLoadingPage = ref(false)

// Настройки для CSV/TXT
const encoding = ref('utf-8')
const delimiter = ref(',')

// Пагинация
const ITEMS_PER_PAGE = parseInt(import.meta.env.VITE_BI_PREVIEW_ITEMS_PER_PAGE || '200', 10)
const currentPage = ref(1)
const pageInput = ref(null)
const totalRowsCount = ref(0)
const pagesCache = ref(new Map())
const loadingPages = ref(new Set())

// Данные
const rawData = ref([])
const columnTypes = ref([])
const activeMenuIndex = ref(null)

// Кэш для данных поиска (для серверных файлов)
const searchDataCache = ref(null)
const isSearchDataLoading = ref(false)

// Изменение ширины столбцов
const resizableColumnWidths = ref({})
const resizingColumn = ref(null)
const resizingStartX = ref(0)
const resizingStartWidth = ref(0)

// Типы данных
const typeLabels = {
  string: 'Строка',
  integer: 'Целое число',
  float: 'Дробное число'
}

const typeIcons = {
  string: Type,
  integer: Hash,
  float: Percent
}

const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

// Дебаунс для поиска
let searchDebounceTimer = null
watch(searchQuery, (newVal) => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(async () => {
    debouncedSearchQuery.value = newVal
    
    // При начале поиска сбрасываем на первую страницу
    if (newVal) {
      currentPage.value = 1
      // Очищаем кэш отфильтрованных строк при изменении запроса
      cachedFilteredRows = null
      cachedFilterQuery = null
      cachedRowsData = null
      
      // Для серверных файлов загружаем все данные при поиске
      if ((!props.file?.originalFile || !(props.file?.originalFile instanceof Blob)) && (props.file?.id || props.file?.temp_path)) {
        await loadAllDataForSearch()
      }
    } else {
      // При очистке поиска очищаем кэш поиска
      searchDataCache.value = null
    }
  }, 300)
})

// Стили для строк и ячеек
const headerRowStyle = {
  backgroundColor: 'rgba(255, 255, 255, 0.95)',
  backdropFilter: 'blur(12px)',
  fontWeight: '600',
  fontSize: '0.875rem',
  color: 'var(--color-primary-text)',
  cursor: 'default',
  display: 'flex',
  minHeight: '48px',
  width: 'max-content',
  minWidth: '100%',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
}

function getHeaderCellStyle(index) {
  // Используем ту же ширину, что и для ячеек данных
  const cellWidth = columnWidths.value[index] || '150px'
  
  return {
    width: cellWidth,
    minWidth: '150px',
    padding: '0.875rem 1.125rem 0.875rem 0.5rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-start',
    flexShrink: 0,
    fontSize: '0.875rem',
    lineHeight: '1.5',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(12px)',
    fontWeight: '600',
    color: 'var(--color-primary-text)',
    position: 'relative',
    cursor: 'pointer'
  }
}

function getRowStyle(index) {
  const isSelected = selectedRow.value === index
  const isEven = index % 2 === 0
  
  return {
    backgroundColor: isSelected 
      ? 'rgba(var(--bs-info-rgb), 0.1)' 
      : isEven 
        ? 'rgba(255, 255, 255, 0.8)' 
        : 'rgba(0, 0, 0, 0.015)',
    minHeight: '44px',
    cursor: 'pointer',
    display: 'flex',
    width: 'max-content',
    minWidth: '100%',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    position: 'relative'
  }
}

function handleRowHover(event, index, isEntering) {
  const isSelected = selectedRow.value === index
  const isEven = index % 2 === 0
  
  if (isEntering && !isSelected) {
    event.currentTarget.style.backgroundColor = 'rgba(var(--bs-info-rgb), 0.08)'
    event.currentTarget.style.transform = 'translateX(2px)'
  } else if (!isEntering && !isSelected) {
    event.currentTarget.style.backgroundColor = isEven 
      ? 'rgba(255, 255, 255, 0.8)' 
      : 'rgba(0, 0, 0, 0.015)'
    event.currentTarget.style.transform = 'translateX(0)'
  }
}

function getCellStyle(colIndex) {
  return {
    width: columnWidths.value[colIndex] || '150px',
    minWidth: '150px',
    padding: '0.875rem 1.125rem 0.875rem 0.5rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-start',
    flexShrink: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    fontSize: '0.9rem',
    lineHeight: '1.5',
    backgroundColor: 'transparent',
    color: 'var(--color-primary-text)'
  }
}

function getCellValue(item, colIndex) {
  if (!item || !item._cells) return ''
  const cell = item._cells[colIndex]
  return cell == null ? '' : String(cell)
}

// Подсветка найденного текста в ячейке
function getHighlightedCellValue(item, colIndex) {
  const cellValue = getCellValue(item, colIndex)
  
  // Если нет поискового запроса, возвращаем обычное значение
  if (!debouncedSearchQuery.value || !cellValue) {
    return escapeHtml(cellValue)
  }
  
  // Экранируем HTML в исходном значении для безопасности
  const escapedValue = escapeHtml(cellValue)
  const query = escapeHtml(debouncedSearchQuery.value)
  
  // Ищем все вхождения (case-insensitive)
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  const highlighted = escapedValue.replace(regex, '<mark class="search-highlight">$1</mark>')
  
  return highlighted
}

// Экранирование HTML для безопасности
function escapeHtml(text) {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// Изменение ширины столбцов
function startResize(columnIndex, event) {
  event.preventDefault()
  resizingColumn.value = columnIndex
  resizingStartX.value = event.clientX
  
  // Получаем текущую ширину столбца
  const currentWidth = columnWidths.value[columnIndex]
  if (currentWidth) {
    // Извлекаем число из строки вида "150px"
    const widthValue = parseInt(currentWidth, 10)
    resizingStartWidth.value = widthValue
  } else {
    resizingStartWidth.value = 150 // Минимальная ширина по умолчанию
  }
  
  // Добавляем обработчики событий для перетаскивания
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  
  // Меняем курсор на resize
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function handleResize(event) {
  if (resizingColumn.value === null) return
  
  const deltaX = event.clientX - resizingStartX.value
  const newWidth = Math.max(120, resizingStartWidth.value + deltaX) // Минимальная ширина 120px
  
  // Обновляем пользовательскую ширину столбца
  resizableColumnWidths.value[resizingColumn.value] = newWidth
  
  // Очищаем кэш ширин, чтобы применить изменения
  cachedColumnWidths = null
  cachedColumnsForWidths = null
}

function stopResize() {
  if (resizingColumn.value === null) return
  
  resizingColumn.value = null
  
  // Удаляем обработчики событий
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  
  // Восстанавливаем курсор и выделение текста
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

function selectRow(index) {
  selectedRow.value = selectedRow.value === index ? null : index
}

function toggleMenu(index) {
  activeMenuIndex.value = activeMenuIndex.value === index ? null : index
}

function setType(index, type) {
  columnTypes.value[index] = type
  activeMenuIndex.value = null
}

// Копирование столбца в CSV формате с заголовком
async function copyColumnToCSV(columnIndex, event) {
  // Игнорируем клики на кнопку выбора типа
  if (event && event.target && event.target.closest('.type-button-wrapper')) {
    return
  }
  
  // Игнорируем клики на меню выбора типа
  if (event && event.target && event.target.closest('.type-menu')) {
    return
  }
  
  // Останавливаем всплытие события, чтобы не триггерить другие обработчики
  if (event) {
    event.stopPropagation()
    event.stopImmediatePropagation()
    // НЕ вызываем preventDefault(), так как это может вызвать нежелательные побочные эффекты
  }
  
  // Сохраняем текущее состояние hasHeader перед операцией
  const headerStateBefore = hasHeader.value
  
  console.log('copyColumnToCSV called', { columnIndex, fileType: fileType.value, hasHeader: hasHeader.value, headerStateBefore })
  
  try {
    const columnName = columns.value[columnIndex] || ''
    console.log('Column name:', columnName, 'Columns:', columns.value)
    
    // Получаем все данные столбца из всех страниц
    const allColumnData = []
    
    // Добавляем заголовок
    allColumnData.push(columnName)
    
    // Получаем данные из текущих загруженных страниц
    for (const pageData of pagesCache.value.values()) {
      let dataRows = pageData
      
      // Если есть заголовок, пропускаем первую строку
      if (hasHeader.value && dataRows.length > 0) {
        dataRows = dataRows.slice(1)
      }
      
      for (const row of dataRows) {
        if (Array.isArray(row) && row[columnIndex] !== undefined) {
          const cellValue = String(row[columnIndex] || '')
          // Экранируем значения, если они содержат разделитель или кавычки
          const escapedValue = cellValue.includes(delimiter.value) || 
                               cellValue.includes('"') || 
                               cellValue.includes('\n') 
            ? `"${cellValue.replace(/"/g, '""')}"` 
            : cellValue
          allColumnData.push(escapedValue)
        }
      }
    }
    
    // Если кэш пуст, используем текущие данные
    if (allColumnData.length === 1) {
      // Добавляем данные из текущих отфильтрованных строк
      for (const row of filteredRows.value) {
        const cellValue = getCellValue(row, columnIndex)
        const escapedValue = cellValue.includes(delimiter.value) || 
                             cellValue.includes('"') || 
                             cellValue.includes('\n') 
          ? `"${cellValue.replace(/"/g, '""')}"` 
          : cellValue
        allColumnData.push(escapedValue)
      }
    }
    
    // Объединяем в CSV строку (каждое значение на новой строке)
    const csvContent = allColumnData.join('\n')
    
    console.log('CSV content:', csvContent)
    console.log('All column data:', allColumnData)
    
    // Копируем в буфер обмена
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(csvContent)
      // Можно добавить визуальную обратную связь через console или небольшое уведомление
      console.log(`Столбец "${columnName}" скопирован в буфер обмена. Строк: ${allColumnData.length}`)
    } else {
      // Fallback для старых браузеров
      const textArea = document.createElement('textarea')
      textArea.value = csvContent
      textArea.style.position = 'fixed'
      textArea.style.opacity = '0'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      console.log(`Столбец "${columnName}" скопирован в буфер обмена`)
    }
    
    // Проверяем, не изменилось ли состояние hasHeader после операции
    if (hasHeader.value !== headerStateBefore) {
      console.warn('hasHeader изменилось после copyColumnToCSV!', { 
        before: headerStateBefore, 
        after: hasHeader.value,
        columnIndex 
      })
      // Восстанавливаем исходное состояние
      hasHeader.value = headerStateBefore
    }
  } catch (error) {
    console.error('Ошибка копирования столбца:', error)
    // Восстанавливаем исходное состояние при ошибке
    if (hasHeader.value !== headerStateBefore) {
      hasHeader.value = headerStateBefore
    }
  }
}

// Переключение hasHeader
function toggleHasHeader(value) {
  console.log('toggleHasHeader called', { value, currentValue: hasHeader.value, savedFirstRow: savedFirstRow.value })
  if (hasHeader.value !== value) {
    // При переключении с true на false: если есть сохраненная первая строка, добавляем её в rawData
    if (!value && savedFirstRow.value && rawData.value && rawData.value.length > 0) {
      // Проверяем, что первой строки нет в rawData (сервер не вернул её)
      if (rawData.value[0]?.[0] !== savedFirstRow.value[0]) {
        rawData.value = [savedFirstRow.value, ...rawData.value]
        console.log('Added saved first row to rawData', { rawDataLength: rawData.value.length })
      }
    }
    
    // Очищаем кэши перед изменением hasHeader
    pagesCache.value.clear()
    cachedColumnWidths = null
    cachedColumnsForWidths = null
    cachedFilteredRows = null
    cachedFilterQuery = null
    cachedRowsData = null
    
    // Если данные уже загружены и файл локальный, обновляем rawData
    if (props.file?.originalFile instanceof File || props.file?.originalFile instanceof Blob) {
      // rawData будет обновлен в watcher через previewLocally
    } else if (props.file?.id || props.file?.temp_path) {
      // Для серверных файлов не очищаем rawData, так как мы уже добавили первую строку выше
      // Если данных нет, очищаем чтобы загрузить заново
      if (!rawData.value || rawData.value.length === 0) {
        rawData.value = []
      }
    }
    
    hasHeader.value = value
    console.log('hasHeader updated to:', hasHeader.value, { rawDataLength: rawData.value?.length })
  } else {
    console.log('hasHeader already set to:', value)
  }
}

function getAllowedTypes(colIndex) {
  if (fileType.value !== 'csv' && fileType.value !== 'txt') return []
  
  const values = rows.value.map(row => row[colIndex])
  let isInt = true
  let isFloat = true

  for (const val of values) {
    if (val === '') continue
    if (!/^[-+]?\d+$/.test(val)) isInt = false
    if (!/^[-+]?\d*(\.\d+)?$/.test(val)) isFloat = false
  }

  if (isInt) return ['string', 'integer', 'float']
  if (isFloat) return ['string', 'float']
  return ['string']
}

function handleClickOutside(event) {
  const menus = document.querySelectorAll('.type-menu')
  if (![...menus].some(menu => menu.contains(event.target))) {
    activeMenuIndex.value = null
  }
}

// Загрузка всех данных для поиска (для серверных файлов)
async function loadAllDataForSearch() {
  if (!props.file) return
  if (!props.file?.id && !props.file?.temp_path) return
  if (isSearchDataLoading.value) return // Уже загружаем
  
  isSearchDataLoading.value = true
  
  try {
    const fileId = props.file.id || props.file.temp_path
    let params = {}
    
    // Загружаем все данные без limit для поиска по всему файлу
    if (fileType.value === 'csv' || fileType.value === 'txt') {
      params = {
        has_header: hasHeader.value,
        // Не передаем limit, чтобы загрузить все данные
        offset: 0,
        encoding: encoding.value,
        delimiter: delimiter.value
      }
    } else if (fileType.value === 'xlsx') {
      params = {
        has_header: hasHeader.value,
        // Не передаем limit, чтобы загрузить все данные
        offset: 0,
        sheet_name: props.file.sheet
      }
    }
    
    const res = await apiClient.get(`${endpoints.bi.Upload}${fileId}/`, params)
    
    if (res.success && res.data?.parsed) {
      let parsed = res.data.parsed.map(row => row.map(cell => cell == null ? '' : String(cell)))
      
      // Применяем hasHeader логику для поиска
      searchDataCache.value = parsed
      
      console.log('Загружены все данные для поиска:', { totalRows: parsed.length })
    }
  } catch (err) {
    console.error('Ошибка загрузки всех данных для поиска:', err)
  } finally {
    isSearchDataLoading.value = false
  }
}

// Загрузка страницы
async function loadPage(page) {
  if (!props.file) return
  if (!props.file?.id && !props.file?.temp_path) return
  
  if (pagesCache.value.has(page) || loadingPages.value.has(page)) {
    return
  }
  
  loadingPages.value.add(page)
  isLoadingPage.value = true
  
  try {
    const offset = (page - 1) * ITEMS_PER_PAGE
    const fileId = props.file.id || props.file.temp_path
    let params = {}
    
    if (fileType.value === 'csv' || fileType.value === 'txt') {
      params = {
        has_header: hasHeader.value,
        limit: ITEMS_PER_PAGE,
        offset: offset,
        encoding: encoding.value,
        delimiter: delimiter.value
      }
    } else if (fileType.value === 'xlsx') {
      params = {
        has_header: hasHeader.value,
        limit: ITEMS_PER_PAGE,
        offset: offset,
        sheet_name: props.file.sheet
      }
    }
    
    const res = await apiClient.get(`${endpoints.bi.Upload}${fileId}/`, params)
    
    if (res.success && res.data?.parsed) {
      let parsed = res.data.parsed.map(row => row.map(cell => cell == null ? '' : String(cell)))
      
      // При hasHeader = true сохраняем первую строку для восстановления при hasHeader = false
      if (hasHeader.value && parsed.length > 0 && page === 1) {
        savedFirstRow.value = [...parsed[0]]
      }
      
      // При hasHeader = false и если есть сохраненная первая строка, добавляем её в начало для первой страницы
      if (!hasHeader.value && savedFirstRow.value && page === 1) {
        parsed = [savedFirstRow.value, ...parsed]
      }
      
      pagesCache.value.set(page, parsed)
      
      if (res.data.total_count !== undefined && res.data.total_count !== null) {
        // Для серверных файлов total_count учитывает hasHeader на стороне сервера
        // При hasHeader = false: total_count включает первую строку
        // При hasHeader = true: total_count не включает первую строку (она используется как заголовки)
        totalRowsCount.value = res.data.total_count
      } else {
        // При hasHeader = false: все строки включая первую считаются как данные
        // При hasHeader = true: первая строка исключается из подсчета
        const loadedRows = hasHeader.value && parsed.length > 0 ? parsed.length - 1 : parsed.length
        if (loadedRows === ITEMS_PER_PAGE) {
          const minTotal = offset + loadedRows + 1
          if (totalRowsCount.value < minTotal) {
            totalRowsCount.value = minTotal
          }
        } else {
          totalRowsCount.value = offset + loadedRows
        }
      }
      
      if (page === currentPage.value) {
        rawData.value = parsed
        
        // Если это первая страница и hasHeader = false, и есть сохраненная первая строка, добавляем её в rawData
        if (!hasHeader.value && savedFirstRow.value && page === 1 && rawData.value[0]?.[0] !== savedFirstRow.value[0]) {
          rawData.value = [savedFirstRow.value, ...rawData.value]
        }
        
        if (fileType.value === 'csv' || fileType.value === 'txt') {
          detectTypes()
        } else if (fileType.value === 'xlsx' && columnTypes.value.length === 0 && columns.value.length > 0) {
          columnTypes.value = Array(columns.value.length).fill('string')
        }
      }
    } else {
      errorState.value = `Ошибка загрузки данных: ${res.message || 'Неизвестная ошибка'}`
    }
  } catch (err) {
    errorState.value = `Ошибка загрузки: ${err.message}`
  } finally {
    isLoadingPage.value = false
    loadingPages.value.delete(page)
  }
}

// Форматирование даты для XLSX
function formatDate(value) {
  if (value instanceof Date) {
    return value.toISOString().split('T')[0]
  }
  return value
}

// Переход на страницу
async function goToPage(page) {
  const total = totalPages.value
  if (page >= 1 && page <= total) {
    currentPage.value = page
    
    if (!pagesCache.value.has(page)) {
      await loadPage(page)
    } else {
      rawData.value = pagesCache.value.get(page)
      if (fileType.value === 'csv' || fileType.value === 'txt') {
        detectTypes()
      }
    }
  }
}

async function goToInputPage() {
  if (pageInput.value && pageInput.value >= 1 && pageInput.value <= totalPages.value) {
    await goToPage(pageInput.value)
    pageInput.value = null
  }
}

// Колонки
const columns = computed(() => {
  const cachedPage = pagesCache.value.get(currentPage.value)
  const dataSource = cachedPage || rawData.value
  
  if (!dataSource || !dataSource.length) return []
  
  const firstRow = dataSource[0]
  if (!firstRow || !Array.isArray(firstRow)) return []
  
  if (hasHeader.value) {
    // При hasHeader = true: первая строка используется как заголовки столбцов
    return firstRow
  }
  // При hasHeader = false: генерируем заголовки a, b, c
  // Первая строка файла (id, order_id, amount) будет отображаться как первая строка данных
  return firstRow.map((_, i) => alphabet[i] || `Col ${i + 1}`)
})

// Строки
// При hasHeader = false первая строка отображается как данные (id, order_id, amount)
// При hasHeader = true первая строка используется только как заголовки столбцов и НЕ отображается в данных
const rows = computed(() => {
  if (!rawData.value || !rawData.value.length) return []
  
  // При hasHeader = false: все строки включая первую (id, order_id, amount) отображаются как данные
  // При hasHeader = true: первая строка исключается из данных, используется только как заголовки
  const result = hasHeader.value ? rawData.value.slice(1) : rawData.value
  console.log('rows computed', { 
    hasHeader: hasHeader.value, 
    rawDataLength: rawData.value.length, 
    resultLength: result.length,
    firstRow: rawData.value[0],
    firstResultRow: result[0]
  })
  return result
})

// Кэш для фильтрации
let cachedFilteredRows = null
let cachedFilterQuery = null
let cachedRowsData = null

// Фильтрация - поиск по всей таблице
const filteredRows = computed(() => {
  // Для поиска используем все данные из rawData, а не только текущую страницу
  // Для локальных файлов: rawData содержит все данные
  // Для серверных файлов при поиске: используем searchDataCache (все данные файла)
  let dataRows
  
  // Если файл локальный, используем все данные из rawData для поиска
  if (props.file?.originalFile instanceof File || props.file?.originalFile instanceof Blob) {
    // Для локальных файлов rawData содержит все данные, применяем hasHeader логику
    if (!rawData.value || !rawData.value.length) {
      return []
    }
    dataRows = hasHeader.value ? rawData.value.slice(1) : rawData.value
  } else {
    // Для серверных файлов при поиске используем searchDataCache (все данные)
    // Если поисковый запрос есть, но searchDataCache пуст, используем загруженные страницы
    if (debouncedSearchQuery.value) {
      if (searchDataCache.value && searchDataCache.value.length > 0) {
        // Используем все данные из кэша поиска
        dataRows = hasHeader.value && searchDataCache.value.length > 0 
          ? searchDataCache.value.slice(1) 
          : searchDataCache.value
      } else {
        // Если кэш поиска пуст, собираем данные из всех загруженных страниц
        const allData = []
        for (const pageData of pagesCache.value.values()) {
          const dataForPage = hasHeader.value && pageData.length > 0 ? pageData.slice(1) : pageData
          allData.push(...dataForPage)
        }
        dataRows = allData
      }
    } else {
      // Без поиска используем данные текущей страницы (rows.value)
      dataRows = rows.value
    }
  }
  
  if (cachedFilteredRows && 
      cachedFilterQuery === debouncedSearchQuery.value && 
      cachedRowsData === dataRows) {
    return cachedFilteredRows
  }
  
  let result
  
  if (!debouncedSearchQuery.value) {
    result = dataRows.map((row, idx) => ({
      __index: idx,
      _cells: row
    }))
  } else {
    const query = debouncedSearchQuery.value.toLowerCase()
    const results = []
    
    // Поиск по всем строкам данных
    for (let i = 0; i < dataRows.length; i++) {
      const row = dataRows[i]
      if (Array.isArray(row) && row.some(cell => String(cell).toLowerCase().includes(query))) {
        results.push({ 
          __index: i,
          _cells: row
        })
      }
    }
    
    result = results
  }
  
  cachedFilteredRows = result
  cachedFilterQuery = debouncedSearchQuery.value
  cachedRowsData = dataRows
  
  return result
})

// Пагинированные строки
const paginatedRows = computed(() => {
  if (debouncedSearchQuery.value) {
    const start = (currentPage.value - 1) * ITEMS_PER_PAGE
    const end = start + ITEMS_PER_PAGE
    return filteredRows.value.slice(start, end)
  }
  
  const cachedPage = pagesCache.value.get(currentPage.value)
  if (cachedPage && Array.isArray(cachedPage) && cachedPage.length > 0) {
    // cachedPage уже содержит данные для текущей страницы (загруженные через loadPage)
    // Применяем hasHeader логику и возвращаем все строки из кэша
    let dataRows = cachedPage
    
    // При hasHeader = false: все строки включая первую (id, order_id, amount) отображаются как данные
    // При hasHeader = true: первая строка исключается из данных
    if (hasHeader.value && dataRows.length > 0) {
      dataRows = dataRows.slice(1)
    }
    
    // cachedPage уже содержит данные для одной страницы, не нужно применять slice(start, end)
    const offset = (currentPage.value - 1) * ITEMS_PER_PAGE
    return dataRows.map((row, idx) => ({
      __index: offset + idx,
      _cells: Array.isArray(row) ? row : []
    }))
  }
  
  if (rawData.value && Array.isArray(rawData.value) && rawData.value.length > 0) {
    // При hasHeader = false: все строки включая первую (id, order_id, amount) отображаются как данные
    // При hasHeader = true: первая строка исключается из данных
    const dataRows = hasHeader.value ? rawData.value.slice(1) : rawData.value
    const start = (currentPage.value - 1) * ITEMS_PER_PAGE
    const end = start + ITEMS_PER_PAGE
    return dataRows.slice(start, end).map((row, idx) => ({
      __index: start + idx,
      _cells: Array.isArray(row) ? row : []
    }))
  }
  
  return []
})

// Пагинация
const totalPages = computed(() => {
  // При поиске используем количество отфильтрованных строк
  if (debouncedSearchQuery.value) {
    const filteredCount = filteredRows.value.length
    if (filteredCount === 0) return 1
    return Math.ceil(filteredCount / ITEMS_PER_PAGE) || 1
  }
  if (totalRowsCount.value === 0) {
    const currentRows = paginatedRows.value.length
    if (currentRows > 0) return 1
    return 1
  }
  return Math.ceil(totalRowsCount.value / ITEMS_PER_PAGE) || 1
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
  // При поиске используем количество отфильтрованных строк
  if (debouncedSearchQuery.value) {
    if (filteredRows.value.length === 0) return 0
    return (currentPage.value - 1) * ITEMS_PER_PAGE + 1
  }
  if (totalRowsCount.value === 0) return 0
  return (currentPage.value - 1) * ITEMS_PER_PAGE + 1
})

const paginationEnd = computed(() => {
  // При поиске используем количество отфильтрованных строк
  if (debouncedSearchQuery.value) {
    const end = currentPage.value * ITEMS_PER_PAGE
    return Math.min(end, filteredRows.value.length)
  }
  return Math.min(currentPage.value * ITEMS_PER_PAGE, totalRowsCount.value)
})

// Ширина колонок
let cachedColumnWidths = null
let cachedColumnsForWidths = null

const columnWidths = computed(() => {
  if (!columns.value.length) return []
  
  const widths = []
  
  // Используем пользовательские ширины, если они заданы, иначе вычисляем автоматически
  for (let i = 0; i < columns.value.length; i++) {
    if (resizableColumnWidths.value[i] !== undefined) {
      // Используем пользовательскую ширину
      widths.push(resizableColumnWidths.value[i] + 'px')
    } else {
      // Вычисляем автоматическую ширину
      if (cachedColumnWidths && 
          cachedColumnsForWidths === columns.value && 
          cachedColumnsForWidths.length === columns.value.length) {
        widths.push(cachedColumnWidths[i])
      } else {
        const minWidth = 120
        const maxWidth = 400
        
        const sampleSize = Math.min(50, filteredRows.value.length)
        const sampleRows = filteredRows.value.slice(0, sampleSize)
        
        const colName = String(columns.value[i])
        let maxLength = colName.length
        
        for (let j = 0; j < sampleRows.length; j++) {
          const cell = sampleRows[j]._cells ? sampleRows[j]._cells[i] : ''
          const cellLength = String(cell || '').length
          if (cellLength > maxLength) {
            maxLength = cellLength
          }
        }
        
        const calculatedWidth = Math.min(Math.max(maxLength * 10 + 40, minWidth), maxWidth)
        widths.push(calculatedWidth + 'px')
      }
    }
  }
  
  // Кэшируем вычисленные ширины только если нет пользовательских
  if (Object.keys(resizableColumnWidths.value).length === 0) {
    cachedColumnWidths = widths
    cachedColumnsForWidths = columns.value
  }
  
  return widths
})

// Определение типов (только для CSV/TXT)
function detectTypes() {
  if (fileType.value !== 'csv' && fileType.value !== 'txt') return
  
  const types = []
  const dataRows = rows.value
  if (!dataRows.length) return

  const sampleSize = Math.min(500, dataRows.length)
  const sampleRows = dataRows.slice(0, sampleSize)

  for (let i = 0; i < (dataRows[0]?.length || 0); i++) {
    const values = sampleRows.map(row => row[i]).filter(val => val !== '')
    if (values.length === 0) {
      types.push('string')
      continue
    }

    let isInt = true
    let isFloat = true

    for (const val of values) {
      if (val === '') continue
      const str = String(val)
      
      if (isInt && !/^[-+]?\d+$/.test(str)) isInt = false
      if (isFloat && !/^[-+]?\d*(\.\d+)?$/.test(str)) isFloat = false
      if (!isInt && !isFloat) break
    }

    if (isInt) types.push('integer')
    else if (isFloat) types.push('float')
    else types.push('string')
  }

  columnTypes.value = types
}

// Обновление totalRowsCount на основе rawData и hasHeader
function updateTotalRowsCount() {
  if (!rawData.value || !rawData.value.length) {
    totalRowsCount.value = 0
    return
  }
  
  // При hasHeader = false: все строки включая первую (id, order_id, amount) считаются как данные
  // При hasHeader = true: первая строка исключается из подсчета (используется только как заголовки)
  const dataRows = hasHeader.value ? rawData.value.slice(1) : rawData.value
  totalRowsCount.value = dataRows.length
}

// Загрузка локальных файлов
async function previewLocally(file) {
  errorState.value = null

  try {
    if (fileType.value === 'csv' || fileType.value === 'txt') {
      const text = await file.text()
      const sep = delimiter.value === '\\t' ? '\t' : delimiter.value
      const lines = text.split(/\r?\n/).filter(line => line.trim() !== '')
      // Всегда парсим файл заново, НЕ добавляем заголовки a, b, c в данные
      // Заголовки a, b, c генерируются только в columns computed, когда hasHeader = false
      const parsed = lines.map(line => line.split(sep))

      // При hasHeader = true сохраняем первую строку для восстановления при hasHeader = false
      if (hasHeader.value && parsed.length > 0) {
        savedFirstRow.value = [...parsed[0]]
      }

      rawData.value = parsed
      detectTypes()
      // Обновляем totalRowsCount после загрузки данных
      updateTotalRowsCount()
    } else if (fileType.value === 'xlsx') {
      if (!(file instanceof Blob)) throw new Error('Требуется файл типа Blob')
      
      const ExcelJSModule = await import('exceljs')
      const ExcelJS = ExcelJSModule.default || ExcelJSModule.ExcelJS || ExcelJSModule
      const Workbook = ExcelJS.Workbook || ExcelJS
      
      if (typeof Workbook !== 'function') {
        throw new Error('Workbook не является конструктором')
      }
      
      const workbook = new Workbook()
      const reader = new FileReader()
      
      await new Promise((resolve, reject) => {
        reader.onload = async (e) => {
          try {
            await workbook.xlsx.load(e.target.result)
            const worksheet = props.file.sheet
              ? workbook.getWorksheet(props.file.sheet)
              : workbook.worksheets[0]
            if (!worksheet) return reject(new Error('Не найден лист'))
            
            const parsed = []
            worksheet.eachRow({ includeEmpty: true }, (row) => {
              parsed.push(row.values.slice(1).map(cell => {
                if (cell == null) return ''
                if (cell instanceof Date) return formatDate(cell)
                return String(cell)
              }))
            })
            
            // НЕ добавляем заголовки a, b, c в данные для XLSX
            // Заголовки a, b, c генерируются только в columns computed, когда hasHeader = false
            
            rawData.value = parsed
            if (columnTypes.value.length === 0 && columns.value.length > 0) {
              columnTypes.value = Array(columns.value.length).fill('string')
            }
            
            resolve(parsed)
          } catch (err) {
            reject(err)
          }
        }
        reader.onerror = () => reject(reader.error)
        reader.readAsArrayBuffer(file)
      })
    }
    
    cachedColumnWidths = null
    cachedColumnsForWidths = null
    
    // Для локальных файлов пересчитываем количество строк данных
    updateTotalRowsCount()
  } catch (err) {
    errorState.value = `Ошибка чтения файла: ${err.message}`
    rawData.value = []
  }
}

// Синхронизация скролла
function setupScrollSync() {
  if (!scrollerRef.value || !headerWrapperRef.value) return
  
  const scroller = scrollerRef.value
  const headerWrapper = headerWrapperRef.value
  
  const actualScrollElement = scroller._actualScrollElement || scroller.$el || scroller
  
  if (!actualScrollElement) return
  
  const syncBodyToHeader = () => {
    if (headerWrapper) {
      headerWrapper.scrollLeft = actualScrollElement.scrollLeft
    }
  }
  
  const syncHeaderToBody = () => {
    if (actualScrollElement) {
      actualScrollElement.scrollLeft = headerWrapper.scrollLeft
    }
  }
  
  actualScrollElement.addEventListener('scroll', syncBodyToHeader)
  headerWrapper.addEventListener('scroll', syncHeaderToBody)
  
  scroller._syncBodyToHeader = syncBodyToHeader
  scroller._syncHeaderToBody = syncHeaderToBody
}

// Watchers
watchEffect(() => {
  if ((fileType.value === 'csv' || fileType.value === 'txt') && rows.value.length > 0) {
    detectTypes()
  } else if (fileType.value === 'xlsx' && rows.value.length > 0) {
    if (columnTypes.value.length === 0 && columns.value.length > 0) {
      columnTypes.value = Array(columns.value.length).fill('string')
    }
  }
})

watch([encoding, delimiter, hasHeader], async () => {
  // Очищаем кэши при изменении настроек
  pagesCache.value.clear()
  cachedColumnWidths = null
  cachedColumnsForWidths = null
  
  if (props.file?.originalFile instanceof File || props.file?.originalFile instanceof Blob) {
    await previewLocally(props.file.originalFile)
    // totalRowsCount обновится в previewLocally через updateTotalRowsCount()
  } else if (props.file?.id || props.file?.temp_path) {
    currentPage.value = 1
    totalRowsCount.value = 0
    await loadPage(1)
    // totalRowsCount обновится в loadPage
  } else if (rawData.value && rawData.value.length > 0) {
    // Если данные уже загружены локально, просто обновляем totalRowsCount
    updateTotalRowsCount()
  }
})

watch(() => props.file, async (newFile, oldFile) => {
  if (newFile && newFile !== oldFile) {
    if (!newFile.id && !newFile.originalFile && !newFile.temp_path) {
      errorState.value = null
      rawData.value = []
      pagesCache.value.clear()
      currentPage.value = 1
      totalRowsCount.value = 0
      cachedColumnWidths = null
      cachedColumnsForWidths = null
      return
    }
    
    if (newFile.originalFile instanceof File || newFile.originalFile instanceof Blob) {
      await previewLocally(newFile.originalFile)
    } else if (newFile.id || newFile.temp_path) {
      pagesCache.value.clear()
      currentPage.value = 1
      totalRowsCount.value = 0
      cachedColumnWidths = null
      cachedColumnsForWidths = null
      
      if (fileType.value && ['csv', 'xlsx', 'txt'].includes(fileType.value)) {
        await loadPage(1)
      } else {
        errorState.value = `Неподдерживаемый тип файла: ${fileType.value || 'неизвестно'}`
      }
    }
    
    nextTick(() => {
      setTimeout(() => {
        setupScrollSync()
      }, 200)
    })
  }
}, { deep: true })

// Lifecycle
onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  
  if (!props.file) return
  
  try {
    if (props.file?.originalFile instanceof File || props.file?.originalFile instanceof Blob) {
      await previewLocally(props.file.originalFile)
    } else if (props.file?.id || props.file?.temp_path) {
      if (fileType.value && ['csv', 'xlsx', 'txt'].includes(fileType.value)) {
        await loadPage(1)
      } else {
        errorState.value = `Неподдерживаемый тип файла: ${fileType.value || 'неизвестно'}`
      }
    }
  } catch (err) {
    errorState.value = `Ошибка загрузки файла: ${err.message}`
  }
  
  nextTick(() => {
    setTimeout(() => {
      setupScrollSync()
    }, 200)
  })
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  
  // Удаляем обработчики изменения ширины столбцов
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  
  if (scrollerRef.value) {
    const actualScrollElement = scrollerRef.value._actualScrollElement || scrollerRef.value.$el || scrollerRef.value
    if (actualScrollElement && scrollerRef.value._syncBodyToHeader) {
      actualScrollElement.removeEventListener('scroll', scrollerRef.value._syncBodyToHeader)
    }
    if (headerWrapperRef.value && scrollerRef.value._syncHeaderToBody) {
      headerWrapperRef.value.removeEventListener('scroll', scrollerRef.value._syncHeaderToBody)
    }
  }
  
  cachedFilteredRows = null
  cachedFilterQuery = null
  cachedRowsData = null
  cachedColumnWidths = null
  cachedColumnsForWidths = null
})
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.unified-table-preview {
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

.error-message {
  text-align: center;
  padding: 2rem;
  border: 1px solid var(--color-accent);
  background: var(--color-primary-background);
  color: var(--color-accent);
  border-radius: 12px;
  margin-top: 1rem;
}

.toolbar {
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.875rem 1.25rem;
  background: white !important;
  border: 1px solid #d1d5db !important;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
  flex: 0 0 auto;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  label {
    margin-right: 0.5rem;
    margin-bottom: 0;
    font-weight: 600;
    font-size: 0.875rem;
    color: #2c3e50;
    white-space: nowrap;
  }
}

.toolbar .form-select {
  min-width: 140px;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  border: 1.5px solid #d1d5db;
  border-radius: 8px;
  transition: all 0.2s ease;
  background-color: white;
  
  &:focus {
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px rgba(109, 0, 26, 0.1);
    outline: none;
  }
}

.toggle-group {
  display: inline-flex;
  border: 1.5px solid #d1d5db;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  
  button {
    padding: 0.5rem 1rem;
    background: white;
    color: #2c3e50;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    font-weight: 600;
    font-size: 0.875rem;
    min-width: 60px;
    
    &:not(:last-child) {
      border-right: 1.5px solid #d1d5db;
    }
    
    &:hover {
      background: #f0f4f8;
    }
    
    &.active {
      background: var(--color-accent);
      color: white;
      box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
    }
  }
}

.search-wrapper {
  flex: 1;
  min-width: 200px;
  
  .form-control {
    padding: 0.5rem 0.875rem;
    font-size: 0.875rem;
    border: 1.5px solid #d1d5db;
    border-radius: 10px;
    transition: all 0.2s ease;
    
    &:focus {
      border-color: var(--color-accent);
      box-shadow: 0 0 0 3px rgba(109, 0, 26, 0.1);
      outline: none;
    }
  }
}

.table-container {
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
}

.table-header-wrapper {
  flex: 0 0 auto;
  overflow-x: auto;
  overflow-y: hidden;
  position: sticky;
  top: 0;
  z-index: 1;
  background: rgba(255, 255, 255, 0.95) !important;
  backdrop-filter: blur(12px);
  border-radius: 20px 20px 0 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  
  scrollbar-width: none;
  -ms-overflow-style: none;
  
  &::-webkit-scrollbar {
    display: none;
  }
}

.table-header-fixed {
  width: max-content;
  min-width: 100%;
}

.scroller {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  overflow-y: auto !important;
  overflow-x: auto !important;
  position: relative;
  background: rgba(255, 255, 255, 0.4) !important;
  
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
  
  :deep(.vue-recycle-scroller) {
    height: 100% !important;
    overflow: visible;
    background: transparent !important;
  }
  
  :deep(.vue-recycle-scroller__item-wrapper) {
    overflow: visible;
  }
  
  :deep(.table-row) {
    position: relative;
    
    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: linear-gradient(180deg, 
        rgba(var(--bs-info-rgb), 0.5) 0%,
        rgba(var(--bs-primary-rgb), 0.5) 100%);
      transform: scaleY(0);
      transition: transform 0.2s ease;
      border-radius: 0 4px 4px 0;
      z-index: 1;
    }
    
    &:hover::before {
      transform: scaleY(1);
    }
    
    &.selected {
      background: linear-gradient(90deg, rgba(var(--bs-info-rgb), 0.12) 0%, rgba(var(--bs-info-rgb), 0.06) 100%) !important;
      box-shadow: 
        inset 3px 0 0 rgba(var(--bs-info-rgb), 0.6),
        0 2px 8px rgba(var(--bs-info-rgb), 0.15);
      
      &::before {
        transform: scaleY(1);
      }
    }
  }
}

.header-cell {
  position: relative;
  
  &:not(:last-child) .column-resizer {
    position: absolute;
    top: 0;
    right: 0;
    width: 4px;
    height: 100%;
    cursor: col-resize;
    z-index: 10;
    background: rgba(var(--bs-info-rgb), 0.15);
    transition: background-color 0.2s ease;
    
    &:hover {
      background-color: rgba(var(--bs-info-rgb), 0.6);
    }
    
    &::after {
      content: '';
      position: absolute;
      top: 0;
      right: 0;
      width: 2px;
      height: 100%;
      background-color: rgba(var(--bs-info-rgb), 0.2);
    }
  }
}

.col-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-width: 0;
  
  .col-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 600;
    color: var(--color-primary-text);
    font-size: 0.875rem;
    line-height: 1.4;
  }
}

.type-icon,
.type-icon-static {
  flex-shrink: 0;
  color: rgba(var(--bs-info-rgb), 0.8);
  opacity: 0.7;
  transition: all 0.2s ease;
}

.type-icon-static {
  margin-right: 0.25rem;
}

.type-button-wrapper {
  position: relative;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border-radius: 10px;
  padding: 0.5rem;
  color: rgba(var(--bs-info-rgb), 0.8);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 
    0 2px 6px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  
  .type-icon {
    margin: 0;
  }
  
  &:hover {
    background: rgba(var(--bs-info-rgb), 0.1);
    transform: translateY(-1px);
    box-shadow: 
      0 4px 12px rgba(0, 0, 0, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.95);
    color: rgba(var(--bs-info-rgb), 1);
    
    .type-icon {
      opacity: 1;
      transform: scale(1.1);
    }
  }
}

.type-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  z-index: 5;
  box-shadow: 
    0 8px 24px rgba(0, 0, 0, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  min-width: 180px;
  padding: 0.5rem 0;
  margin-top: 0.25rem;
  overflow: hidden;
}

.type-option {
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: var(--color-primary-text);
  cursor: pointer;
  transition: all 0.2s ease;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  
  svg {
    flex-shrink: 0;
    opacity: 0.7;
  }
  
  &:hover {
    background: linear-gradient(90deg, rgba(var(--bs-info-rgb), 0.1) 0%, rgba(var(--bs-info-rgb), 0.05) 100%);
    color: rgba(var(--bs-info-rgb), 1);
    
    svg {
      opacity: 1;
    }
  }
  
  &.active {
    background: linear-gradient(90deg, rgba(var(--bs-info-rgb), 0.15) 0%, rgba(var(--bs-info-rgb), 0.08) 100%);
    color: rgba(var(--bs-info-rgb), 1);
    font-weight: 600;
    
    svg {
      opacity: 1;
      color: rgba(var(--bs-info-rgb), 1);
    }
  }
}

.table-loading,
.table-empty {
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

// Подсветка найденного текста при поиске
:deep(.search-highlight) {
  background-color: rgba(255, 235, 59, 0.5);
  color: #1a1a1a;
  font-weight: 600;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style>
