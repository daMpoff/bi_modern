<template>
  <div v-if="file" class="file-preview-panel">
    <UnifiedTablePreview 
      v-if="isSupportedFile(file)" 
      :file="file" 
      :isLoading="isLoading" 
      :key="`preview-${file.id || file.temp_path || file.name}`" 
    />

    <div v-else class="text-muted p-4">Формат файла не поддерживается для предпросмотра.</div>
  </div>
</template>

<script setup>
import UnifiedTablePreview from './FilePreview/UnifiedTablePreview.vue'

defineProps({
  file: Object,
  isLoading: Boolean
})

function isSupportedFile(file) {
  if (!file) return false
  
  const supportedTypes = ['csv', 'xlsx', 'xls', 'txt']
  const supportedExtensions = ['.csv', '.xlsx', '.xls', '.txt']
  
  // Проверяем расширение
  if (file.name) {
    const ext = file.name.toLowerCase()
    if (supportedExtensions.some(supported => ext.endsWith(supported))) {
      return true
    }
  }
  
  // Проверяем file_type
  if (file.file_type) {
    const type = file.file_type.toLowerCase()
    if (supportedTypes.includes(type)) {
      return true
    }
  }
  
  return false
}
</script>
  
<style scoped>
.file-preview-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
  