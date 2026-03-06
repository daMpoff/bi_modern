<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { apiClient } from '@/js/api/manager.js'
import { useRouter } from 'vue-router'
import SimpleTableDataSet from './SimpleTableDataSet.vue'

const props = defineProps({
  config: {
    type: Object,
    required: true,
    validator: (config) => {
      return config.type && config.endpoint
    }
  },
  hideCreateButton: {
    type: Boolean,
    default: false
  }
})

const items = ref([])
const search = ref('')
const sort = ref('new')
const loading = ref(false)

const cols = [
  { key: 'name', label: 'Название' },
  { key: 'created_at', label: 'Дата', format: val => new Date(val).toLocaleDateString() },
  { key: 'actions', label: '' }
]

const router = useRouter()

function goToCreate() {
  if (!props.config.createRoute) return
  if (typeof props.config.createRoute === 'string') {
    router.push(props.config.createRoute)
  } else if (typeof props.config.createRoute === 'object' && props.config.createRoute.name) {
    router.push(props.config.createRoute)
  }
}

async function fetchItems() {
  loading.value = true
  try {
    const { data } = await apiClient.get(props.config.endpoint)
    const rows = Array.isArray(data) ? data : (data.results || [])
    if (props.config.mapData) {
      items.value = rows.map(props.config.mapData)
    } else {
      items.value = rows.map(item => ({
        id: item.id,
        name: item.name || '—',
        created_at: item.created_at,
        owner_username: item.owner_username,
        type: props.config.type,
        ...item
      }))
    }
  } catch (err) {
    console.error(`Ошибка загрузки ${props.config.type}:`, err)
  } finally {
    loading.value = false
  }
}

function handleDeleteRow(row) {
  const idx = items.value.findIndex(item => item.id === row.id)
  if (idx !== -1) items.value.splice(idx, 1)
}

const transformedData = computed(() => {
  const term = search.value.toLowerCase()
  let list = [...items.value]
  if (term) {
    if (props.config.filterFunction) {
      list = list.filter(props.config.filterFunction(term))
    } else {
      list = list.filter(item =>
        item.name?.toLowerCase().includes(term) ||
        item.owner_username?.toLowerCase().includes(term)
      )
    }
  }
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

onMounted(fetchItems)
</script>

<template>
  <div class="generic-list-page">
    <div class="decorative-elements">
      <div class="decorative-circle decorative-circle-1"></div>
      <div class="decorative-circle decorative-circle-2"></div>
      <div class="decorative-circle decorative-circle-3"></div>
    </div>
    <div class="page-content">
      <div class="control-panel">
        <input
          class="search-input"
          :placeholder="config.searchPlaceholder || 'Введите для поиска...'"
          v-model="search"
        />
        <select class="sort-select" v-model="sort">
          <option value="new">Сначала новые</option>
          <option value="old">Сначала старые</option>
          <option value="az">А-Я</option>
          <option value="za">Я-А</option>
        </select>
        <button
          v-if="!hideCreateButton && config.createRoute && config.createButtonText"
          type="button"
          class="create-button"
          :style="{ width: config.createButtonWidth || '11rem' }"
          @click="goToCreate"
        >
          {{ config.createButtonText }}
        </button>
      </div>
      <div class="table-wrapper">
        <div v-if="loading" class="loader-center">
          <span class="loader"></span>
        </div>
        <SimpleTableDataSet
          v-else
          :cols="cols"
          :current-page="config.type"
          :users="transformedData"
          @delete-row="handleDeleteRow"
        />
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.generic-list-page {
  position: relative;
  width: 100%;
  height: 100%;
  padding: 2rem;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.92) 100%);
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
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -30px) scale(1.1); }
  50% { transform: translate(-20px, 20px) scale(0.9); }
  75% { transform: translate(20px, 30px) scale(1.05); }
}

.page-content {
  position: relative;
  z-index: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.control-panel {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: nowrap;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  max-width: 25rem;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  padding: 0.5rem 1rem;
  font-size: 14px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  &:focus {
    background: rgba(255, 255, 255, 0.9);
    border-color: var(--color-accent);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 0 0 3px rgba(var(--bs-info-rgb), 0.1);
    outline: none;
  }
}

.sort-select {
  width: 11rem;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  padding: 0.5rem 1rem;
  font-size: 14px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  &:focus {
    background: rgba(255, 255, 255, 0.9);
    border-color: var(--color-accent);
    outline: none;
  }
}

.create-button {
  background: var(--color-accent, #e53935);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 0.5rem 1.5rem;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(229, 57, 53, 0.3);
  &:hover {
    background: #c62828;
    box-shadow: 0 4px 12px rgba(229, 57, 53, 0.4);
    transform: translateY(-2px);
  }
}

.table-wrapper {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
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
  100% { transform: rotate(360deg); }
}
</style>
