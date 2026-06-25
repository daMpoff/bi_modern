import { ref, watch, unref } from 'vue'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'
import { isFileConnection } from './connectionType.js'

function normalizeFile(f) {
  return {
    ...f,
    id: f.id || f.file_id,
    file_id: f.id || f.file_id,
    file_upload_id: f.file_upload_id || null,
    name: f.name || f.original_filename,
    original_filename: f.original_filename || null,
    schema: null
  }
}

function normalizeTable(t) {
  return {
    ...t,
    id: `${t.schema || ''}.${t.name || t.table || ''}`,
    file_id: null,
    file_upload_id: null,
    name: t.name || t.table,
    original_filename: null
  }
}

export function useConnectionItems(connectionIdRef, connectionTypeRef) {
  const items = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function loadItems() {
    const connectionId = unref(connectionIdRef)
    const connectionType = unref(connectionTypeRef)
    if (!connectionId) {
      items.value = []
      error.value = null
      return
    }
    loading.value = true
    error.value = null
    try {
      if (isFileConnection(connectionType)) {
        const res = await apiClient.get(biEndpoints.bi.connectionFiles(connectionId))
        if (res.success && res.data) {
          items.value = (Array.isArray(res.data) ? res.data : []).map(normalizeFile)
        } else {
          items.value = []
        }
      } else {
        const res = await apiClient.get(biEndpoints.bi.connectionTables(connectionId))
        if (res.success && res.data) {
          items.value = (Array.isArray(res.data) ? res.data : []).map(normalizeTable)
        } else {
          items.value = []
        }
      }
    } catch (err) {
      logError('Ошибка загрузки элементов подключения:', err)
      error.value = err
      items.value = []
    } finally {
      loading.value = false
    }
  }

  watch(
    () => [unref(connectionIdRef), unref(connectionTypeRef)],
    () => loadItems(),
    { immediate: true }
  )

  return { items, loading, loadItems, error }
}
