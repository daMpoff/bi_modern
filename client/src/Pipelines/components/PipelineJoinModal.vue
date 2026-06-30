<template>
  <ModalCenter
    modal-id="pipelineJoinModal"
    standalone
    :visible="show"
    :dialog-style="{ maxWidth: '480px' }"
    :z-index="10050"
    body-class="p-0"
    @close="$emit('close')"
  >
    <template #title>
      <div class="pm-header-icon" style="background: rgba(236, 72, 153, 0.12); color: #ec4899">
        <GitMerge :size="20" />
      </div>
      <span>Настройки соединения</span>
    </template>

    <div class="pm-body">
      <div class="pm-section">
        <span class="pm-section-title">Тип связи</span>
        <div class="pm-chip-group">
          <button
            v-for="jt in joinTypes"
            :key="jt.value"
            class="pm-chip"
            :class="{ 'pm-chip--active': joinType === jt.value }"
            @click="joinType = jt.value"
          >
            <component :is="jt.icon" style="width: 28px; height: 14px" />
            <span>{{ jt.label }}</span>
          </button>
        </div>
      </div>

      <div v-if="suggestions.length > 0" class="pm-section">
        <span class="pm-section-title">Совпадающие поля</span>
        <div class="pm-chip-group">
          <button
            v-for="(s, idx) in suggestions"
            :key="idx"
            class="pm-chip"
            :class="{ 'pm-chip--active': leftKey === s.leftKey && rightKey === s.rightKey }"
            @click="applySuggestion(s)"
          >
            <span>{{ s.leftKey }}</span>
            <Link2 :size="12" style="opacity: 0.5" />
            <span>{{ s.rightKey }}</span>
          </button>
        </div>
      </div>

      <div class="pm-section">
        <div class="pm-section-row">
          <span class="pm-section-title">Ключевые поля</span>
          <button
            type="button"
            class="pm-btn pm-btn--secondary pm-btn--sm"
            :disabled="!canSuggest || suggestionsLoading"
            @click="pickSuggestedKeys"
          >
            <span v-if="suggestionsLoading" class="spinner-border spinner-border-sm" role="status"></span>
            <Link2 v-else :size="14" />
            Подобрать ключи
          </button>
        </div>
        <div style="display: flex; gap: 0.75rem; align-items: flex-end">
          <div style="flex: 1">
            <label class="pm-label">Левая таблица</label>
            <select v-if="leftColumns.length > 0" v-model="leftKey" class="pm-select">
              <option value="">-- выберите --</option>
              <option v-for="col in leftColumns" :key="col" :value="col">{{ col }}</option>
            </select>
            <input v-else v-model="leftKey" type="text" class="pm-input" placeholder="id" />
          </div>
          <div style="padding-bottom: 0.5rem; color: var(--color-secondary-text)">
            <ArrowRight :size="16" />
          </div>
          <div style="flex: 1">
            <label class="pm-label">Правая таблица</label>
            <select v-if="rightColumns.length > 0" v-model="rightKey" class="pm-select">
              <option value="">-- выберите --</option>
              <option v-for="col in rightColumns" :key="col" :value="col">{{ col }}</option>
            </select>
            <input v-else v-model="rightKey" type="text" class="pm-input" placeholder="user_id" />
          </div>
        </div>
        <div v-if="suggestionsLoading && !suggestionsLoadedOnce" style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem; font-size: 13px; color: var(--color-secondary-text)">
          <span class="spinner-border spinner-border-sm" role="status"></span>
          Загрузка полей...
        </div>
      </div>
    </div>

    <template #footer>
      <button class="pm-btn pm-btn--secondary" @click="$emit('close')">Отмена</button>
      <button class="pm-btn pm-btn--primary" @click="handleApply">Применить</button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { GitMerge, ArrowRight, Link2 } from 'lucide-vue-next'
import { useToast } from '@/js/utils/toast.js'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'
import ModalCenter from '@/components/ModalCenter.vue'
import JoinInnerIcon from '@/modules/bi_analysis_modern/client/src/components/icons/JoinInnerIcon.vue'
import JoinLeftIcon from '@/modules/bi_analysis_modern/client/src/components/icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/modules/bi_analysis_modern/client/src/components/icons/JoinRightIcon.vue'
import JoinFullIcon from '@/modules/bi_analysis_modern/client/src/components/icons/JoinFullIcon.vue'

const toast = useToast()

const props = defineProps({
  show: { type: Boolean, default: false },
  initialConfig: { type: Object, default: null },
  leftSource: { type: Object, default: null },
  rightSource: { type: Object, default: null }
})

const emit = defineEmits(['close', 'apply'])

const joinTypes = [
  { value: 'INNER JOIN', label: 'INNER', icon: JoinInnerIcon },
  { value: 'LEFT JOIN', label: 'LEFT', icon: JoinLeftIcon },
  { value: 'RIGHT JOIN', label: 'RIGHT', icon: JoinRightIcon },
  { value: 'FULL JOIN', label: 'FULL', icon: JoinFullIcon }
]

const joinType = ref('LEFT JOIN')
const leftKey = ref('')
const rightKey = ref('')
const suggestions = ref([])
const leftColumns = ref([])
const rightColumns = ref([])
const suggestionsLoading = ref(false)
const suggestionsLoadedOnce = ref(false)

const canSuggest = computed(() => !!props.leftSource?.config && !!props.rightSource?.config)

async function fetchSuggestions() {
  if (!props.leftSource?.config || !props.rightSource?.config) {
    suggestions.value = []; leftColumns.value = []; rightColumns.value = []; return
  }
  suggestionsLoading.value = true
  try {
    const { data } = await apiClient.post(biEndpoints.bi.suggestJoinKeys, {
      leftSource: props.leftSource,
      rightSource: props.rightSource
    })
    suggestions.value = data?.suggestions || []
    leftColumns.value = data?.leftColumns || []
    rightColumns.value = data?.rightColumns || []
    suggestionsLoadedOnce.value = true
    if (suggestions.value.length > 0 && !props.initialConfig?.leftKey) {
      applySuggestion(suggestions.value[0])
    }
  } catch {
    suggestions.value = []
    leftColumns.value = []
    rightColumns.value = []
  } finally {
    suggestionsLoading.value = false
  }
}

async function pickSuggestedKeys() {
  if (!canSuggest.value) return
  await fetchSuggestions()
  if (suggestions.value.length > 0) {
    applySuggestion(suggestions.value[0])
    toast.success('Ключи подобраны по совпадающим полям')
  } else {
    toast.info('Совпадающих полей не найдено. Выберите ключи вручную.')
  }
}

function applySuggestion(s) { leftKey.value = s.leftKey; rightKey.value = s.rightKey }

function handleApply() {
  emit('apply', {
    joinType: joinType.value,
    leftKey: (leftKey.value || '').trim(),
    rightKey: (rightKey.value || '').trim()
  })
}

watch(() => props.show, (isOpen) => {
  if (!isOpen) return
  joinType.value = props.initialConfig?.joinType || 'LEFT JOIN'
  leftKey.value = props.initialConfig?.leftKey || ''
  rightKey.value = props.initialConfig?.rightKey || ''
  suggestionsLoadedOnce.value = false
  fetchSuggestions()
})

watch([() => props.leftSource, () => props.rightSource], () => {
  if (props.show) fetchSuggestions()
}, { deep: true })
</script>

<style scoped lang="scss">
@import '../scss/pipeline-modals.scss';

.pm-section-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;

  .pm-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
  }
}
</style>
