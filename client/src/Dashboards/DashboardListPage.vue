<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiClient } from '@/js/api/manager.js'
import { LayoutDashboard, Search, MoreHorizontal, Eye, Pencil, Trash2, Settings } from 'lucide-vue-next'
import { getListConfig } from '@/modules/bi_analysis_modern/client/src/js/listConfigs.js'
import { useToast } from 'vue-toastification'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ModalCenter from '@/components/ModalCenter.vue'

const config = getListConfig('dashboards')
const router = useRouter()
const toast = useToast()

const items = ref([])
const search = ref('')
const sort = ref('new')
const loading = ref(false)

// Меню действий
const showMenu = ref(false)
const menuPosition = ref({ top: '0px', left: '0px' })
const menuDashboardId = ref(null)

// Удаление
const showDeleteDialog = ref(false)
const dashboardToDelete = ref(null)
const isDeleteLocked = ref(false)
const deleteCountdown = ref(3)
let countdownTimer = null

// Настройки отображения
const SETTINGS_STORAGE_KEY = 'dashboards_list_settings'
const showSettingsModal = ref(false)

// Модальное окно создания дашборда
const showCreateModal = ref(false)
const newDashboardName = ref('')
const isCreating = ref(false)

// Настройки по умолчанию
const defaultSettings = {
  cardSize: 'medium', // 'small' | 'medium' | 'large'
  gridGap: 1.5, // в rem
  minCardWidth: 280, // в px
  showDescription: true,
  showDate: true,
  defaultSort: 'new'
}

// Загрузка настроек из localStorage
function loadSettings() {
  try {
    const saved = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return { ...defaultSettings, ...parsed }
    }
  } catch (e) {
    logError('Ошибка загрузки настроек:', e)
  }
  return defaultSettings
}

// Сохранение настроек в localStorage
function saveSettings() {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(gridSettings.value))
    toast.success('Настройки сохранены')
  } catch (e) {
    logError('Ошибка сохранения настроек:', e)
    toast.error('Не удалось сохранить настройки')
  }
}

const gridSettings = ref(loadSettings())

// Применение настроек к сетке
const gridStyle = computed(() => ({
  gap: `${gridSettings.value.gridGap}rem`,
  gridTemplateColumns: `repeat(auto-fill, minmax(${gridSettings.value.minCardWidth}px, 1fr))`
}))

// Загрузка дашбордов
async function fetchItems() {
  loading.value = true
  try {
    const { data } = await apiClient.get(config.endpoint)
    const rows = Array.isArray(data) ? data : (data.results || [])
    
    if (config.mapData) {
      items.value = rows.map(config.mapData)
    } else {
      items.value = rows.map(item => ({
        id: item.id,
        name: item.name || '—',
        created_at: item.created_at,
        owner_username: item.owner_username,
        description: item.description,
        ...item
      }))
    }
  } catch (err) {
    logError('Ошибка загрузки дашбордов:', err)
  } finally {
    loading.value = false
  }
}

// Фильтрация и сортировка
const filteredItems = computed(() => {
  const term = search.value.toLowerCase()
  let list = [...items.value]

  if (term && config.filterFunction) {
    list = list.filter(config.filterFunction(term))
  } else if (term) {
    list = list.filter(item =>
      item.name?.toLowerCase().includes(term) ||
      item.owner_username?.toLowerCase().includes(term)
    )
  }

  // Сортировка
  switch (sort.value) {
    case 'new':
      list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      break
    case 'old':
      list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      break
    case 'az':
      list.sort((a, b) => a.name.localeCompare(b.name))
      break
    case 'za':
      list.sort((a, b) => b.name.localeCompare(a.name))
      break
  }

  return list
})

function goToCreate() {
  newDashboardName.value = ''
  showCreateModal.value = true
}

function closeCreateModal() {
  showCreateModal.value = false
  newDashboardName.value = ''
}

async function createDashboard() {
  if (!newDashboardName.value.trim()) {
    toast.error('Введите название дашборда')
    return
  }

  try {
    isCreating.value = true
    const { data } = await apiClient.post(config.endpoint, {
      name: newDashboardName.value.trim(),
      description: ''
    })
    
    if (data?.id) {
      toast.success('Дашборд создан')
      closeCreateModal()
      // Обновляем список
      await fetchItems()
      // Переходим на страницу редактирования
      router.push(`/bi-modern/dashboard/${data.id}/`)
    }
  } catch (err) {
    logError('Ошибка создания дашборда:', err)
    toast.error('Ошибка при создании дашборда: ' + (err.message || err))
  } finally {
    isCreating.value = false
  }
}

