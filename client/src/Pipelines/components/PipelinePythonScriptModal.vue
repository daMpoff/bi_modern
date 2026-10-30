<template>
  <ModalCenter
    modal-id="pipelinePythonScriptModal"
    standalone
    :visible="show"
    :dialog-style="{ maxWidth: '720px' }"
    :z-index="10050"
    body-class="p-0"
    @close="$emit('close')"
  >
    <template #title>
      <div class="pm-header-icon" style="background: rgba(99, 102, 241, 0.12); color: #6366f1">
        <Code :size="20" />
      </div>
      <span>Python Script</span>
    </template>

    <div class="pm-body">
      <div class="pm-section">
        <span class="pm-section-title">Название скрипта</span>
        <input v-model="scriptName" type="text" class="pm-input" placeholder="Мой скрипт" />
      </div>

      <div v-if="availableFields.length > 0" class="pm-section">
        <span class="pm-section-title">Входные поля</span>
        <div class="pm-chip-group">
          <span v-for="f in availableFields" :key="f.name" class="pm-chip" @click="insertFieldRef(f.name)">
            {{ f.name }}
            <span style="font-size: 11px; opacity: 0.5; margin-left: 2px">{{ f.type }}</span>
          </span>
        </div>
      </div>

      <div class="pm-section">
        <span class="pm-section-title">Код</span>
        <textarea
          ref="codeRef"
          v-model="code"
          class="pm-input code-textarea"
          placeholder="# df — входной Polars DataFrame&#10;# rows — строки данных&#10;&#10;result = df"
          rows="10"
        ></textarea>
        <p class="code-hint">
          Переменная <code>df</code> содержит входные данные (Polars DataFrame).
          Результат запишите в переменную <code>result</code>.
        </p>
      </div>

      <div class="pm-divider"></div>

      <div class="pm-section">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem">
          <span class="pm-section-title" style="margin: 0">Выходные поля (опционально)</span>
          <button class="pm-btn pm-btn--outline pm-btn--sm" @click="addOutputField">
            <Plus :size="14" />
            Добавить
          </button>
        </div>
        <p class="code-hint" style="margin-top: 0; margin-bottom: 0.75rem">
          Если скрипт меняет набор полей, укажите выходные поля. Иначе будут использованы входные.
        </p>
        <div v-for="(field, idx) in outputFields" :key="idx" class="pm-card" style="margin-bottom: 0.375rem">
          <div class="pm-row">
            <input v-model="field.name" type="text" class="pm-input" style="flex: 1" placeholder="Имя поля" />
            <select v-model="field.type" class="pm-select" style="width: 120px; flex-shrink: 0">
              <option value="string">Строка</option>
              <option value="number">Число</option>
              <option value="date">Дата</option>
              <option value="boolean">Логический</option>
            </select>
            <button class="pm-btn pm-btn--danger pm-btn--icon pm-btn--sm" @click="outputFields.splice(idx, 1)">
              <X :size="14" />
            </button>
          </div>
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
import { ref, watch } from 'vue'
import { Code, Plus, X } from 'lucide-vue-next'
import ModalCenter from '@/components/ModalCenter.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  initialConfig: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'apply'])

const scriptName = ref('')
const code = ref('')
const outputFields = ref([])
const codeRef = ref(null)

function insertFieldRef(fieldName) {
  const ref = `df['${fieldName}']`
  const textarea = codeRef.value
  if (!textarea) { code.value += ref; return }
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const before = code.value.substring(0, start)
  const after = code.value.substring(end)
  code.value = before + ref + after
  const cursorPos = start + ref.length
  setTimeout(() => { textarea.focus(); textarea.setSelectionRange(cursorPos, cursorPos) }, 0)
}

function addOutputField() {
  outputFields.value.push({ name: '', type: 'string' })
}

function handleApply() {
  emit('apply', {
    scriptName: scriptName.value.trim(),
    code: code.value,
    outputFields: outputFields.value.filter(f => f.name.trim())
  })
}

watch(() => props.show, (isOpen) => {
  if (!isOpen) return
  const config = props.initialConfig
  scriptName.value = config?.scriptName || ''
  code.value = config?.code || ''
  outputFields.value = (config?.outputFields || []).map(f => ({ ...f }))
})
</script>

<style scoped lang="scss">
@import '../scss/pipeline-modals.scss';

.code-textarea {
  resize: vertical;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  min-height: 160px;
  tab-size: 4;
}

.code-hint {
  font-size: 12px;
  color: var(--color-secondary-text);
  margin: 0.5rem 0 0;

  code {
    background: rgba(0, 0, 0, 0.06);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 12px;
  }
}
</style>
