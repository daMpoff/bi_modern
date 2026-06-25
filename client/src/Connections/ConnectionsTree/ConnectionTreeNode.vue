<template>
  <div class="tree-node" :class="{ 'tree-node--expanded': isExpanded }">
    <div
      class="tree-node__content"
      :class="{ 'tree-node__content--drop-target': isDropTarget, 'tree-node__content--uploading': isUploading }"
      :style="{ paddingLeft: `${level * 20 + 12}px` }"
      @click="handleClick"
      @dragover="onDragover"
      @dragenter="onDragenter"
      @dragleave="onDragleave"
      @drop="onDrop"
    >
      <div class="tree-node__left">
        <button
          v-if="hasChildren"
          class="tree-node__expand-btn"
          @click.stop="toggleExpand"
        >
          <ChevronRight :size="16" :class="{ 'rotated': isExpanded }" />
        </button>
        <div v-else class="tree-node__spacer"></div>
        
        <div class="tree-node__icon">
          <img v-if="nodeIconUrl" :src="nodeIconUrl" alt="" class="tree-node__icon-img" />
          <component v-else :is="nodeIcon" :size="18" />
        </div>
        
        <button
          v-if="isFileConnection"
          type="button"
          class="tree-node__add-file-btn"
          title="Добавить файл"
          @click.stop="triggerAddFile"
        >
          <Plus :size="14" />
          <span class="tree-node__add-file-label">Добавить файл</span>
        </button>
        <input
          v-if="isFileConnection"
          ref="fileInputRef"
          type="file"
          accept=".csv,.xlsx,.txt"
          multiple
          style="display: none"
          @change="onFileInputChange"
        />
        
        <span class="tree-node__label" :title="nodeLabel">{{ nodeLabel }}</span>
      </div>
      
      <template v-if="isFileConnection && isUploading">
        <div class="tree-node__upload-spinner">
          <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">Загрузка...</span>
          </div>
        </div>
      </template>
      
      <!-- Кнопка удаления для файлов -->
      <button
        v-if="nodeType === 'file'"
        class="tree-node__delete-btn"
        @click.stop="handleDeleteFile"
        title="Удалить файл"
      >
        <Trash2 :size="14" />
      </button>
    </div>

    <div v-if="hasChildren && isExpanded" class="tree-node__children">
      <template v-if="isLoading">
        <div class="tree-node__loading">
          <div class="spinner-border spinner-border-sm" role="status">
            <span class="visually-hidden">Загрузка...</span>
          </div>
        </div>
      </template>
      <template v-else>
        <ConnectionTreeNode
          v-for="child in children"
          :key="child.id || child.name"
          :node="child"
          :level="level + 1"
          :expanded-nodes="expandedNodes"
          @toggle-expand="$emit('toggle-expand', $event)"
          @node-click="$emit('node-click', $event)"
          @file-deleted="handleFileDeleted"
        />
      </template>
    </div>
    
    <ConfirmDialog
      :show="showConfirmDialog"
      title="Удаление файла"
      :message="`Вы уверены, что хотите удалить файл &quot;${nodeLabel}&quot;? Это действие нельзя отменить.`"
      confirm-text="Удалить"
      cancel-text="Отмена"
      @confirm="confirmDeleteFile"
      @close="showConfirmDialog = false"
    />
    <XlsxSheetPicker
      :visible="sheetPickerVisible"
      :filename="sheetPickerFilename"
      :sheets="sheetPickerSheets"
      :single-select="false"
      @confirm="onSheetPickerConfirm"
      @cancel="onSheetPickerCancel"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ChevronRight, Database, FileText, Table, File, Folder, Trash2, Plus } from 'lucide-vue-next'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useToast } from 'vue-toastification'
import XlsxSheetPicker from '../Files/FilePreview/XlsxSheetPicker.vue'
import { MAX_UPLOAD_SIZE_MB, MAX_UPLOAD_FILES } from '@/modules/bi_analysis_modern/client/src/js/uploadConfig'
import { logError } from '@/js/utils/logError.js'

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  level: {
    type: Number,
    default: 0
  },
  expandedNodes: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['toggle-expand', 'node-click', 'file-deleted'])

