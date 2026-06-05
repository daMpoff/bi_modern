<template>
  <div class="dashboard-page" :class="{ 'is-view-mode': mode === 'view' }">
    <!-- Модальное окно выбора режима размещения -->
    <div v-if="showPlacementModal" class="placement-modal-overlay" @click.self="handlePlacementModalClose">
      <div class="placement-modal" @click.stop>
        <div class="placement-modal-header">
          <h3 class="placement-modal-title">Выберите режим размещения блоков</h3>
          <p class="placement-modal-subtitle">Выберите способ размещения блоков на дашборде. Вы можете запомнить выбор для всех дашбордов.</p>
        </div>
        <div class="placement-modal-content">
          <div class="placement-cards">
            <div
              class="placement-card"
              :class="{ active: selectedPlacementMode === 'grid' }"
              @click="selectPlacementMode('grid')"
            >
              <div class="placement-card-icon">
                <LayoutGrid :size="48" />
              </div>
              <h4 class="placement-card-title">Сетка (12 колонок)</h4>
              <p class="placement-card-description">
                Блоки размещаются в сетке Bootstrap из 12 колонок. Подходит для структурированных дашбордов.
              </p>
            </div>
            <div
              class="placement-card"
              :class="{ active: selectedPlacementMode === 'absolute' }"
              @click="selectPlacementMode('absolute')"
            >
              <div class="placement-card-icon">
                <Move :size="48" />
              </div>
              <h4 class="placement-card-title">Абсолютное размещение</h4>
              <p class="placement-card-description">
                Блоки размещаются свободно с абсолютными координатами. Подходит для творческих дашбордов.
              </p>
            </div>
          </div>
          <div class="placement-modal-remember">
            <label class="placement-remember-checkbox">
              <input type="checkbox" v-model="rememberChoice" />
              <span>Запомнить выбор для всех дашбордов</span>
            </label>
          </div>
        </div>
        <div class="placement-modal-actions">
          <button class="placement-modal-btn placement-modal-btn-primary" @click="confirmPlacementMode" :disabled="!selectedPlacementMode">
            Продолжить
          </button>
        </div>
      </div>
    </div>
    <!-- Верхняя панель инструментов -->
    <div class="dashboard-toolbar">
      <div class="toolbar-left">
        <h2 class="dashboard-title">{{ dashboard?.name || 'Загрузка...' }}</h2>
        <!-- Вкладки страниц дашборда -->
        <div v-if="dashboard?.pages?.length > 0" class="dashboard-page-tabs">
          <button
            v-for="page in dashboard.pages"
            :key="page.id"
            type="button"
            class="page-tab"
            :class="{ active: currentPage?.id === page.id }"
            @click="selectPage(page)"
          >
            {{ page.name || `Страница ${page.order + 1}` }}
          </button>
        </div>
        <!-- Подсказка для пустого дашборда -->
        <div v-if="mode === 'edit' && placementMode && currentPageBlocks.length === 0" class="toolbar-hint">
          <span class="hint-text">Перетащите блоки с нижней панели, в панель справа</span>
        </div>
      </div>
      <div class="toolbar-right">
        <!-- Undo / Redo (до 50 действий) -->
        <div v-if="mode === 'edit' && placementMode" class="undo-redo-group">
          <button
            type="button"
            class="undo-redo-btn"
            :disabled="!canUndo"
            title="Назад"
            @click="handleUndo"
          >
            <Undo2 :size="18" />
          </button>
          <button
            type="button"
            class="undo-redo-btn"
            :disabled="!canRedo"
            title="Вперёд"
            @click="handleRedo"
          >
            <Redo2 :size="18" />
          </button>
        </div>
        <!-- Экспорт дашборда (PNG / PDF) -->
        <div v-if="dashboard && placementMode" ref="dashboardExportDropdownRef" class="dashboard-export-dropdown">
          <button
            type="button"
            class="dashboard-export-btn"
            title="Скачать дашборд"
            :disabled="exporting"
            @click.stop="toggleExportDropdown"
          >
            <Download :size="18" />
            <span class="dashboard-export-btn-text">Скачать дашборд</span>
            <ChevronDown :size="16" />
          </button>
          <Transition name="dashboard-export-menu">
            <ul v-if="exportDropdownOpen" class="dashboard-export-menu">
              <li>
                <button type="button" class="dashboard-export-item" @click="handleExportDashboardPng">
                  <Image :size="16" />
                  <span>PNG</span>
                </button>
              </li>
              <li>
                <button type="button" class="dashboard-export-item" @click="handleExportDashboardPdf">
                  <FileText :size="16" />
                  <span>PDF</span>
                </button>
              </li>
            </ul>
          </Transition>
        </div>
        <!-- Toggle для переключения режимов размещения -->
        <div class="placement-mode-toggle" v-if="mode === 'edit' && placementMode">
          <button
            class="toggle-btn"
            :class="{ active: placementMode === 'grid' }"
            @click="changePlacementMode('grid')"
            title="Сетка (12 колонок)"
          >
            <LayoutGrid :size="18" />
          </button>
          <button
            class="toggle-btn"
            :class="{ active: placementMode === 'absolute' }"
            @click="changePlacementMode('absolute')"
            title="Абсолютное размещение"
          >
            <Move :size="18" />
          </button>
          <button
            class="toggle-btn toggle-btn-settings"
            @click="openPlacementModeModal"
            title="Изменить режим размещения"
          >
            <Settings :size="18" />
          </button>
        </div>
      </div>
    </div>

    <!-- Основной контент -->
    <div class="dashboard-content">
      <!-- Левая панель с блоками (только в режиме редактирования) -->
      <div v-if="mode === 'edit' && placementMode" class="dashboard-sidebar dashboard-sidebar--blocks">
        <DashboardBlocksPalette
          @drag-start="handlePaletteDragStart"
          @drag-end="handlePaletteDragEnd"
          @block-add="handlePaletteBlockAdd"
        />
      </div>

      <!-- Центральная область с дашбордом -->
      <div class="dashboard-main">
        <div v-if="loading" class="dashboard-loading">
          <div class="spinner-border" role="status">
            <span class="visually-hidden">Загрузка дашборда...</span>
          </div>
        </div>

        <div v-else-if="error" class="dashboard-error">
          <p>{{ error }}</p>
        </div>

        <div v-else-if="dashboard && placementMode" ref="dashboardExportRef" class="dashboard-canvas-wrapper">
          <DashboardCanvas
            ref="dashboardCanvasRef"
            :blocks="currentPageBlocks"
            :placement-mode="placementMode"
            :mode="mode"
            :selected-block-id="selectedBlockId"
            @block-add="handleBlockAdd"
            @block-update="handleBlockUpdate"
            @block-update-local="handleBlockUpdateLocal"
            @block-delete="handleBlockDelete"
            @block-click="handleBlockClick"
            @block-settings="handleBlockSettings"
            @canvas-click="handleCanvasClick"
            @focus-mode="handleChartFocusMode"
          />
        </div>
      </div>
    </div>

    <!-- Модальное окно пайплайна блока -->
    <DashboardBlockPipelineModal
      :show="showPipelineModal"
      :block="selectedBlock"
      @close="showPipelineModal = false"
      @save="handlePipelineSave"
      @block-config-update="handleBlockConfigUpdate"
    />

    <!-- Модальное окно настройки селектора -->
    <DashboardBlockSelectorModal
      :show="showSelectorModal"
      :block="selectedBlock"
      @close="showSelectorModal = false"
      @save="handleSelectorSave"
    />

    <!-- Модальное окно редактора текста -->
    <DashboardBlockTextModal
      :show="showTextModal"
      :block="selectedBlock"
      @close="showTextModal = false"
      @save="handleTextSave"
    />

    <!-- Режим фокуса графика (полноразмерный просмотр) -->
    <ChartFocusModal
      :show="showChartFocusModal"
      :block="focusChartBlock"
      @close="showChartFocusModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutGrid, Move, Undo2, Redo2, Settings, Download, ChevronDown, Image, FileText } from 'lucide-vue-next'