// Просмотр дашборда (клик на карточку - без редактирования)
function goToDashboardView(dashboard) {
  if (dashboard?.id) {
    router.push(`/bi-modern/dashboard/${dashboard.id}/?mode=view`)
  }
}

// Просмотр (из меню)
function goToDashboardViewFromMenu(dashboard) {
  closeMenu()
  if (dashboard?.id) {
    router.push(`/bi-modern/dashboard/${dashboard.id}/?mode=view`)
  }
}

// Редактирование (из меню)
function goToDashboardEdit(dashboard) {
  closeMenu()
  if (dashboard?.id) {
    router.push(`/bi-modern/dashboard/${dashboard.id}/`)
  }
}

// Открытие меню действий
function onMoreClick(event, dashboardId) {
  event.stopPropagation()
  const rect = event.currentTarget.getBoundingClientRect()
  showMenu.value = true
  menuDashboardId.value = dashboardId
  menuPosition.value = {
    top: `${rect.bottom + window.scrollY + 6}px`,
    left: `${rect.left + window.scrollX}px`
  }
}

// Закрытие меню
function closeMenu() {
  showMenu.value = false
}

// Получение дашборда по ID
function getDashboardById(id) {
  return items.value.find(d => d.id === id)
}

// Удаление дашборда
function askDelete(dashboard) {
  dashboardToDelete.value = dashboard
  showDeleteDialog.value = true
  isDeleteLocked.value = true
  deleteCountdown.value = 3
  closeMenu()
  
  if (countdownTimer) clearInterval(countdownTimer)
  countdownTimer = setInterval(() => {
    if (deleteCountdown.value > 1) {
      deleteCountdown.value -= 1
    } else {
      isDeleteLocked.value = false
      clearInterval(countdownTimer)
    }
  }, 1000)
}

function cancelDelete() {
  showDeleteDialog.value = false
  dashboardToDelete.value = null
  isDeleteLocked.value = false
  if (countdownTimer) clearInterval(countdownTimer)
}

async function confirmDelete() {
  if (isDeleteLocked.value || !dashboardToDelete.value) return
  
  const endpoint = `/bi_analysis/bi_dashboards/${dashboardToDelete.value.id}/`
  
  try {
    const res = await apiClient.delete(endpoint)
    if (res.success !== false) {
      toast.success('Дашборд успешно удален')
      // Удаляем из списка
      const idx = items.value.findIndex(item => item.id === dashboardToDelete.value.id)
      if (idx !== -1) items.value.splice(idx, 1)
      cancelDelete()
    } else {
      toast.error('Ошибка при удалении: ' + (res.message || ''))
      cancelDelete()
    }
  } catch (err) {
    toast.error('Ошибка при удалении: ' + (err.message || err))
    cancelDelete()
  }
}

// Закрытие меню при клике вне его
function handleClickOutside(event) {
  if (showMenu.value && !event.target.closest('.menu-dropdown') && !event.target.closest('.card-menu-btn')) {
    closeMenu()
  }
}

function openSettings() {
  showSettingsModal.value = true
}

function closeSettings() {
  showSettingsModal.value = false
}

function resetSettings() {
  gridSettings.value = { ...defaultSettings }
  toast.info('Настройки сброшены')
}

