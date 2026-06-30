<template>
  <ModalCenter
    modal-id="pipelineFormulaModal"
    standalone
    :visible="show"
    :dialog-style="{ maxWidth: '600px' }"
    :z-index="10050"
    :close-on-esc="false"
    body-class="p-0"
    @close="$emit('close')"
  >
    <template #title>
      <div class="pm-header-icon" style="background: rgba(139, 92, 246, 0.12); color: #8b5cf6">
        <SquareFunction :size="20" />
      </div>
      <span>Настройки формулы</span>
    </template>

    <div class="pm-body">
      <div class="pm-section">
          <span class="pm-section-title">Выходное поле</span>
          <div style="margin-bottom: 0.75rem">
            <label class="pm-label">Имя поля результата</label>
            <input v-model="outputField" type="text" class="pm-input" placeholder="new_column" />
          </div>
          <div>
            <label class="pm-label">Тип результата</label>
            <select v-model="outputType" class="pm-select">
              <option value="number">Число</option>
              <option value="string">Строка</option>
              <option value="date">Дата</option>
              <option value="boolean">Логический</option>
            </select>
          </div>
        </div>

        <div class="pm-divider"></div>

        <div class="pm-section">
          <span class="pm-section-title">Формула</span>
          <div v-if="availableFields.length > 0" style="margin-bottom: 0.75rem">
            <label class="pm-label">Доступные поля (нажмите, чтобы вставить)</label>
            <div class="pm-chip-group">
              <button
                v-for="f in availableFields"
                :key="f.name"
                class="pm-chip"
                @click="insertField(f.name)"
              >
                {{ f.name }}
                <span style="font-size: 11px; opacity: 0.5; margin-left: 2px">{{ f.type }}</span>
              </button>
            </div>
          </div>
          <textarea
            ref="formulaRef"
            v-model="expression"
            class="pm-input formula-textarea"
            placeholder="Например: price * quantity"
            rows="4"
          ></textarea>
          <p class="formula-hint">
            Используйте имена полей и математические операторы: +, -, *, /, (, )
          </p>
        </div>
    </div>

    <template #footer>
      <button class="pm-btn pm-btn--secondary" @click="$emit('close')">Отмена</button>
      <button class="pm-btn pm-btn--primary" @click="handleApply">Применить</button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, watch } from 'vue'
import { SquareFunction } from 'lucide-vue-next'
import ModalCenter from '@/components/ModalCenter.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  initialConfig: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'apply'])

const outputField = ref('')
const outputType = ref('number')
const expression = ref('')
const formulaRef = ref(null)

function insertField(fieldName) {
  const textarea = formulaRef.value
  if (!textarea) {
    expression.value += fieldName
    return
  }
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const before = expression.value.substring(0, start)
  const after = expression.value.substring(end)
  expression.value = before + fieldName + after
  const cursorPos = start + fieldName.length
  setTimeout(() => {
    textarea.focus()
    textarea.setSelectionRange(cursorPos, cursorPos)
  }, 0)
}

function handleApply() {
  emit('apply', {
    outputField: outputField.value.trim(),
    outputType: outputType.value,
    expression: expression.value.trim()
  })
}

watch(() => props.show, (isOpen) => {
  if (!isOpen) return
  const config = props.initialConfig
  outputField.value = config?.outputField || ''
  outputType.value = config?.outputType || 'number'
  expression.value = config?.expression || ''
})
</script>

<style scoped lang="scss">
@import '../scss/pipeline-modals.scss';

.formula-textarea {
  resize: vertical;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  min-height: 80px;
}

.formula-hint {
  font-size: 12px;
  color: var(--color-secondary-text);
  margin: 0.5rem 0 0;
}
</style>