import { useToast } from 'vue-toastification'
import { apiClient } from '@/js/api/manager.js'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'
import { createPipeline, createPipelineChart } from '@/modules/bi_analysis_modern/client/src/Pipelines/js/pipelineApi.js'
import { useBiStore } from '@/modules/bi_analysis_modern/client/src/js/biStore.js'
import DashboardBlocksPalette from './DashboardBlocksPalette.vue'
import DashboardCanvas from './DashboardCanvas.vue'
import DashboardBlockPipelineModal from './DashboardBlockPipelineModal.vue'
import DashboardBlockSelectorModal from './DashboardBlockSelectorModal.vue'
import DashboardBlockTextModal from './DashboardBlockTextModal.vue'
import ChartFocusModal from './ChartFocusModal.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const biStore = useBiStore()

const dashboardId = computed(() => route.params.id)

/** Страница «новый дашборд»: /bi-modern/dashboard/new */
const isNewDashboardPage = computed(() => route.name === 'NewDashboardModern' || route.path === '/bi-modern/dashboard/new')
const mode = computed(() => route.query.mode || 'edit')

const dashboard = ref(null)
const loading = ref(false)
const error = ref(null)

// Состояние блоков
const currentPage = ref(null)
const blocks = ref([])
const selectedBlockId = ref(null)
const selectedBlock = computed(() => {
  if (!selectedBlockId.value) return null
  return blocks.value.find(b => b.id === selectedBlockId.value) || null
})
const showPipelineModal = ref(false)
const showSelectorModal = ref(false)
const showTextModal = ref(false)
const showChartFocusModal = ref(false)
const focusChartBlock = ref(null)

const dashboardExportRef = ref(null)
const dashboardCanvasRef = ref(null)
const dashboardExportDropdownRef = ref(null)
const exportDropdownOpen = ref(false)
const exporting = ref(false)
const dashboardExportCapturing = ref(false)

// Параметры дашборда (для селекторов и фильтрации графиков), синхронизируются с URL
const RESERVED_QUERY_KEYS = ['mode']
const dashboardParams = ref({})
function updateDashboardParams(patch) {
  if (!patch || typeof patch !== 'object') return
  for (const [k, v] of Object.entries(patch)) {
    if (v === undefined || v === null || v === '') delete dashboardParams.value[k]
    else dashboardParams.value[k] = v
  }
  const filtered = {}
  for (const [k, v] of Object.entries(dashboardParams.value)) {
    if (v !== undefined && v !== null && v !== '') filtered[k] = v
  }
  const query = { ...route.query, ...filtered }
  RESERVED_QUERY_KEYS.forEach(k => { if (route.query[k] !== undefined) query[k] = route.query[k] })
  router.replace({ query })
}
function syncDashboardParamsFromRoute() {
  const q = route.query || {}
  const next = {}
  for (const [k, v] of Object.entries(q)) {
    if (RESERVED_QUERY_KEYS.includes(k)) continue
    next[k] = v
  }
  dashboardParams.value = next
}
watch(() => route.query, syncDashboardParamsFromRoute, { immediate: true })
// Sync local dashboardParams → Pinia store (dual-write for backward compat)
watch(dashboardParams, (val) => biStore.setDashboardParams(val), { deep: true, immediate: true })
// Keep provide/inject for existing consumers (backward compatibility)
provide('dashboardParams', dashboardParams)
provide('updateDashboardParams', updateDashboardParams)
provide('dashboardExportCapturing', dashboardExportCapturing)