onMounted(() => {
  fetchItems()
  document.addEventListener('click', handleClickOutside)
  
  // Применяем настройки по умолчанию для сортировки
  if (gridSettings.value.defaultSort) {
    sort.value = gridSettings.value.defaultSort
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<template>
  <div class="dashboard-list-page">
    <!-- Декоративные элементы -->
    <div class="decorative-elements">
      <div class="decorative-circle decorative-circle-1"></div>
      <div class="decorative-circle decorative-circle-2"></div>
      <div class="decorative-circle decorative-circle-3"></div>
    </div>

    <div class="page-content">
      <!-- Кнопка настроек (правый верхний угол) -->
      <button 
        type="button" 
        class="settings-button-top-right" 
        @click="openSettings"
        title="Настройки отображения"
      >
        <Settings :size="20" />
      </button>
      <!-- Панель управления -->
      <div class="control-panel">
        <div class="search-wrapper">
          <Search :size="18" class="search-icon" />
          <input 
            class="search-input" 
            :placeholder="config.searchPlaceholder || 'Введите для поиска...'" 
            v-model="search" 
          />
        </div>
        <select class="sort-select" v-model="sort">
          <option value="new">Сначала новые</option>
          <option value="old">Сначала старые</option>
          <option value="az">А-Я</option>
          <option value="za">Я-А</option>
        </select>
        <button 
          v-if="config.createRoute && config.createButtonText"
          type="button" 
          class="create-button" 
          :style="{ width: config.createButtonWidth || '11rem' }" 
          @click="goToCreate"
        >
          {{ config.createButtonText }}
        </button>
      </div>
      
      <!-- Карточки дашбордов -->
      <div class="cards-grid-wrapper">
        <div v-if="loading" class="loader-center">
          <span class="loader"></span>
        </div>
        <div v-else-if="filteredItems.length === 0" class="empty-state">
          <LayoutDashboard :size="48" class="empty-icon" />
          <p class="empty-text">Нет дашбордов</p>
          <p class="empty-description">Создайте новый дашборд, чтобы начать работу</p>
        </div>
        <div v-else class="cards-grid" :style="gridStyle" :class="`card-size-${gridSettings.cardSize}`">
          <div
            v-for="dashboard in filteredItems"
            :key="dashboard.id"
            class="dashboard-card"
            @click="goToDashboardView(dashboard)"
          >
            <div class="card-header">
              <div class="card-icon-wrapper">
                <LayoutDashboard :size="24" class="card-icon" />
              </div>
              <button class="card-menu-btn" @click.stop="onMoreClick($event, dashboard.id)">
                <MoreHorizontal :size="18" />
              </button>
            </div>
            <div class="card-body">
              <h3 class="card-title">{{ dashboard.name }}</h3>
              <p v-if="gridSettings.showDescription && dashboard.description" class="card-description">{{ dashboard.description }}</p>
              <div v-if="gridSettings.showDate" class="card-meta">
                <span class="card-date">{{ new Date(dashboard.created_at).toLocaleDateString() }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Меню действий -->
    <teleport to="body">
      <div v-if="showMenu" class="menu-dropdown" :style="menuPosition" @mouseleave="closeMenu">
        <div class="menu-item" @click="goToDashboardViewFromMenu(getDashboardById(menuDashboardId))">
          <Eye :size="18" :stroke-width="2" />
          Просмотр
        </div>
        <div class="menu-item" @click="goToDashboardEdit(getDashboardById(menuDashboardId))">
          <Pencil :size="18" :stroke-width="2" />
          Редактировать
        </div>
        <hr>
        <div class="menu-item danger" @click="askDelete(getDashboardById(menuDashboardId))">
          <Trash2 :size="18" :stroke-width="2" />
          Удалить
        </div>
      </div>
    </teleport>

    <!-- Модальное окно удаления -->
    <ConfirmDialog
      :show="showDeleteDialog"
      title="Удаление дашборда"
      :message="`Вы действительно хотите удалить дашборд &quot;${dashboardToDelete?.name || 'элемент'}&quot;?`"
      confirm-text="Удалить"
      cancel-text="Отмена"
      :loading="isDeleteLocked"
      @confirm="confirmDelete"
      @close="cancelDelete"
    />

    <!-- Модальное окно настроек -->
    <ModalCenter
      modal-id="dashboardListSettingsModal"
      standalone
      :visible="showSettingsModal"
      title="Настройки отображения"
      :dialog-style="{ width: '720px', maxWidth: 'calc(100vw - 4rem)' }"
      :z-index="10001"
      @close="closeSettings"
    >
      <div class="settings-section">
        <label class="settings-label">Размер карточек</label>
        <div class="settings-options">
          <button
            class="settings-option"
            :class="{ active: gridSettings.cardSize === 'small' }"
            @click="gridSettings.cardSize = 'small'"
          >
            Маленькие
          </button>
          <button
            class="settings-option"
            :class="{ active: gridSettings.cardSize === 'medium' }"
            @click="gridSettings.cardSize = 'medium'"
          >
            Средние
          </button>
          <button
            class="settings-option"
            :class="{ active: gridSettings.cardSize === 'large' }"
            @click="gridSettings.cardSize = 'large'"
          >
            Большие
          </button>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">Минимальная ширина карточки: {{ gridSettings.minCardWidth }}px</label>
        <input
          type="range"
          class="settings-range"
          min="200"
          max="400"
          step="20"
          v-model.number="gridSettings.minCardWidth"
        />
        <div class="settings-range-labels">
          <span>200px</span>
          <span>400px</span>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">Отступ между карточками: {{ gridSettings.gridGap }}rem</label>
        <input
          type="range"
          class="settings-range"
          min="0.5"
          max="3"
          step="0.5"
          v-model.number="gridSettings.gridGap"
        />
        <div class="settings-range-labels">
          <span>0.5rem</span>
          <span>3rem</span>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">Отображение элементов</label>
        <div class="settings-checkboxes">
          <label class="settings-checkbox">
            <input type="checkbox" v-model="gridSettings.showDescription" />
            <span>Показывать описание</span>
          </label>
          <label class="settings-checkbox">
            <input type="checkbox" v-model="gridSettings.showDate" />
            <span>Показывать дату создания</span>
          </label>
        </div>
      </div>

      <div class="settings-section">
        <label class="settings-label">Сортировка по умолчанию</label>
        <select class="settings-select" v-model="gridSettings.defaultSort">
          <option value="new">Сначала новые</option>
          <option value="old">Сначала старые</option>
          <option value="az">А-Я</option>
          <option value="za">Я-А</option>
        </select>
      </div>

      <template #footer>
        <div class="settings-footer">
          <button class="settings-btn settings-btn-secondary" @click="resetSettings">
            Сбросить
          </button>
          <div class="settings-actions-right">
            <button class="settings-btn settings-btn-secondary" @click="closeSettings">
              Отмена
            </button>
            <button class="settings-btn settings-btn-primary" @click="saveSettings(); closeSettings()">
              Сохранить
            </button>
          </div>
        </div>
      </template>
    </ModalCenter>

    <!-- Модальное окно создания дашборда -->
    <ModalCenter
      modal-id="dashboardListCreateModal"
      standalone
      :visible="showCreateModal"
      title="Создать дашборд"
      :dialog-style="{ width: '500px', maxWidth: 'calc(100vw - 4rem)' }"
      :z-index="10001"
      @close="closeCreateModal"
    >
      <div class="create-modal-field">
        <label class="create-modal-label">Название дашборда</label>
        <input
          type="text"
          class="create-modal-input"
          v-model="newDashboardName"
          placeholder="Введите название дашборда"
          @keyup.enter="createDashboard"
          :disabled="isCreating"
          autofocus
        />
      </div>

      <template #footer>
        <button class="create-modal-btn create-modal-btn-secondary" @click="closeCreateModal" :disabled="isCreating">
          Отмена
        </button>
        <button class="create-modal-btn create-modal-btn-primary" @click="createDashboard" :disabled="isCreating || !newDashboardName.trim()">
          Создать
        </button>
      </template>
    </ModalCenter>
  </div>
</template>

<style scoped lang="scss">
@import '@/scss/_variables.scss';
@import '../scss/_bi-theme.scss';

.dashboard-list-page {
  @include bi-burgundy-tokens;
  position: relative;
  width: 100%;
  height: 90vh;
  min-height: 90vh;
  max-height: 90vh;
  padding: 0;
  overflow: hidden;
  background: var(--color-background);
  margin: 0 auto;
}

.dashboard-list-page::before {
  display: none;
}

.decorative-elements {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
  display: none;
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

.page-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: transparent;
}

.control-panel {
  display: flex;
  gap: 1rem;
  flex-wrap: nowrap;
  flex-shrink: 0;
  padding: 1.25rem 1rem;
  background: var(--color-primary-background);
  border-bottom: 1px solid var(--color-border);
}

.search-wrapper {
  flex: 1;
  max-width: 25rem;
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
  flex: 1;
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

.sort-select {
  width: 11rem;
  background: var(--color-primary-background);
  color: var(--color-primary-text);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 14px;
  transition: all 0.2s ease;
  cursor: pointer;

  &:focus {
    border-color: rgba(var(--bi-accent-rgb), 0.5);
    box-shadow: 0 0 0 3px rgba(var(--bi-accent-rgb), 0.12);
    outline: none;
  }
}

.settings-button-top-right {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 40px;
  height: 40px;
  background: transparent;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--color-secondary-text);
  z-index: 1000;

  &:hover {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.15);
    color: var(--color-primary-text);
  }

  &:active {
    background: rgba(0, 0, 0, 0.06);
    transform: scale(0.95);
  }
}

.create-button {
  background: var(--bi-accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1.5rem;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 2px rgba(var(--bi-accent-rgb), 0.3);

  &:hover {
    background: var(--bi-accent-hover);
    box-shadow: 0 2px 8px rgba(var(--bi-accent-rgb), 0.35);
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
    background: var(--bi-accent-active);
  }
}

.cards-grid-wrapper {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  padding: 0 1rem;
}

.cards-grid {
  display: grid;
  padding: 0.75rem 0;

  &.card-size-small .dashboard-card {
    min-height: 140px;
    padding: 1rem;

    .card-icon-wrapper {
      width: 36px;
      height: 36px;
    }

    .card-title {
      font-size: 14px;
    }

    .card-description {
      font-size: 12px;
    }
  }

  &.card-size-medium .dashboard-card {
    min-height: 180px;
    padding: 1.5rem;
  }

  &.card-size-large .dashboard-card {
    min-height: 220px;
    padding: 2rem;

    .card-icon-wrapper {
      width: 56px;
      height: 56px;
    }

    .card-title {
      font-size: 18px;
    }

    .card-description {
      font-size: 14px;
    }
  }
}

.dashboard-card {
  background: var(--color-primary-background);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: visible;
  min-height: 180px;
  display: flex;
  flex-direction: column;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
    background: linear-gradient(90deg,
      transparent 0%,
      rgba(var(--bi-accent-rgb), 0.6) 50%,
      transparent 100%);
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  &:hover {
    border-color: rgba(var(--bi-accent-rgb), 0.4);
    transform: translateY(-4px);
    box-shadow:
      0 8px 24px rgba(0, 0, 0, 0.10),
      0 2px 8px rgba(var(--bi-accent-rgb), 0.18);

    &::before {
      opacity: 1;
      height: 3px;
    }

    .card-icon {
      transform: scale(1.12);
    }

    .card-icon-wrapper {
      background: rgba(var(--bi-accent-rgb), 0.18);
    }
  }

  &:active {
    transform: translateY(-1px);
  }
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.25rem;
  margin: -0.25rem -0.25rem 1rem -0.25rem;
}

.card-icon-wrapper {
  width: 48px;
  height: 48px;
  background: rgba(var(--bs-info-rgb), 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--bs-info);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin: 0.25rem;
  flex-shrink: 0;
}

.card-icon {
  transition: transform 0.3s ease;
}

.card-menu-btn {
  background: transparent;
  border: none;
  color: var(--color-secondary-text);
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin: -0.25rem;
  min-width: 32px;
  min-height: 32px;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(var(--bs-info-rgb), 0.1);
    border-radius: 8px;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    background: rgba(var(--bs-info-rgb), 0.15);
    border: 1px solid rgba(var(--bs-info-rgb), 0.3);
    color: var(--bs-info);
    box-shadow: 
      0 2px 8px rgba(var(--bs-info-rgb), 0.2),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
    transform: scale(1.1);
    margin: -0.5rem;

    &::before {
      opacity: 1;
    }
  }

  &:active {
    transform: scale(1.05);
  }
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-primary-text);
  margin: 0 0 0.5rem 0;
  line-height: 1.4;
}

.card-description {
  font-size: 13px;
  color: var(--color-secondary-text);
  margin: 0 0 1rem 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.card-date {
  font-size: 12px;
  color: var(--color-secondary-text);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.empty-icon {
  color: var(--color-secondary-text);
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-primary-text);
  margin: 0 0 0.5rem 0;
}

.empty-description {
  font-size: 14px;
  color: var(--color-secondary-text);
  margin: 0;
}

.loader-center {
  min-height: 240px;
  display: flex; 
  align-items: center; 
  justify-content: center;
}

.loader {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-top: 4px solid var(--color-accent);
  border-radius: 50%;
  width: 42px; 
  height: 42px;
  animation: spin 1s linear infinite;
}

@keyframes spin { 
  100% { 
    transform: rotate(360deg); 
  } 
}

// Адаптивность
@media (max-width: 768px) {
  .cards-grid {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
  
  .control-panel {
    flex-wrap: wrap;
  }
  
  .search-wrapper {
    max-width: 100%;
  }
}

.menu-dropdown {
  position: fixed;
  background-color: var(--color-primary-background);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  padding: 8px 0;
  min-width: 160px;
  z-index: 10000;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: var(--color-primary-text);
  cursor: pointer;
  transition: background 0.2s ease;
  font-size: 14px;

  &:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  &.danger {
    color: #f87171;

    &:hover {
      background-color: rgba(248, 113, 113, 0.1);
    }
  }
}

.menu-dropdown hr {
  margin: 4px 0;
  border: none;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.settings-section {
  margin-bottom: 2rem;

  &:last-of-type {
    margin-bottom: 1rem;
  }
}

.settings-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary-text);
  margin-bottom: 0.75rem;
}

.settings-options {
  display: flex;
  gap: 0.5rem;
}

.settings-option {
  flex: 1;
  padding: 0.75rem 1.25rem;
  background: var(--color-secondary-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--color-secondary-text);

  &:hover {
    border-color: rgba(var(--bi-accent-rgb), 0.4);
    color: var(--color-primary-text);
  }

  &.active {
    background: var(--bi-accent);
    border-color: var(--bi-accent);
    color: #fff;
    font-weight: 600;
  }
}

.settings-range {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: rgba(0, 0, 0, 0.1);
  outline: none;
  margin: 0.5rem 0;

  &::-webkit-slider-thumb {
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--color-accent, #6D001A);
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  &::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--color-accent, #6D001A);
    cursor: pointer;
    border: none;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }
}

.settings-range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-secondary-text);
  margin-top: 0.25rem;
}

.settings-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.settings-checkbox {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-primary-text);
  padding: 0.625rem;
  background: var(--color-secondary-background);
  border-radius: 8px;
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;

  &:hover {
    border-color: rgba(var(--bi-accent-rgb), 0.3);
  }

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
    accent-color: var(--bi-accent);
  }
}