const children = ref([])
const isLoading = ref(false)
const toast = useToast()
const showConfirmDialog = ref(false)
const isDeleting = ref(false)

const isDropTarget = ref(false)
const dragEnterCount = ref(0)
const isUploading = ref(false)
const fileInputRef = ref(null)
const sheetPickerVisible = ref(false)
const sheetPickerSheets = ref([])
const sheetPickerFilename = ref('')
const currentXlsxFile = ref(null)
const pendingFilesQueue = ref([])

const ACCEPTED_EXT = ['.csv', '.xlsx', '.txt']

// Определение типа узла
const nodeType = computed(() => {
  if (props.node.connector_type) {
    return 'connection'
  } else if (props.node.schema !== undefined || props.node.table_name) {
    return 'table'
  } else if (props.node.file_type || props.node.name?.endsWith('.csv') || props.node.name?.endsWith('.xlsx')) {
    return 'file'
  } else if (props.node.data_type || props.node.type) {
    return 'column'
  }
  return 'unknown'
})

const isFileConnection = computed(() => {
  return nodeType.value === 'connection' && (props.node.connector_type || '').toLowerCase() === 'file'
})

// URL иконки для SVG (для подключений и файлов)
const nodeIconUrl = computed(() => {
  if (nodeType.value === 'connection' && props.node.connector_type) {
    const connectorType = props.node.connector_type.toLowerCase()
    switch (connectorType) {
      case 'postgres':
      case 'postgresql':
        return '/src/core/bi/assets/icons/postgres.svg'
      case 'clickhouse':
        return '/src/core/bi/assets/icons/clickhouse.svg'
      case 'mssql':
        return '/src/core/bi/assets/icons/mssql.svg'
      case 'file':
        return '/src/core/bi/assets/icons/folder_windows_style.svg'
      default:
        return null
    }
  }
  
  // Для файлов определяем иконку по расширению
  if (nodeType.value === 'file') {
    const fileName = props.node.name || ''
    const fileExtension = fileName.toLowerCase().split('.').pop()
    
    switch (fileExtension) {
      case 'csv':
        return '/src/core/bi/assets/icons/csv.svg'
      case 'xlsx':
      case 'xls':
        return '/src/core/bi/assets/icons/xlsx.svg'
      case 'txt':
        return '/src/core/bi/assets/icons/txt.svg'
      default:
        // Если есть file_type в данных узла, используем его
        const fileType = props.node.file_type?.toLowerCase()
        if (fileType === 'csv') {
          return '/src/core/bi/assets/icons/csv.svg'
        } else if (fileType === 'xlsx' || fileType === 'xls') {
          return '/src/core/bi/assets/icons/xlsx.svg'
        } else if (fileType === 'txt') {
          return '/src/core/bi/assets/icons/txt.svg'
        }
        // По умолчанию используем иконку папки
        return '/src/core/bi/assets/icons/folder_windows_style.svg'
    }
  }
  
  return null
})

// Иконка узла (для не-подключений используем Lucide иконки)
const nodeIcon = computed(() => {
  // Для подключений используем SVG через nodeIconUrl
  if (nodeType.value === 'connection') {
    return null
  }
  
  switch (nodeType.value) {
    case 'table':
      return Table
    case 'file':
      return FileText
    case 'column':
      return File
    default:
      return Folder
  }
})

// Метка узла
const nodeLabel = computed(() => {
  return props.node.name || props.node.table_name || props.node.column_name || 'Без имени'
})

// Есть ли дочерние элементы
const hasChildren = computed(() => {
  if (nodeType.value === 'connection') {
    return true // Подключения всегда могут иметь дочерние элементы
  } else if (nodeType.value === 'table') {
    return false // Таблицы — листовые узлы, колонки в предпросмотре
  } else if (nodeType.value === 'file') {
    return false // Файлы не раскрываются - они открываются при клике для предпросмотра
  }
  return false // Колонки - конечные элементы
})

