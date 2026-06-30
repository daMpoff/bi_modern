<template>
  <ModalCenter
    modal-id="dashboardBlockTextModal"
    standalone
    :visible="show"
    title="Редактор текста"
    :dialog-style="{ maxWidth: '720px', width: '92vw' }"
    :z-index="1050"
    @close="handleClose"
  >
    <div class="mb-3">
      <label class="form-label">Заголовок блока</label>
      <input
        v-model="form.title"
        type="text"
        class="form-control"
        placeholder="Необязательно"
      />
    </div>

    <div class="editor-toolbar">
      <div class="toolbar-group">
        <button
          v-for="btn in formattingButtons"
          :key="btn.cmd"
          type="button"
          class="toolbar-btn"
          :title="btn.title"
          @mousedown.prevent
          @click="execCommand(btn.cmd, btn.value)"
        >
          <component :is="btn.icon" :size="16" />
        </button>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <button
          v-for="btn in headingButtons"
          :key="btn.cmd + btn.value"
          type="button"
          class="toolbar-btn toolbar-btn-text"
          :title="btn.title"
          @mousedown.prevent
          @click="execCommand(btn.cmd, btn.value)"
        >
          {{ btn.label }}
        </button>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <button
          v-for="btn in alignButtons"
          :key="btn.cmd"
          type="button"
          class="toolbar-btn"
          :title="btn.title"
          @mousedown.prevent
          @click="execCommand(btn.cmd)"
        >
          <component :is="btn.icon" :size="16" />
        </button>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <button
          v-for="btn in listButtons"
          :key="btn.cmd"
          type="button"
          class="toolbar-btn"
          :title="btn.title"
          @mousedown.prevent
          @click="execCommand(btn.cmd)"
        >
          <component :is="btn.icon" :size="16" />
        </button>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <label class="toolbar-btn toolbar-btn-color" title="Цвет текста">
          <Type :size="16" />
          <input
            type="color"
            class="color-input"
            :value="currentColor"
            @input="handleColorChange"
          />
          <span class="color-indicator" :style="{ backgroundColor: currentColor }" />
        </label>
        <button
          type="button"
          class="toolbar-btn"
          title="Очистить форматирование"
          @mousedown.prevent
          @click="execCommand('removeFormat')"
        >
          <RemoveFormatting :size="16" />
        </button>
      </div>

      <div class="toolbar-divider" />

      <div class="toolbar-group">
        <select
          class="toolbar-select"
          :value="form.fontSize"
          @change="handleFontSizeChange"
        >
          <option v-for="s in fontSizes" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>
    </div>

    <div
      ref="editorRef"
      class="editor-area"
      contenteditable="true"
      @input="handleEditorInput"
      @paste="handlePaste"
    />

    <template #footer>
      <button type="button" class="btn btn-secondary" @click="handleClose">
        Отмена
      </button>
      <button type="button" class="btn btn-primary" @click="handleSave">
        Сохранить
      </button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import {
  Bold, Italic, Underline, Strikethrough,
  AlignLeft, AlignCenter, AlignRight,
  List, ListOrdered,
  Type, RemoveFormatting
} from 'lucide-vue-next'
import ModalCenter from '@/components/ModalCenter.vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  block: { type: Object, default: null }
})

const emit = defineEmits(['close', 'save'])

const editorRef = ref(null)
const currentColor = ref('#000000')

const form = ref({
  title: '',
  content: '',
  textAlign: 'left',
  fontSize: '14px',
  padding: '16px'
})

const fontSizes = ['12px', '13px', '14px', '15px', '16px', '18px', '20px', '24px']

const formattingButtons = [
  { cmd: 'bold', title: 'Жирный (Ctrl+B)', icon: Bold },
  { cmd: 'italic', title: 'Курсив (Ctrl+I)', icon: Italic },
  { cmd: 'underline', title: 'Подчёркнутый (Ctrl+U)', icon: Underline },
  { cmd: 'strikeThrough', title: 'Зачёркнутый', icon: Strikethrough }
]

const headingButtons = [
  { cmd: 'formatBlock', value: 'h1', title: 'Заголовок 1', label: 'H1' },
  { cmd: 'formatBlock', value: 'h2', title: 'Заголовок 2', label: 'H2' },
  { cmd: 'formatBlock', value: 'h3', title: 'Заголовок 3', label: 'H3' },
  { cmd: 'formatBlock', value: 'p', title: 'Параграф', label: 'P' }
]