.settings-select {
  width: 100%;
  background: var(--color-primary-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-size: 14px;
  color: var(--color-primary-text);
  cursor: pointer;
  transition: all 0.2s ease;

  &:focus {
    border-color: rgba(var(--bi-accent-rgb), 0.5);
    outline: none;
    box-shadow: 0 0 0 3px rgba(var(--bi-accent-rgb), 0.15);
  }
}

.settings-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 0.75rem;
}

.settings-actions-right {
  display: flex;
  gap: 0.75rem;
}

.settings-btn {
  padding: 0.75rem 1.75rem;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;

  &.settings-btn-secondary {
    background: var(--color-secondary-background);
    border: 1px solid var(--color-border);
    color: var(--color-primary-text);

    &:hover {
      border-color: rgba(var(--bi-accent-rgb), 0.4);
      transform: translateY(-1px);
    }
  }

  &.settings-btn-primary {
    background: var(--bi-accent);
    color: #fff;
    box-shadow: 0 1px 2px rgba(var(--bi-accent-rgb), 0.3);
    border: 1px solid var(--bi-accent);

    &:hover {
      background: var(--bi-accent-hover);
      box-shadow: 0 2px 8px rgba(var(--bi-accent-rgb), 0.35);
      transform: translateY(-1px);
    }

    &:active {
      transform: translateY(0);
      background: var(--bi-accent-active);
    }
  }
}

// Модальное окно создания дашборда — контент
.create-modal-field {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.create-modal-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary-text);
}

.create-modal-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--color-primary-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 14px;
  color: var(--color-primary-text);
  transition: all 0.2s ease;

  &:focus {
    border-color: rgba(var(--bi-accent-rgb), 0.5);
    box-shadow: 0 0 0 3px rgba(var(--bi-accent-rgb), 0.12);
    outline: none;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  &::placeholder {
    color: var(--color-secondary-text);
    opacity: 0.6;
  }
}

.create-modal-btn {
  padding: 0.75rem 1.75rem;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.create-modal-btn-secondary {
    background: var(--color-secondary-background);
    border: 1px solid var(--color-border);
    color: var(--color-primary-text);

    &:hover:not(:disabled) {
      border-color: rgba(var(--bi-accent-rgb), 0.4);
      transform: translateY(-1px);
    }
  }

  &.create-modal-btn-primary {
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
