<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { Workflow, Search, MoreHorizontal, Pencil, Trash2, BarChart3, X } from 'lucide-vue-next'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { fetchPipelines, createPipeline, deletePipeline } from '../js/pipelineApi.js'

const router = useRouter()
const toast = useToast()

const items = ref([])
const search = ref('')
const sort = ref('new')
const includeTemporary = ref(false)
const loading = ref(false)

const showMenu = ref(false)
const menuPosition = ref({ top: '0px', left: '0px' })
const menuItemId = ref(null)

const showDeleteDialog = ref(false)
const itemToDelete = ref(null)

const showCreateModal = ref(false)
const newName = ref('')
const isCreating = ref(false)

async function loadItems() {
  loading.value = true
  try {
    items.value = await fetchPipelines({ includeDashboardOnly: includeTemporary.value })
  } catch (err) {
    console.error('Pipeline load error:', err)
    toast.error('Ошибка загрузки пайплайнов')
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  const term = search.value.toLowerCase()
  let list = [...items.value]
  if (term) {
    list = list.filter(item =>
      item.name?.toLowerCase().includes(term) ||
      item.description?.toLowerCase().includes(term)
    )
  }
  switch (sort.value) {
    case 'new': list.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)); break
    case 'old': list.sort((a, b) => new Date(a.updated_at) - new Date(b.updated_at)); break
    case 'az': list.sort((a, b) => a.name.localeCompare(b.name)); break
    case 'za': list.sort((a, b) => b.name.localeCompare(a.name)); break
  }
  return list
})

function goToCreate() {
  newName.value = ''
  showCreateModal.value = true
}

function closeCreateModal() {
  showCreateModal.value = false
  newName.value = ''
}

async function handleCreate() {
  if (!newName.value.trim()) {
    toast.error('Введите название пайплайна')
    return
  }
  try {
    isCreating.value = true
    const data = await createPipeline({ name: newName.value.trim(), description: '' })
    if (data?.id) {
      toast.success('Пайплайн создан')
      closeCreateModal()
      router.push(`/bi-modern/pipelines/${data.id}`)
    }
  } catch (err) {
    toast.error('Ошибка создания: ' + (err.message || err))
  } finally {
    isCreating.value = false
  }
}

function goToEditor(pipeline) {
  if (pipeline?.id) router.push(`/bi-modern/pipelines/${pipeline.id}`)
}

function onMoreClick(event, id) {
  event.stopPropagation()
  const rect = event.currentTarget.getBoundingClientRect()
  showMenu.value = true
  menuItemId.value = id
  menuPosition.value = {
    top: `${rect.bottom + window.scrollY + 6}px`,
    left: `${rect.left + window.scrollX}px`
  }
}

function closeMenu() { showMenu.value = false }

function getItemById(id) { return items.value.find(d => d.id === id) }

function askDelete(pipeline) {
  itemToDelete.value = pipeline
  showDeleteDialog.value = true
  closeMenu()
}

function cancelDelete() {
  showDeleteDialog.value = false
  itemToDelete.value = null
}

async function confirmDelete() {
  if (!itemToDelete.value) return
  try {
    await deletePipeline(itemToDelete.value.id)
    toast.success('Пайплайн удален')
    items.value = items.value.filter(item => item.id !== itemToDelete.value.id)
    cancelDelete()
  } catch (err) {
    toast.error('Ошибка удаления: ' + (err.message || err))
    cancelDelete()
  }
}

