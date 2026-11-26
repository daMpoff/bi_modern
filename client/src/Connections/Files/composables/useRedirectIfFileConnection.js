import { logError } from '@/js/utils/logError.js'
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiClient } from '@/js/api/manager'
import { biEndpoints as endpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'

export function useRedirectIfFileConnection() {
  const router = useRouter()
  const route = useRoute()

  onMounted(async () => {
    const connectionId = route.params.id || route.params.pk
    if (!connectionId) return

    const res = await apiClient.get(`${endpoints.bi.ConnectionsList}${connectionId}/`)
    if (res.success) {
      const type = (res.data.connector_type_display || res.data.connector_type || '').toLowerCase().trim()

      const isFileConnection = type === 'file' ||
                               type === 'files' ||
                               type === 'файл' ||
                               type === 'файлы' ||
                               type.includes('file') ||
                               type.includes('файл')

      if (isFileConnection) {
        router.replace(`/bi-modern/connections/${connectionId}/files/`)
      }
    } else {
      logError('Ошибка загрузки подключения:', res.errors || res)
    }
  })
}