// Раскрыт ли узел
const isExpanded = computed(() => {
  return !!props.expandedNodes[getNodeId()]
})

// Получение ID узла
function getNodeId() {
  if (props.node.id) return props.node.id
  if (props.node.table_name) return `${props.node.schema || 'public'}.${props.node.table_name}`
  if (props.node.column_name) return `${props.node.table_name || ''}_${props.node.column_name}`
  return props.node.name || ''
}

// Переключение раскрытия
async function toggleExpand() {
  const nodeId = getNodeId()
  const newExpandedState = !isExpanded.value
  
  if (newExpandedState && children.value.length === 0) {
    await loadChildren()
  }
  
  emit('toggle-expand', nodeId, newExpandedState)
}

// Загрузка дочерних элементов
async function loadChildren() {
  if (isLoading.value) return
  
  isLoading.value = true
  try {
    if (nodeType.value === 'connection') {
      await loadConnectionChildren()
    } else if (nodeType.value === 'table') {
      await loadTableColumns()
    } else if (nodeType.value === 'file') {
      await loadFileColumns()
    }
  } catch (error) {
    logError('Ошибка загрузки дочерних элементов:', error)
  } finally {
    isLoading.value = false
  }
}

// Загрузка таблиц/файлов подключения
async function loadConnectionChildren() {
  const connection = props.node
  
  if (connection.connector_type === 'file') {
    // Загрузка файлов
    const res = await apiClient.get(biEndpoints.bi.connectionFiles(connection.id))
    if (res.success && res.data) {
      children.value = (res.data || []).map(file => ({
        ...file,
        connection_id: connection.id
      }))
    }
  } else {
    // Загрузка таблиц БД
    try {
      const res = await apiClient.get(biEndpoints.bi.connectionTables(connection.id))
      
      // API может вернуть либо {success: true, data: [...]}, либо просто массив
      const tablesData = res?.data || res || []
      
      if (Array.isArray(tablesData) && tablesData.length > 0) {
        children.value = tablesData.map(table => ({
          ...table,
          connection_id: connection.id,
          table_name: table.name || table.table_name,
          schema: table.schema || 'public'
        }))
      } else {
        children.value = []
      }
    } catch (error) {
      logError('Ошибка загрузки таблиц:', error)
      children.value = []
    }
  }
}

// Загрузка колонок таблицы
async function loadTableColumns() {
  const table = props.node
  const connectionId = table.connection_id
  
  if (!connectionId) return
  
  const res = await apiClient.get(
    biEndpoints.bi.connectionTableColumns(connectionId),
    {
      table_name: table.table_name || table.name,
      schema: table.schema || 'public'
    }
  )
  
  if (res.success && res.data) {
    children.value = (res.data || []).map(column => ({
      ...column,
      connection_id: connectionId,
      table_name: table.table_name || table.name,
      schema: table.schema
    }))
  }
}

// Загрузка колонок файла (пока заглушка, нужно будет реализовать через API)
async function loadFileColumns() {
  // TODO: Реализовать загрузку колонок файла через API
  // Пока возвращаем пустой массив
  children.value = []
}

function onDragover(e) {
  if (!isFileConnection.value) return
  e.preventDefault()
  e.dataTransfer.dropEffect = 'copy'
}

function onDragenter(e) {
  if (!isFileConnection.value) return
  e.preventDefault()
  dragEnterCount.value++
  isDropTarget.value = true
}

function onDragleave(e) {
  if (!isFileConnection.value) return
  e.preventDefault()
  dragEnterCount.value--
  if (dragEnterCount.value <= 0) {
    dragEnterCount.value = 0
    isDropTarget.value = false
  }
}