const MAX_UNDO_STEPS = 50
const undoStack = ref([])
const redoStack = ref([])
const isApplyingUndoRedo = ref(false)
const canUndo = computed(() => undoStack.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

function snapshotState() {
  const pageId = currentPage.value != null
    ? (typeof currentPage.value === 'object' ? currentPage.value.id : currentPage.value)
    : null
  const blocksCopy = blocks.value.map(b => ({
    id: b.id,
    type: b.type,
    x: b.x,
    y: b.y,
    width: b.width,
    height: b.height,
    config: b.config ? JSON.parse(JSON.stringify(b.config)) : {},
    page: b.page,
    order: b.order,
    _uid: b._uid
  }))
  return { pageId, blocks: blocksCopy }
}

function applySnapshot(snap) {
  if (!snap?.blocks) return
  blocks.value = snap.blocks
  if (snap.pageId != null && dashboard.value?.pages?.length) {
    const page = dashboard.value.pages.find((p) => p.id === snap.pageId)
    if (page) currentPage.value = page
  }
}

function pushUndo() {
  if (isApplyingUndoRedo.value) return
  redoStack.value = []
  const snap = snapshotState()
  undoStack.value.push(snap)
  if (undoStack.value.length > MAX_UNDO_STEPS) {
    undoStack.value = undoStack.value.slice(-MAX_UNDO_STEPS)
  }
}

function handleUndo() {
  if (!undoStack.value.length) return
  isApplyingUndoRedo.value = true
  const snap = undoStack.value.pop()
  redoStack.value.push(snapshotState())
  applySnapshot(snap)
  isApplyingUndoRedo.value = false
}

function handleRedo() {
  if (!redoStack.value.length) return
  isApplyingUndoRedo.value = true
  const snap = redoStack.value.pop()
  undoStack.value.push(snapshotState())
  applySnapshot(snap)
  isApplyingUndoRedo.value = false
}

// Ключ для сохранения режима размещения в localStorage
const PLACEMENT_MODE_STORAGE_KEY = 'dashboard_placement_mode'
// Ключ для флага, что пользователь явно выбрал режим через модальное окно
const PLACEMENT_MODE_SELECTED_KEY = 'dashboard_placement_mode_selected'
// Ключ для глобального сохранения выбора (для всех дашбордов)
const PLACEMENT_MODE_GLOBAL_CHOICE_KEY = 'dashboard_placement_mode_global_choice'
// Функция для получения ключа выбора режима для конкретного дашборда
const getDashboardPlacementModeKey = (id) => `dashboard_${id}_placement_mode_selected`

// Режим размещения (null означает, что режим еще не выбран)
const placementMode = ref(null)

// Модальное окно выбора режима размещения
const showPlacementModal = ref(false)
const selectedPlacementMode = ref(null)
const rememberChoice = ref(true) // По умолчанию запоминаем выбор

// Загрузка сохраненного режима размещения
function loadPlacementMode() {
  // Пытаемся загрузить сохраненный режим из localStorage
  try {
    // Сначала проверяем глобальный выбор (для всех дашбордов)
    const globalChoice = localStorage.getItem(PLACEMENT_MODE_GLOBAL_CHOICE_KEY)
    if (globalChoice === 'true') {
      // Если есть глобальный выбор, загружаем сохраненный режим
      const saved = localStorage.getItem(PLACEMENT_MODE_STORAGE_KEY)
      if (saved !== null && saved !== undefined && saved !== '') {
        if (saved === 'grid' || saved === 'absolute') {
          return saved
        }
      }
    }
    
    // Если глобального выбора нет, проверяем выбор для конкретного дашборда (обратная совместимость)
    const dashboardKey = dashboardId.value ? getDashboardPlacementModeKey(dashboardId.value) : null
    const modeSelected = dashboardKey ? localStorage.getItem(dashboardKey) : null
    
    // Если режим НЕ был явно выбран пользователем для этого дашборда - возвращаем null (показываем модальное окно)
    if (modeSelected !== 'true') {
      return null
    }
    
    // Если режим был выбран, загружаем его значение
    const saved = localStorage.getItem(PLACEMENT_MODE_STORAGE_KEY)
    if (saved !== null && saved !== undefined && saved !== '') {
      if (saved === 'grid' || saved === 'absolute') {
        return saved
      }
    }
  } catch (e) {
    console.error('Ошибка загрузки режима размещения:', e)
  }
  
  // Если режим не сохранен или не был явно выбран - возвращаем null (показываем модальное окно)
  return null
}

// Сохранение режима размещения
async function savePlacementMode(mode, isUserSelected = false, rememberGlobal = false) {
  try {
    // Сохраняем в localStorage для быстрого доступа
    localStorage.setItem(PLACEMENT_MODE_STORAGE_KEY, mode)
    
    // Если пользователь выбрал "Запомнить выбор", сохраняем глобальный выбор
    if (rememberGlobal) {
      localStorage.setItem(PLACEMENT_MODE_GLOBAL_CHOICE_KEY, 'true')
    }
    
    // Если режим был выбран пользователем через модальное окно - сохраняем флаг для этого дашборда
    if (isUserSelected && dashboardId.value) {
      const dashboardKey = getDashboardPlacementModeKey(dashboardId.value)
      localStorage.setItem(dashboardKey, 'true')
      // Также сохраняем общий флаг для обратной совместимости
      localStorage.setItem(PLACEMENT_MODE_SELECTED_KEY, 'true')
    }
    
    // Сохраняем на сервере, если есть ID дашборда
    if (dashboardId.value) {
      try {
        await apiClient.patch(biEndpoints.bi.dashboardDetail(dashboardId.value), {
          placement_mode: mode
        })
        // Обновляем локальное значение дашборда, если оно уже загружено
        if (dashboard.value) {
          dashboard.value.placement_mode = mode
        }
      } catch (err) {
        console.error('Ошибка сохранения режима размещения на сервере:', err)
        // Не прерываем выполнение, так как значение уже сохранено в localStorage
      }
    }
  } catch (e) {
    console.error('Ошибка сохранения режима размещения:', e)
  }
}

// Выбор режима размещения в модальном окне
function selectPlacementMode(mode) {
  selectedPlacementMode.value = mode
}

// Подтверждение выбора режима размещения
async function confirmPlacementMode() {
  if (!selectedPlacementMode.value) return
  
  placementMode.value = selectedPlacementMode.value
  await savePlacementMode(selectedPlacementMode.value, true, rememberChoice.value)
  showPlacementModal.value = false
}

// Открытие модального окна для изменения режима (из toolbar)
function openPlacementModeModal() {
  selectedPlacementMode.value = placementMode.value || null
  // Проверяем, был ли сохранен глобальный выбор
  rememberChoice.value = localStorage.getItem(PLACEMENT_MODE_GLOBAL_CHOICE_KEY) === 'true'
  showPlacementModal.value = true
}

// Инициализация модального окна при первом показе
function initPlacementModal() {
  // При первом показе режим не выбран
  if (!selectedPlacementMode.value) {
    selectedPlacementMode.value = null
  }
  // Проверяем, был ли сохранен глобальный выбор
  rememberChoice.value = localStorage.getItem(PLACEMENT_MODE_GLOBAL_CHOICE_KEY) === 'true'
}

// Закрытие модального окна (нельзя закрыть без выбора)
function handlePlacementModalClose() {
  // Модальное окно не закрывается при клике вне его - нужно выбрать режим
}

/** Создать дашборд и перейти на страницу редактирования (для маршрута /bi-modern/dashboard/new). */
async function createDashboardAndRedirect() {
  loading.value = true
  error.value = null
  try {
    const { data } = await apiClient.post(biEndpoints.bi.DashboardList, {
      name: 'Новый дашборд',
      description: ''
    })
    if (data?.id) {
      await router.replace(`/bi-modern/dashboard/${data.id}/`)
      return true
    }
  } catch (err) {
    console.error('Ошибка создания дашборда:', err)
    error.value = 'Не удалось создать дашборд: ' + (err.message || err)
  } finally {
    loading.value = false
  }
  return false
}

// Загрузка дашборда
async function loadDashboard() {
  if (!dashboardId.value) {
    if (!isNewDashboardPage.value) {
      error.value = 'ID дашборда не указан'
    }
    return
  }

  // Reset BI store for the new dashboard
  biStore.$reset()
  biStore.setCurrentDashboard(dashboardId.value)

  loading.value = true
  error.value = null

  try {
    const { data } = await apiClient.get(biEndpoints.bi.dashboardDetail(dashboardId.value))
    dashboard.value = data
    
    // Загружаем страницы и блоки
    if (data.pages && data.pages.length > 0) {
      currentPage.value = data.pages[0]
      // Собираем все блоки из всех страниц
      blocks.value = []
      data.pages.forEach(page => {
        if (page.items) {
          page.items.forEach(item => {
            blocks.value.push({
              ...item,
              page: page.id,
              // Добавляем _uid если его нет (для стабильного key)
              _uid: item._uid || (item.id ? undefined : (crypto.randomUUID ? crypto.randomUUID() : `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`))
            })
          })
        }
      })
    }
    
    // Проверяем, был ли режим явно выбран пользователем для этого дашборда
    const dashboardKey = getDashboardPlacementModeKey(dashboardId.value)
    const modeSelected = localStorage.getItem(dashboardKey)
    
    // Если режим был явно выбран пользователем, используем значение с сервера
    if (modeSelected === 'true' && data.placement_mode && (data.placement_mode === 'grid' || data.placement_mode === 'absolute')) {
      placementMode.value = data.placement_mode
      // Синхронизируем с localStorage
      localStorage.setItem(PLACEMENT_MODE_STORAGE_KEY, data.placement_mode)
    }
    // Если режим не был выбран явно, НЕ устанавливаем placementMode.value,
    // чтобы модальное окно могло появиться
  } catch (err) {
    console.error('Ошибка загрузки дашборда:', err)
    error.value = 'Не удалось загрузить дашборд: ' + (err.message || err)
  } finally {
    loading.value = false
  }
}

// Получение блоков текущей страницы
const currentPageBlocks = computed(() => {
  if (!currentPage.value) return []
  
  const currentPageId = typeof currentPage.value === 'object' ? currentPage.value.id : currentPage.value
  return blocks.value.filter(block => {
    // Блок может иметь page как ID или как объект
    const blockPageId = typeof block.page === 'object' ? block.page.id : block.page
    return blockPageId === currentPageId
  })
})

function selectPage(page) {
  if (currentPage.value?.id === page?.id) return
  pushUndo()
  currentPage.value = page
}

// Обработка drag start из палитры
function handlePaletteDragStart() {
  // Логика уже обрабатывается в DashboardBlocksPalette
}

// Обработка drag end из палитры
function handlePaletteDragEnd() {
  // Логика уже обрабатывается в DashboardBlocksPalette
}

// Обработка добавления блока из палитры по клику
function handlePaletteBlockAdd(block) {
  // Вычисляем позицию в центре канваса
  // Для grid режима - в центре сетки
  // Для absolute режима - в центре видимой области
  
  if (placementMode.value === 'grid') {
    // В grid режиме размещаем в центре (примерно 4-5 колонка, 3-4 строка)
    // Размер по умолчанию: 4 колонки, 3 строки
    const defaultCols = 4
    const defaultRows = 3
    const centerCol = Math.floor((12 - defaultCols) / 2) + 1 // Центр 12-колоночной сетки
    const centerRow = 3 // Начинаем с 3-й строки
    
    // Вычисляем позицию в пикселях (будет пересчитано в DashboardCanvas)
    // Используем примерные значения, реальные будут вычислены при рендеринге
    block.x = (centerCol - 1) * 100 // Примерная ширина ячейки
    block.y = (centerRow - 1) * 50 // Примерная высота ячейки
    block.width = defaultCols * 100 + (defaultCols - 1) * 8 // Примерная ширина
    block.height = defaultRows * 50 + (defaultRows - 1) * 8 // Примерная высота
  } else {
    // В absolute режиме размещаем в центре видимой области
    // Примерные значения, будут скорректированы при рендеринге
    block.x = 300
    block.y = 200
    block.width = 400
    block.height = 300
  }
  
  // Вычисляем order
  block.order = blocks.value.length
  
  // Вызываем стандартную функцию добавления блока
  handleBlockAdd(block)
}

// Добавление нового блока
async function handleBlockAdd(newBlock) {
  pushUndo()
  if (!currentPage.value) {
    // Если страницы нет, используем первую страницу или создаем новую через обновление дашборда
    if (!dashboard.value || !dashboard.value.pages || dashboard.value.pages.length === 0) {
      // Создаем страницу через обновление дашборда
      try {
        const updatedDashboard = {
          ...dashboard.value,
          pages: [
            {
              name: 'Страница 1',
              order: 0,
              items: []
            }
          ]
        }
        const { data } = await apiClient.patch(
          biEndpoints.bi.dashboardDetail(dashboardId.value),
          updatedDashboard
        )
        dashboard.value = data
        if (data.pages && data.pages.length > 0) {
          currentPage.value = data.pages[0]
        }
      } catch (err) {
        console.error('Ошибка создания страницы:', err)
        toast.error('Не удалось создать страницу')
        return
      }
    } else {
      currentPage.value = dashboard.value.pages[0]
    }
  }

  if (newBlock.type === 'График' && !newBlock.config?.pipelineChartId) {
    try {
      const name = `Дашборд: график ${dashboardId.value ?? (typeof crypto?.randomUUID === 'function' ? crypto.randomUUID() : `uuid-${Date.now()}`)}`
      const pipeline = await createPipeline({ name, is_dashboard_only: true })
      const chart = await createPipelineChart({
        pipeline: pipeline.id,
        name,
        chart_type: 'bar',
        chart_config: {},
        engine: 'echarts'
      })
      newBlock.config = {
        ...(newBlock.config || {}),
        pipelineChartId: chart.id,
        chartType: 'bar',
        engine: 'echarts'
      }
    } catch (err) {
      console.error('Ошибка создания пайплайна/графика для блока:', err)
      toast.error('Не удалось создать график: ' + (err?.message || 'Неизвестная ошибка'))
      return
    }
  }

  try {
    const currentPageId = typeof currentPage.value === 'object' ? currentPage.value.id : currentPage.value
    
    const response = await apiClient.post(biEndpoints.bi.dashboardItemList(), {
      page: currentPageId,
      type: newBlock.type,
      x: Math.round(Number(newBlock.x) || 0),
      y: Math.round(Number(newBlock.y) || 0),
      width: Math.round(Number(newBlock.width) || 200),
      height: Math.round(Number(newBlock.height) || 150),
      config: newBlock.config ?? {},
      order: Math.max(0, Math.floor(Number(newBlock.order) || 0))
    })

    // Получаем данные из ответа
    const blockData = response.data || response
    
    // Проверяем, что блок имеет id
    if (!blockData.id) {
      console.error('Блок не имеет id:', blockData)
      toast.error('Ошибка: блок не был создан корректно')
      return
    }

    // Добавляем блок с правильным page ID и _uid (если id еще нет)
    const blockWithPage = {
      ...blockData,
      page: currentPageId,
      _uid: blockData._uid || (crypto.randomUUID ? crypto.randomUUID() : `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`)
    }
    
    // Используем реактивное обновление массива
    blocks.value = [...blocks.value, blockWithPage]
    
    // Принудительно обновляем список блоков для реактивности
    await nextTick()
    
    toast.success('Блок добавлен')
  } catch (err) {
    console.error('Ошибка добавления блока:', err)
    toast.error('Не удалось добавить блок: ' + (err.message || 'Неизвестная ошибка'))
  }
}

// Локальное обновление блока (только UI, без API и undo) — во время ресайза/перетаскивания
function handleBlockUpdateLocal(updatedBlock) {
  const i = blocks.value.findIndex(b => b.id === updatedBlock.id)
  if (i === -1) return
  const existing = blocks.value[i]
  blocks.value[i] = { ...existing, ...updatedBlock, page: existing.page, _uid: existing._uid }
}

// Обновление блока с сохранением на сервер (вызывается по окончании ресайза/перемещения)
async function handleBlockUpdate(updatedBlock) {
  if (!blocks.value.some(b => b.id === updatedBlock.id)) return
  pushUndo()
  try {
    const { data } = await apiClient.patch(
      biEndpoints.bi.dashboardItemDetail(updatedBlock.id),
      {
        x: updatedBlock.x,
        y: updatedBlock.y,
        width: updatedBlock.width,
        height: updatedBlock.height,
        config: updatedBlock.config
      }
    )

    const index = blocks.value.findIndex(b => b.id === updatedBlock.id)
    if (index !== -1) {
      // Сохраняем page ID и _uid при обновлении
      const existingBlock = blocks.value[index]
      blocks.value[index] = {
        ...data,
        page: typeof currentPage.value === 'object' ? currentPage.value.id : currentPage.value,
        _uid: existingBlock._uid || data._uid
      }
    }
  } catch (err) {
    console.error('Ошибка обновления блока:', err)
    toast.error('Не удалось обновить блок')
  }
}

// Удаление блока
async function handleBlockDelete(block) {
  pushUndo()
  try {
    await apiClient.delete(biEndpoints.bi.dashboardItemDetail(block.id))
    blocks.value = blocks.value.filter(b => b.id !== block.id)
    if (selectedBlockId.value === block.id) {
      selectedBlockId.value = null
    }
    toast.success('Блок удален')
  } catch (err) {
    console.error('Ошибка удаления блока:', err)
    toast.error('Не удалось удалить блок')
  }
}

// Клик по canvas (для снятия выделения)
function handleCanvasClick() {
  selectedBlockId.value = null
}

// Клик по блоку (для выделения; для блока «График»/«Селектор»/«Текст» открываем настройки)
function handleBlockClick(block) {
  if (!block) return
  selectedBlockId.value = block.id
  if (block.type === 'График') showPipelineModal.value = true
  else if (block.type === 'Селектор') showSelectorModal.value = true
  else if (block.type === 'Текст') showTextModal.value = true
}

// Открытие настроек блока
function handleBlockSettings(block) {
  selectedBlockId.value = block.id
  if (block.type === 'Селектор') showSelectorModal.value = true
  else if (block.type === 'Текст') showTextModal.value = true
  else showPipelineModal.value = true
}

function handleChartFocusMode(block) {
  focusChartBlock.value = block
  showChartFocusModal.value = true
}

function sanitizeFilename(name) {
  return (name || 'dashboard').replace(/[^\w\u0400-\u04FF-]/g, '_')
}

function toggleExportDropdown() {
  exportDropdownOpen.value = !exportDropdownOpen.value
}

function closeExportDropdown() {
  exportDropdownOpen.value = false
}

function handleClickOutsideExport(event) {
  if (dashboardExportDropdownRef.value && !dashboardExportDropdownRef.value.contains(event.target)) {
    closeExportDropdown()
  }
}

const EXPORT_CAPTURE_CLASS = 'dashboard-export-capturing'
/* Единый коэффициент качества: 3 (как pixelRatio у графиков), фон #fff */
const EXPORT_SCALE = 3
const EXPORT_BG = '#fff'

async function handleExportDashboardPng() {
  closeExportDropdown()
  const wrapperEl = dashboardExportRef.value
  const captureEl = dashboardCanvasRef.value?.$el ?? wrapperEl
  if (!captureEl) {
    toast.warning('Область дашборда не найдена')
    return
  }
  exporting.value = true
  dashboardExportCapturing.value = true
  if (wrapperEl) wrapperEl.classList.add(EXPORT_CAPTURE_CLASS)
  await nextTick()
  await new Promise(r => requestAnimationFrame(r))
  try {
    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(captureEl, {
      useCORS: true,
      allowTaint: true,
      backgroundColor: EXPORT_BG,
      scale: EXPORT_SCALE,
      logging: false,
      imageTimeout: 0,
      scrollX: 0,
      scrollY: 0,
      width: captureEl.scrollWidth,
      height: captureEl.scrollHeight
    })
    const dataUrl = canvas.toDataURL('image/png')
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = `${sanitizeFilename(dashboard.value?.name)}.png`
    link.click()
    toast.success('Дашборд сохранён в PNG')
  } catch (err) {
    toast.error(err?.message || 'Ошибка экспорта в PNG')
  } finally {
    dashboardExportCapturing.value = false
    if (wrapperEl) wrapperEl.classList.remove(EXPORT_CAPTURE_CLASS)
    exporting.value = false
  }
}

async function handleExportDashboardPdf() {
  closeExportDropdown()
  const wrapperEl = dashboardExportRef.value
  const captureEl = dashboardCanvasRef.value?.$el ?? wrapperEl
  if (!captureEl) {
    toast.warning('Область дашборда не найдена')
    return
  }
  exporting.value = true
  dashboardExportCapturing.value = true
  if (wrapperEl) wrapperEl.classList.add(EXPORT_CAPTURE_CLASS)
  await nextTick()
  await new Promise(r => requestAnimationFrame(r))
  try {
    const [html2canvasModule, jsPDFModule] = await Promise.all([
      import('html2canvas'),
      import('jspdf')
    ])
    const html2canvas = html2canvasModule.default
    const { default: jsPDF } = jsPDFModule
    const canvas = await html2canvas(captureEl, {
      useCORS: true,
      allowTaint: true,
      backgroundColor: EXPORT_BG,
      scale: EXPORT_SCALE,
      logging: false,
      imageTimeout: 0,
      scrollX: 0,
      scrollY: 0,
      width: captureEl.scrollWidth,
      height: captureEl.scrollHeight
    })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
      unit: 'mm',
      format: 'a4'
    })
    const pageW = pdf.internal.pageSize.getWidth()
    const pageH = pdf.internal.pageSize.getHeight()
    const imgW = canvas.width
    const imgH = canvas.height
    const margin = 0.95
    let w = pageW * margin
    let h = w * (imgH / imgW)
    if (h > pageH * margin) {
      h = pageH * margin
      w = h * (imgW / imgH)
    }
    const x = (pageW - w) / 2
    const y = (pageH - h) / 2
    pdf.addImage(imgData, 'PNG', x, y, w, h)
    pdf.save(`${sanitizeFilename(dashboard.value?.name)}.pdf`)
    toast.success('Дашборд сохранён в PDF')
  } catch (err) {
    toast.error(err?.message || 'Ошибка экспорта в PDF')
  } finally {
    dashboardExportCapturing.value = false
    if (wrapperEl) wrapperEl.classList.remove(EXPORT_CAPTURE_CLASS)
    exporting.value = false
  }
}

