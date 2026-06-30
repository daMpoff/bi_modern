<template>
  <ModalCenter
    modal-id="dashboardBlockSelectorModal"
    standalone
    :visible="show"
    title="Настройки селектора"
    :dialog-style="{ minWidth: '400px', maxWidth: '90vw' }"
    :z-index="1050"
    @close="handleClose"
  >
    <div class="mb-3">
      <label class="form-label">Пайплайн</label>
      <select
        v-model="form.pipelineId"
        class="form-select"
        @change="onPipelineChange"
      >
        <option :value="null">Выберите пайплайн</option>
        <option
          v-for="p in pipelines"
          :key="p.id"
          :value="p.id"
        >
          {{ p.name || `Пайплайн ${p.id}` }}
        </option>
      </select>
    </div>
    <div class="mb-3">
      <label class="form-label">Поле (источник вариантов)</label>
      <select
        v-model="form.fieldName"
        class="form-select"
        :disabled="!form.pipelineId || fieldsLoading"
      >
        <option value="">Выберите поле</option>
        <option
          v-for="f in fields"
          :key="f.name"
          :value="f.name"
        >
          {{ f.name }} ({{ f.type || 'auto' }})
        </option>
      </select>
      <span v-if="fieldsLoading" class="text-muted small">Загрузка...</span>
    </div>
    <div class="mb-3">
      <label class="form-label">Имя параметра</label>
      <input
        v-model="form.paramName"
        type="text"
        class="form-control"
        placeholder="например, min_glucose"
      />
      <small class="form-text text-muted">Указывайте имя без знака $, в фильтрах используйте $имя_параметра</small>
    </div>
    <div class="mb-3">
      <label class="form-label">Подпись (необязательно)</label>
      <input
        v-model="form.label"
        type="text"
        class="form-control"
        placeholder="например, Глюкоза"
      />
    </div>

    <template #footer>
      <button type="button" class="btn btn-secondary" @click="handleClose">
        Отмена
      </button>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="!form.pipelineId || !form.fieldName || !form.paramName"
        @click="handleSave"
      >
        Применить
      </button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, watch } from 'vue'
import ModalCenter from '@/components/ModalCenter.vue'
import { fetchPipelines, fetchPipelineFields } from '@/modules/bi_analysis_modern/client/src/Pipelines/js/pipelineApi.js'

const props = defineProps({
  show: { type: Boolean, default: false },
  block: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save'])

const pipelines = ref([])
const fields = ref([])
const fieldsLoading = ref(false)

const form = ref({
  pipelineId: null,
  fieldName: '',
  paramName: '',
  label: ''
})

watch(
  () => [props.show, props.block],
  async () => {
    if (!props.show) return
    form.value = {
      pipelineId: props.block?.config?.pipelineId ?? null,
      fieldName: props.block?.config?.fieldName ?? '',
      paramName: (props.block?.config?.paramName || '').replace(/^\$/u, '') || props.block?.config?.fieldName || '',
      label: props.block?.config?.label ?? ''
    }
    pipelines.value = await fetchPipelines()
    if (form.value.pipelineId) await loadFields(form.value.pipelineId)
    else fields.value = []
  },
  { immediate: true }
)

async function loadFields(pipelineId) {
  if (!pipelineId) {
    fields.value = []
    return
  }
  fieldsLoading.value = true
  try {
    const { fields: list } = await fetchPipelineFields(pipelineId, {})
    fields.value = list || []
  } catch {
    fields.value = []
  } finally {
    fieldsLoading.value = false
  }
}

async function onPipelineChange() {
  form.value.fieldName = ''
  form.value.paramName = ''
  await loadFields(form.value.pipelineId)
}

function handleClose() {
  emit('close')
}

function handleSave() {
  let cleanName = (form.value.paramName || '').trim()
  if (cleanName.startsWith('$')) cleanName = cleanName.slice(1)
  if (!cleanName) cleanName = form.value.fieldName

  const config = {
    ...(props.block?.config || {}),
    pipelineId: form.value.pipelineId,
    fieldName: form.value.fieldName,
    paramName: cleanName,
    label: (form.value.label || '').trim() || undefined
  }
  emit('save', { ...props.block, config })
  emit('close')
}
</script>

<style scoped lang="scss">
.form-text {
  display: block;
  margin-top: 0.25rem;
}
</style>