function onDrop(e) {
  if (!isFileConnection.value) return
  e.preventDefault()
  isDropTarget.value = false
  dragEnterCount.value = 0
  const connectionId = props.node.id
  if (!connectionId) return
  const files = Array.from(e.dataTransfer.files || [])
  if (files.length) processFiles(files, connectionId)
}

function triggerAddFile() {
  if (!fileInputRef.value) return
  fileInputRef.value.value = ''
  fileInputRef.value.click()
}

function onFileInputChange(e) {
  const connectionId = props.node.id
  if (!connectionId || !e.target.files) return
  const files = Array.from(e.target.files)
  e.target.value = ''
  if (files.length) processFiles(files, connectionId)
}

function getAcceptedFiles(files) {
  const list = files.filter(f => {
    const ext = '.' + (f.name || '').split('.').pop()?.toLowerCase()
    return ACCEPTED_EXT.includes(ext)
  })
  return list
}

function validateFiles(files) {
  if (files.length > MAX_UPLOAD_FILES) {
    toast.error(`Можно загрузить не более ${MAX_UPLOAD_FILES} файлов`)
    return false
  }
  const oversized = files.filter(f => f.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024)
  if (oversized.length) {
    toast.error(`Файлы превышают ${MAX_UPLOAD_SIZE_MB} МБ: ${oversized.map(f => f.name).join(', ')}`)
    return false
  }
  const empty = files.filter(f => !f.size)
  if (empty.length) {
    toast.error(`Пустые файлы: ${empty.map(f => f.name).join(', ')}`)
    return false
  }
  return true
}

async function uploadOne(file, sheet = null) {
  const formData = new FormData()
  formData.append('file', file)
  let name = file.name
  if (sheet) {
    const base = file.name.replace(/\.xlsx$/, '')
    name = `${base} – ${sheet}.xlsx`
    formData.append('sheet', sheet)
  }
  const res = await apiClient.upload(biEndpoints.bi.Upload, formData, true)
  if (!res.success) throw new Error(res.error || 'Ошибка загрузки')
  return {
    name,
    temp_path: res.data.temp_path,
    original_filename: res.data.original_filename,
    file_type: res.data.file_type,
    sheet: sheet || null
  }
}

async function finalizeOne(temp, connectionId) {
  const formData = new FormData()
  formData.append('temp_path', temp.temp_path)
  formData.append('name', temp.name)
  formData.append('original_filename', temp.original_filename)
  formData.append('file_type', temp.file_type)
  formData.append('connection', connectionId)
  if (temp.sheet) formData.append('sheet', temp.sheet)
  const res = await apiClient.post(biEndpoints.bi.uploadFinalize, formData)
  if (!res || !res.success) throw new Error(res?.error || res?.message || 'Ошибка финализации')
  return res.data
}

async function processFiles(files, connectionId) {
  const accepted = getAcceptedFiles(files)
  if (!accepted.length) {
    toast.error('Допустимые форматы: .csv, .xlsx, .txt')
    return
  }
  if (!validateFiles(accepted)) return
  isUploading.value = true
  pendingFilesQueue.value = [...accepted]
  try {
    await processQueue(connectionId)
  } catch (err) {
    logError('[ConnectionTreeNode] processFiles:', err)
    toast.error(err?.message || 'Ошибка загрузки файлов')
    finishUpload(connectionId, false)
  }
}

function finishUpload(connectionId, success = true) {
  isUploading.value = false
  pendingFilesQueue.value = []
  if (success) toast.success('Файлы загружены')
  window.dispatchEvent(new CustomEvent('connections-reload'))
  window.dispatchEvent(new CustomEvent('files-reload', { detail: { connectionId } }))
}