function handleClickOutside(event) {
  if (showMenu.value && !event.target.closest('.menu-dropdown') && !event.target.closest('.card-menu-btn')) {
    closeMenu()
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString()
}

onMounted(() => {
  loadItems()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div class="pipeline-list-page">
    <div class="page-content">
      <div class="control-panel">
        <div class="search-wrapper">
          <Search :size="18" class="search-icon" />
          <input class="search-input" placeholder="Поиск пайплайнов..." v-model="search" />
        </div>
        <select class="sort-select" v-model="sort">
          <option value="new">Сначала новые</option>
          <option value="old">Сначала старые</option>
          <option value="az">А-Я</option>
          <option value="za">Я-А</option>
        </select>
        <label class="include-temporary-label">
          <input type="checkbox" v-model="includeTemporary" @change="loadItems" />
          <span>Временные (дашборд)</span>
        </label>
        <button type="button" class="create-button" @click="goToCreate">
          Создать пайплайн
        </button>
      </div>

      <div class="cards-grid-wrapper">
        <div v-if="loading" class="loader-center">
          <span class="loader"></span>
        </div>
        <div v-else-if="filteredItems.length === 0" class="empty-state">
          <Workflow :size="48" class="empty-icon" />
          <p class="empty-text">Нет пайплайнов</p>
          <p class="empty-description">Создайте пайплайн для обработки данных и построения графиков</p>
        </div>
        <div v-else class="cards-grid">
          <div
            v-for="pipeline in filteredItems"
            :key="pipeline.id"
            class="pipeline-card"
            @click="goToEditor(pipeline)"
          >
            <div class="card-header">
              <div class="card-icon-wrapper">
                <Workflow :size="24" />
              </div>
              <button class="card-menu-btn" @click.stop="onMoreClick($event, pipeline.id)">
                <MoreHorizontal :size="18" />
              </button>
            </div>
            <div class="card-body">
              <h3 class="card-title">
                {{ pipeline.name }}
                <span v-if="pipeline.is_dashboard_only" class="card-badge-temporary">Временный</span>
              </h3>
              <p v-if="pipeline.description" class="card-description">{{ pipeline.description }}</p>
              <div class="card-meta">
                <span>{{ formatDate(pipeline.updated_at) }}</span>
                <span class="card-charts-count">
                  <BarChart3 :size="14" />
                  {{ pipeline.charts_count || 0 }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <teleport to="body">
      <div v-if="showMenu" class="menu-dropdown" :style="menuPosition" @mouseleave="closeMenu">
        <div class="menu-item" @click="goToEditor(getItemById(menuItemId)); closeMenu()">
          <Pencil :size="18" />
          Редактировать
        </div>
        <hr>
        <div class="menu-item danger" @click="askDelete(getItemById(menuItemId))">
          <Trash2 :size="18" />
          Удалить
        </div>
      </div>
    </teleport>

    <ConfirmDialog
      :show="showDeleteDialog"
      title="Удаление пайплайна"
      :message="itemToDelete?.is_dashboard_only
        ? `Удалить пайплайн «${itemToDelete?.name || ''}»? Будут удалены пайплайн, его графики и блоки этих графиков со всех дашбордов.`
        : `Удалить пайплайн «${itemToDelete?.name || ''}» и все его графики?`"
      confirm-text="Удалить"
      cancel-text="Отмена"
      @confirm="confirmDelete"
      @close="cancelDelete"
    />

    <div v-if="showCreateModal" class="create-modal-overlay" @click="closeCreateModal">
      <div class="create-modal" @click.stop>
        <div class="create-modal-header">
          <h3 class="create-modal-title">Создать пайплайн</h3>
          <button class="create-modal-close" @click="closeCreateModal">
            <X :size="20" />
          </button>
        </div>
        <div class="create-modal-content">
          <div class="create-modal-field">
            <label class="create-modal-label">Название пайплайна</label>
            <input
              type="text"
              class="create-modal-input"
              v-model="newName"
              placeholder="Введите название"
              @keyup.enter="handleCreate"
              :disabled="isCreating"
              autofocus
            />
          </div>
        </div>
        <div class="create-modal-actions">
          <button class="create-modal-btn create-modal-btn-secondary" @click="closeCreateModal" :disabled="isCreating">
            Отмена
          </button>
          <button class="create-modal-btn create-modal-btn-primary" @click="handleCreate" :disabled="isCreating || !newName.trim()">
            Создать
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '../scss/pipeline-list.scss';
</style>
