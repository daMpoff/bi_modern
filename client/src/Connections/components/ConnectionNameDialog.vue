<template>
  <ModalCenter
    modal-id="connectionNameDialog"
    standalone
    :visible="visible"
    title="Название подключения"
    :dialog-style="{ maxWidth: '480px' }"
    :close-on-backdrop="false"
    :close-on-esc="false"
    @close="cancel"
  >
    <input v-model="localName" class="form-control" placeholder="Введите название" />
    <div v-if="error" class="text-danger mt-2">{{ error }}</div>

    <template #footer>
      <button class="btn btn-secondary" @click="cancel">Отмена</button>
      <button class="btn btn-primary" @click="submit" :disabled="!localName || loading">
        Сохранить
      </button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apiClient } from '@/js/api/manager'
import { endpoints } from '@/js/api/endpoints'
import ModalCenter from '@/components/ModalCenter.vue'

const props = defineProps({
  visible: Boolean,
  modelValue: String,
  connectorType: String,
  connectionConfig: Object,
  connectionFiles: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:visible', 'saved'])

const localName = ref(props.modelValue || '')
const error = ref('')
const loading = ref(false)

watch(() => props.modelValue, (newVal) => {
  localName.value = newVal || ''
})

function extractErrorMessage(err) {
  if (err.response && err.response.data) {
    const data = err.response.data
    if (typeof data === 'object') {
      return Object.values(data).flat().join(', ') || 'Неизвестная ошибка'
    }
    return String(data)
  }
  return err.message || 'Неизвестная ошибка'
}

async function submit() {
  if (!localName.value || loading.value) return

  error.value = ''
  loading.value = true

  try {
    const isFileConnection = props.connectorType === undefined

    const payload = {
      name: localName.value,
      connector_type: isFileConnection ? 'file' : props.connectorType,
      config: isFileConnection ? { source: 'local_upload' } : (props.connectionConfig || {})
    }

    // Создаем подключение через API
    const response = await apiClient.post(endpoints.bi.ConnectionsList, payload)
    const data = response?.data
    if (data && data.id) {
      emit('saved', data)
      emit('update:visible', false)
    } else {
      error.value = 'Не удалось сохранить подключение'
    }

  } catch (err) {
    logError('Ошибка при сохранении подключения:', err.response?.data || err)
    error.value = extractErrorMessage(err)
  } finally {
    loading.value = false
  }
}

function cancel() {
  emit('update:visible', false)
}
</script>

<style scoped>
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>