// Обновление конфигурации блока (например, при «Применить» в настройках графика)
async function handleBlockConfigUpdate(updatedBlock) {
  try {
    await handleBlockUpdate(updatedBlock)
  } catch (err) {
    console.error('Ошибка обновления настроек блока:', err)
    toast.error('Не удалось применить настройки')
  }
}

// Сохранение пайплайна
async function handlePipelineSave(updatedBlock) {
  try {
    await handleBlockUpdate(updatedBlock)
    showPipelineModal.value = false
    toast.success('Пайплайн сохранен')
  } catch (err) {
    console.error('Ошибка сохранения пайплайна:', err)
    toast.error('Не удалось сохранить пайплайн')
  }
}

// Сохранение настроек селектора
async function handleSelectorSave(updatedBlock) {
  try {
    await handleBlockUpdate(updatedBlock)
    showSelectorModal.value = false
    toast.success('Настройки селектора сохранены')
  } catch (err) {
    console.error('Ошибка сохранения селектора:', err)
    toast.error('Не удалось сохранить настройки')
  }
}

// Сохранение текстового блока
async function handleTextSave(updatedBlock) {
  try {
    await handleBlockUpdate(updatedBlock)
    showTextModal.value = false
    toast.success('Текст сохранён')
  } catch (err) {
    console.error('Ошибка сохранения текста:', err)
    toast.error('Не удалось сохранить текст')
  }
}