const alignButtons = [
  { cmd: 'justifyLeft', title: 'По левому краю', icon: AlignLeft },
  { cmd: 'justifyCenter', title: 'По центру', icon: AlignCenter },
  { cmd: 'justifyRight', title: 'По правому краю', icon: AlignRight }
]

const listButtons = [
  { cmd: 'insertUnorderedList', title: 'Маркированный список', icon: List },
  { cmd: 'insertOrderedList', title: 'Нумерованный список', icon: ListOrdered }
]

watch(
  () => [props.show, props.block],
  () => {
    if (!props.show) return
    const cfg = props.block?.config || {}
    form.value = {
      title: cfg.title || '',
      content: cfg.content || '',
      textAlign: cfg.textAlign || 'left',
      fontSize: cfg.fontSize || '14px',
      padding: cfg.padding || '16px'
    }
    nextTick(() => {
      if (editorRef.value) {
        editorRef.value.innerHTML = form.value.content
        editorRef.value.style.fontSize = form.value.fontSize
      }
    })
  },
  { immediate: true }
)

function execCommand(cmd, value) {
  if (!editorRef.value) return
  editorRef.value.focus()
  if (cmd === 'formatBlock' && value) {
    document.execCommand(cmd, false, `<${value}>`)
  } else {
    document.execCommand(cmd, false, value || null)
  }
}

function handleColorChange(e) {
  currentColor.value = e.target.value
  editorRef.value?.focus()
  document.execCommand('foreColor', false, e.target.value)
}

function handleFontSizeChange(e) {
  form.value.fontSize = e.target.value
  if (editorRef.value) {
    editorRef.value.style.fontSize = e.target.value
  }
}

function handleEditorInput() {
  if (editorRef.value) {
    form.value.content = editorRef.value.innerHTML
  }
}

function handlePaste(e) {
  e.preventDefault()
  const html = e.clipboardData?.getData('text/html')
  const text = e.clipboardData?.getData('text/plain') || ''

  if (html) {
    const cleaned = html
      .replace(/<meta[^>]*>/gi, '')
      .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
      .replace(/\s+class="[^"]*"/gi, '')
      .replace(/\s+style="[^"]*"/gi, '')
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    document.execCommand('insertHTML', false, cleaned)
  } else {
    document.execCommand('insertText', false, text)
  }
}

function handleClose() {
  emit('close')
}

function handleSave() {
  const content = editorRef.value ? editorRef.value.innerHTML : form.value.content
  const config = {
    ...(props.block?.config || {}),
    title: (form.value.title || '').trim() || undefined,
    content: content || '',
    textAlign: form.value.textAlign,
    fontSize: form.value.fontSize,
    padding: form.value.padding
  }
  emit('save', { ...props.block, config })
  emit('close')
}
</script>

<style scoped lang="scss">
.editor-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  background: var(--bs-light, #f8f9fa);
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--bs-border-color, #dee2e6);
  margin: 0 4px;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--bs-body-color, #212529);
  transition: background 0.15s;

  &:hover {
    background: rgba(0, 0, 0, 0.08);
  }

  &:active {
    background: rgba(0, 0, 0, 0.12);
  }
}

.toolbar-btn-text {
  width: auto;
  padding: 0 8px;
  font-size: 0.8rem;
  font-weight: 600;
}

.toolbar-btn-color {
  position: relative;
  cursor: pointer;
}

.color-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.color-indicator {
  position: absolute;
  bottom: 3px;
  left: 50%;
  transform: translateX(-50%);
  width: 14px;
  height: 3px;
  border-radius: 1px;
}

.toolbar-select {
  height: 28px;
  font-size: 0.8rem;
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 4px;
  background: #fff;
  padding: 0 6px;
  cursor: pointer;
}

.editor-area {
  min-height: 280px;
  max-height: 50vh;
  overflow-y: auto;
  padding: 16px;
  border: 1px solid var(--bs-border-color, #dee2e6);
  border-radius: 0 0 6px 6px;
  outline: none;
  line-height: 1.6;
  font-size: 14px;
  background: #fff;
  word-break: break-word;

  &:focus {
    border-color: var(--bs-primary, #0d6efd);
    box-shadow: 0 0 0 2px rgba(var(--bs-primary-rgb, 13, 110, 253), 0.15);
  }

  &:empty::before {
    content: 'Начните вводить текст...';
    color: var(--bs-secondary, #6c757d);
    opacity: 0.6;
    pointer-events: none;
  }
}
</style>