async function processQueue(connectionId) {
  if (!pendingFilesQueue.value.length) {
    finishUpload(connectionId)
    return
  }
  try {
    const file = pendingFilesQueue.value[0]
    const isXlsx = file.name && file.name.toLowerCase().endsWith('.xlsx')
    if (isXlsx) {
      const formData = new FormData()
      formData.append('file', file)
      let sheetRes
      try {
        sheetRes = await apiClient.upload(biEndpoints.bi.xlsxSheets, formData)
      } catch (e) {
        pendingFilesQueue.value.shift()
        await processQueue(connectionId)
        return
      }
      const sheets = sheetRes?.success && sheetRes?.data?.sheets ? sheetRes.data.sheets : []
      if (sheets.length > 1) {
        currentXlsxFile.value = file
        sheetPickerSheets.value = sheets
        sheetPickerFilename.value = file.name
        sheetPickerVisible.value = true
        return
      }
      const sheet = sheets[0] || null
      const temp = await uploadOne(file, sheet)
      await finalizeOne(temp, connectionId)
      pendingFilesQueue.value.shift()
      await processQueue(connectionId)
      return
    }
    const temp = await uploadOne(file)
    await finalizeOne(temp, connectionId)
    pendingFilesQueue.value.shift()
    await processQueue(connectionId)
  } catch (err) {
    finishUpload(connectionId, false)
    throw err
  }
}

async function onSheetPickerConfirm(selectedSheets) {
  sheetPickerVisible.value = false
  const file = currentXlsxFile.value
  const connectionId = props.node.id
  if (!file || !selectedSheets?.length || !connectionId) {
    currentXlsxFile.value = null
    pendingFilesQueue.value.shift()
    await processQueue(connectionId)
    return
  }
  try {
    for (const sheet of selectedSheets) {
      const temp = await uploadOne(file, sheet)
      await finalizeOne(temp, connectionId)
    }
  } catch (err) {
    toast.error(err?.message || 'Ошибка загрузки листов')
  }
  currentXlsxFile.value = null
  pendingFilesQueue.value.shift()
  await processQueue(connectionId)
}

function onSheetPickerCancel() {
  sheetPickerVisible.value = false
  currentXlsxFile.value = null
  pendingFilesQueue.value.shift()
  processQueue(props.node.id).catch(() => {})
}

// Обработка клика на узел
function handleClick(event) {
  if (event.target.closest('.tree-node__expand-btn') ||
      event.target.closest('.tree-node__delete-btn') ||
      event.target.closest('.tree-node__add-file-btn')) {
    return
  }
  
  emit('node-click', {
    ...props.node,
    type: nodeType.value,
    id: getNodeId()
  })
}

// Автоматическая загрузка при раскрытии
watch(isExpanded, (newVal) => {
  if (newVal && children.value.length === 0 && hasChildren.value) {
    loadChildren()
  }
})

// Обработка удаления файла из дочернего узла
function handleFileDeleted({ fileId, connectionId }) {
  // Удаляем файл из списка детей, если это подключение с файлами
  if (nodeType.value === 'connection' && props.node.id === connectionId) {
    children.value = children.value.filter(child => child.id !== fileId)
  }
  
  // Пробрасываем событие наверх
  emit('file-deleted', { fileId, connectionId })
}

// Удаление файла
function handleDeleteFile() {
  showConfirmDialog.value = true
}

async function confirmDeleteFile() {
  if (!props.node?.id) {
    toast.error('Ошибка: не найден ID файла')
    return
  }
  
  isDeleting.value = true
  showConfirmDialog.value = false
  
  try {
    const fileId = parseInt(props.node.id, 10)
    
    if (isNaN(fileId)) {
      toast.error('Ошибка: неверный ID файла')
      return
    }
    
    const endpoint = biEndpoints.bi.uploadDelete(fileId)
    const res = await apiClient.delete(endpoint)
    
    if (res && (res.success === true || res.status === 204 || res.status === 200)) {
      toast.success(`Файл "${props.node.name}" успешно удалён`)
      emit('file-deleted', { fileId, connectionId: props.node.connection_id })
    } else if (res && res.success === false) {
      const errorMsg = res.message || res.error || 'Ошибка при удалении файла'
      toast.error(errorMsg)
    } else if (res && (res.status >= 200 && res.status < 300)) {
      toast.success(`Файл "${props.node.name}" успешно удалён`)
      emit('file-deleted', { fileId, connectionId: props.node.connection_id })
    } else {
      logError('Unexpected delete response format:', res)
      toast.error('Неожиданный формат ответа от сервера')
    }
  } catch (error) {
    logError('Ошибка удаления файла:', error)
    const errorMsg = error?.response?.data?.message || 
                     error?.response?.data?.detail ||
                     error?.response?.data?.error ||
                     error?.message || 
                     'Ошибка при удалении файла'
    toast.error(errorMsg)
  } finally {
    isDeleting.value = false
  }
}
</script>