// Изменение режима размещения через toggle (с сохранением)
async function changePlacementMode(mode) {
  if (placementMode.value === mode) return // Если режим уже установлен, ничего не делаем
  
  placementMode.value = mode
  // При изменении через toggle режим уже был выбран ранее, поэтому сохраняем без нового флага
  await savePlacementMode(mode, false)
}

async function applyPlacementModeAfterLoad() {
  // Проверяем глобальный выбор в первую очередь
  const globalChoice = localStorage.getItem(PLACEMENT_MODE_GLOBAL_CHOICE_KEY)
  
  if (globalChoice === 'true') {
    // Если есть глобальный выбор, загружаем его
    const savedMode = loadPlacementMode()
    if (savedMode) {
      placementMode.value = savedMode
      return
    }
  }
  
  // Если глобального выбора нет, проверяем выбор для конкретного дашборда
  const dashboardKey = dashboardId.value ? getDashboardPlacementModeKey(dashboardId.value) : null
  const modeSelected = dashboardKey ? localStorage.getItem(dashboardKey) : null
  
  if (modeSelected !== 'true') {
    // Если режим не был выбран, показываем модальное окно
    setTimeout(() => {
      initPlacementModal()
      showPlacementModal.value = true
    }, 200)
  } else {
    const savedMode = loadPlacementMode()
    if (savedMode) {
      placementMode.value = savedMode
    } else if (dashboard.value?.placement_mode) {
      placementMode.value = dashboard.value.placement_mode
    }
  }
}

