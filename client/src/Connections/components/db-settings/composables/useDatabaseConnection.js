import { logError } from '@/js/utils/logError.js'
import { ref } from 'vue'
import { apiClient } from '@/js/api/manager'
import { biEndpoints as endpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'

export function useDatabaseConnection(dbType, defaultPort = 5432) {
  const form = ref(null)
  
  const host = ref('')
  const port = ref(defaultPort)
  const database = ref('')
  const username = ref('')
  const password = ref('')
  
  const message = ref('')
  const error = ref(false)
  const isChecked = ref(false)
  const loading = ref(false)

  async function checkConnection() {
    message.value = ''
    error.value = false
    isChecked.value = false
    loading.value = true

    const formEl = form.value
    if (!formEl?.checkValidity()) {
      formEl?.classList.add('was-validated')
      loading.value = false
      return
    }

    try {
      const requestPayload = {
        type: dbType,
        host: host.value,
        port: port.value,
        username: username.value,
        password: password.value,
      }

      // Добавляем database только если оно определено и не пустое
      if (database.value) {
        requestPayload.database = database.value
      }

      const response = await apiClient.post(endpoints.bi.CheckConnection, requestPayload)
      const data = response.data || {}

      formEl?.classList.add('was-validated')

      if (data.success === true) {
        message.value = data.message || 'Соединение успешно'
        error.value = false
      } else {
        const raw = data.message || 'Ошибка соединения'
        message.value = translateErrorMessage(String(raw).trim())
        error.value = true
      }
    } catch (err) {
      logError('Ошибка проверки подключения:', err)
      message.value = 'Не удалось выполнить запрос: ' + (err.message || 'Неизвестная ошибка')
      error.value = true
    }

    isChecked.value = true
    loading.value = false
  }

  function translateErrorMessage(raw) {
    const text = raw.toLowerCase()

    if (text.includes('getaddrinfo failed') || text.includes('name resolution')) {
      return 'Не удалось распознать имя хоста. Проверьте правильность адреса.'
    }

    if (text.includes('timed out') || text.includes('timeout expired')) {
      return 'Превышено время ожидания подключения. Сервер недоступен или указан неправильный порт.'
    }

    if (text.includes('connection refused')) {
      return 'Подключение отклонено. Убедитесь, что сервер работает и принимает подключения.'
    }

    if (text.includes('authentication failed') || text.includes('password authentication failed') || text.includes('access denied')) {
      return 'Ошибка авторизации. Проверьте имя пользователя и пароль.'
    }

    if (text.includes('database') && text.includes('does not exist')) {
      return 'Указанная база данных не найдена.'
    }

    if (text.includes('ssl') && text.includes('handshake')) {
      return 'Ошибка SSL-соединения. Возможно, сервер требует защищённое подключение.'
    }

    if (text.includes('utf-8') && text.includes('decode')) {
      return 'Сервер вернул сообщение с некорректной кодировкой. Проверьте параметры подключения.'
    }

    if (text.includes('could not translate host name')) {
      return 'Не удалось разрешить имя хоста. Убедитесь, что адрес указан правильно.'
    }

    // MSSQL-специфичные ошибки
    if (text.includes('adaptive server is unavailable')) {
      return 'Сервер MSSQL недоступен или указан неверный хост.'
    }

    if (text.includes('db-lib error message')) {
      return 'Не удалось подключиться: проверьте адрес сервера, порт и параметры авторизации.'
    }

    return raw || 'Ошибка соединения'
  }

  return {
    form,
    host,
    port,
    database,
    username,
    password,
    message,
    error,
    isChecked,
    loading,
    checkConnection,
    translateErrorMessage
  }
}