<style scoped lang="scss">
@import '@/scss/_variables.scss';

.tree-node {
  user-select: none;
}

.tree-node__content {
  display: flex;
  align-items: center;
  padding: 0.625rem 0.875rem;
  margin: 0.125rem 0.5rem;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    background: linear-gradient(90deg, rgba(var(--bs-info-rgb), 0.08) 0%, rgba(var(--bs-info-rgb), 0.04) 100%);
    transform: translateX(2px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }
}

.tree-node__left {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex: 1;
  min-width: 0;
}

.tree-node__expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  color: var(--color-secondary-text);
  transition: all 0.2s ease;
  flex-shrink: 0;
  
  &:hover {
    background: rgba(0, 0, 0, 0.08);
    color: var(--color-primary-text);
    transform: scale(1.1);
  }
  
  .rotated {
    transform: rotate(90deg);
  }
}

.tree-node__spacer {
  width: 22px;
  flex-shrink: 0;
}

.tree-node__icon {
  display: flex;
  align-items: center;
  color: var(--color-secondary-text);
  flex-shrink: 0;
  transition: color 0.2s ease;
}

.tree-node__icon-img {
  width: 18px;
  height: 18px;
  object-fit: contain;
  flex-shrink: 0;
}

.tree-node__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-primary-text);
  font-size: 0.9rem;
  line-height: 1.4;
  transition: color 0.2s ease, font-weight 0.2s ease;
}

.tree-node__children {
  animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  padding-left: 0.5rem;
  margin-left: 0.5rem;
  position: relative;

  // Декоративная линия вместо border
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
    background: linear-gradient(180deg, 
      transparent 0%,
      rgba(var(--bs-info-rgb), 0.15) 20%,
      rgba(var(--bs-info-rgb), 0.15) 80%,
      transparent 100%);
    border-radius: 2px;
  }
}

.tree-node__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem 0.5rem;
  color: var(--color-secondary-text);
  opacity: 0.7;
}

.tree-node__delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
  color: var(--bs-danger);
  opacity: 0;
  transition: all 0.2s ease;
  flex-shrink: 0;
  margin-left: auto;
  margin-right: 0.5rem;
  
  &:hover {
    background: rgba(var(--bs-danger-rgb), 0.1);
    opacity: 1;
    transform: scale(1.1);
  }
  
  &:active {
    transform: scale(0.95);
  }
}

.tree-node__content:hover .tree-node__delete-btn {
  opacity: 0.7;
}

.tree-node__content--drop-target {
  background: rgba(var(--bs-info-rgb), 0.12);
  border: 2px dashed rgba(var(--bs-info-rgb), 0.5);
  border-radius: 8px;
}

.tree-node__content--uploading {
  pointer-events: none;
  opacity: 0.9;
}

.tree-node__add-file-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border: 1px solid rgba(var(--bs-info-rgb), 0.5);
  border-radius: 6px;
  background: rgba(var(--bs-info-rgb), 0.08);
  color: var(--color-primary-text);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.tree-node__add-file-btn:hover {
  background: rgba(var(--bs-info-rgb), 0.15);
  border-color: rgba(var(--bs-info-rgb), 0.7);
}

.tree-node__add-file-label {
  white-space: nowrap;
}

.tree-node__upload-spinner {
  display: flex;
  align-items: center;
  margin-left: 0.5rem;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    max-height: 1000px;
    transform: translateY(0);
  }
}
</style>