onMounted(async () => {
  const currentMode = mode.value || route.query.mode || 'edit'

  if (currentMode === 'view') {
    placementMode.value = 'grid'
    await loadDashboard()
    return
  }

  if (isNewDashboardPage.value) {
    const created = await createDashboardAndRedirect()
    if (created) return
  }

  await loadDashboard()
  await applyPlacementModeAfterLoad()
  document.addEventListener('click', handleClickOutsideExport)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutsideExport)
  biStore.$reset()
})

watch(dashboardId, async (id, prevId) => {
  if (id && id !== prevId && mode.value !== 'view') {
    await loadDashboard()
    await applyPlacementModeAfterLoad()
  }
})
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';
@import '../scss/_bi-theme.scss';

.dashboard-page {
  @include bi-burgundy-tokens;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100vh - 60px);
  background: var(--color-background);
  overflow: hidden;
}

/* При экспорте скрываем сетку фона и снимаем обрезку для полного захвата */
.dashboard-export-capturing :deep(.grid-background) {
  display: none !important;
}

.dashboard-export-capturing :deep(.dashboard-canvas) {
  overflow: visible !important;
}

.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.5rem;
  background: var(--color-primary-background);
  border-bottom: 1px solid var(--color-border);
  z-index: 10;
}

.toolbar-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.dashboard-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-primary-text);
}

.dashboard-page-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.5rem;
}

.page-tab {
  padding: 0.375rem 0.75rem;
  font-size: 13px;
  color: var(--color-secondary-text);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.05);
    color: var(--color-primary-text);
  }

  &.active {
    background: rgba(var(--bs-primary-rgb), 0.1);
    color: var(--bs-primary);
    border-color: rgba(var(--bs-primary-rgb), 0.3);
  }
}

.toolbar-hint {
  margin-top: 0.25rem;
}

.hint-text {
  font-size: 13px;
  color: var(--color-secondary-text);
  font-style: italic;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.dashboard-export-dropdown {
  position: relative;
}

.dashboard-export-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  background: rgba(var(--bs-primary-rgb), 0.1);
  color: var(--bs-primary);
  transition: background-color 0.2s ease, color 0.2s ease;

  &:hover:not(:disabled) {
    background: rgba(var(--bs-primary-rgb), 0.2);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.dashboard-export-btn-text {
  white-space: nowrap;
}

.dashboard-export-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin: 0.25rem 0 0;
  padding: 0.25rem 0;
  min-width: 120px;
  list-style: none;
  background: var(--bs-body-bg, #fff);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(0, 0, 0, 0.08);
  z-index: 1050;
}

.dashboard-export-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  text-align: left;
  border: none;
  background: transparent;
  color: var(--bs-body-color);
  cursor: pointer;
  transition: background-color 0.15s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
  }
}

.dashboard-export-menu-enter-active,
.dashboard-export-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.1s ease;
}

.dashboard-export-menu-enter-from,
.dashboard-export-menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.undo-redo-group {
  display: flex;
  gap: 0.25rem;
  padding: 0.25rem;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}

.undo-redo-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--color-secondary-text);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover:not(:disabled) {
    background: rgba(0, 0, 0, 0.06);
    color: var(--color-primary-text);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.placement-mode-toggle {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 8px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--color-secondary-text);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
    color: var(--color-primary-text);
  }

  &.active {
    background: rgba(var(--bs-primary-rgb), 0.1);
    color: var(--bs-primary);
  }

  &.toggle-btn-settings {
    margin-left: 0.5rem;
    border-left: 1px solid rgba(0, 0, 0, 0.1);
    padding-left: 0.5rem;

    &:hover {
      background: rgba(var(--bs-info-rgb), 0.1);
      color: var(--bs-info);
    }
  }
}

.dashboard-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.dashboard-sidebar {
  width: 320px;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  background: var(--color-primary-background);
  border-right: 1px solid var(--color-border);
}

.sidebar-header {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--color-primary-text);
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 0;
}

.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-background);
}

.dashboard-loading,
.dashboard-error {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 2rem;
}

.dashboard-error {
  color: #f87171;
  text-align: center;
}

.dashboard-canvas-wrapper {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dashboard-grid-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 2rem;
  background: var(--color-primary-background);
  border-radius: 12px;
  border: 2px dashed var(--color-border);
  text-align: center;

  p {
    margin: 0.5rem 0;
    font-size: 16px;
    color: var(--color-primary-text);

    &.text-muted {
      font-size: 14px;
      color: var(--color-secondary-text);
    }
  }
}

// Модальное окно выбора режима размещения
.placement-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    135deg,
    rgba(0, 0, 0, 0.4) 0%,
    rgba(0, 0, 0, 0.5) 100%
  );
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10002;
  padding: 2rem;
}

.placement-modal {
  background: var(--color-primary-background);
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  width: 800px;
  max-width: calc(100vw - 4rem);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--color-border);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(var(--bi-accent-rgb), 0.5) 50%,
      transparent 100%
    );
    opacity: 0.7;
  }
}

.placement-modal-header {
  padding: 2rem 2rem 1.5rem 2rem;
  border-bottom: 1px solid var(--color-border);
  text-align: center;
}

.placement-modal-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 0.5rem 0;
  color: var(--color-primary-text);
}

.placement-modal-subtitle {
  font-size: 14px;
  color: var(--color-secondary-text);
  margin: 0;
}

.placement-modal-content {
  padding: 2rem;
}

.placement-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

.placement-card {
  padding: 2rem;
  background: var(--color-secondary-background);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: center;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(
      90deg,
      rgba(var(--bs-primary-rgb), 0) 0%,
      rgba(var(--bs-primary-rgb), 0.6) 50%,
      rgba(var(--bs-primary-rgb), 0) 100%
    );
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    border-color: rgba(var(--bs-primary-rgb), 0.4);
    transform: translateY(-3px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.10);

    &::before {
      opacity: 1;
    }
  }

  &.active {
    background: rgba(var(--bs-primary-rgb), 0.1);
    border-color: var(--bs-primary);
    box-shadow: 0 4px 16px rgba(var(--bs-primary-rgb), 0.2);

    &::before {
      opacity: 1;
    }

    .placement-card-icon {
      color: var(--bs-primary);
    }

    .placement-card-title {
      color: var(--bs-primary);
    }
  }
}

.placement-card-icon {
  margin-bottom: 1rem;
  color: var(--color-secondary-text);
  transition: color 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placement-card-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 0.75rem 0;
  color: var(--color-primary-text);
  transition: color 0.3s ease;
}

.placement-card-description {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-secondary-text);
  margin: 0;
}

.placement-modal-remember {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
}

.placement-remember-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-primary-text);
  padding: 0.75rem 1.25rem;
  background: var(--color-secondary-background);
  border-radius: 10px;
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
  user-select: none;

  &:hover {
    border-color: rgba(var(--bs-primary-rgb), 0.3);
  }

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
    accent-color: var(--bi-accent);
    flex-shrink: 0;
  }

  span {
    font-weight: 500;
  }
}

.placement-modal-actions {
  padding: 1.5rem 2rem 2rem 2rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: center;
}

.placement-modal-btn {
  padding: 0.75rem 2rem;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.placement-modal-btn-primary {
    background: var(--bi-accent);
    color: #fff;
    box-shadow: 0 1px 2px rgba(var(--bi-accent-rgb), 0.3);
    border: 1px solid var(--bi-accent);

    &:hover:not(:disabled) {
      background: var(--bi-accent-hover);
      box-shadow: 0 2px 8px rgba(var(--bi-accent-rgb), 0.35);
      transform: translateY(-1px);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
      background: var(--bi-accent-active);
    }
  }
}
</style>
