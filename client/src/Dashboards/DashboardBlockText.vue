<template>
  <div
    class="dashboard-block-text"
    :style="containerStyle"
  >
    <div
      v-if="hasContent"
      class="text-content"
      v-html="sanitizedContent"
    />
    <div v-else class="text-empty">
      <Type :size="24" class="text-empty-icon" />
      <span>Нажмите для редактирования</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Type } from 'lucide-vue-next'

const props = defineProps({
  block: { type: Object, required: true }
})

const config = computed(() => props.block?.config || {})

const hasContent = computed(() => {
  const c = config.value.content
  if (!c) return false
  // Strip tags to check if there's actual text
  const text = c.replace(/<[^>]*>/g, '').trim()
  return text.length > 0
})

const containerStyle = computed(() => {
  const s = {}
  if (config.value.textAlign) s.textAlign = config.value.textAlign
  if (config.value.fontSize) s.fontSize = config.value.fontSize
  if (config.value.padding) s.padding = config.value.padding
  return s
})

// XSS sanitization — strip dangerous tags and attributes
function sanitizeHtml(html) {
  if (!html) return ''
  return html
    // Remove script tags and their content
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    // Remove style tags and their content
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    // Remove event handler attributes
    .replace(/\s+on\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    // Remove javascript: URLs
    .replace(/\bhref\s*=\s*(?:"javascript:[^"]*"|'javascript:[^']*')/gi, '')
    .replace(/\bsrc\s*=\s*(?:"javascript:[^"]*"|'javascript:[^']*')/gi, '')
    // Remove iframe, object, embed, form, input
    .replace(/<\/?(?:iframe|object|embed|form|input|textarea|button)\b[^>]*>/gi, '')
}

const sanitizedContent = computed(() => sanitizeHtml(config.value.content || ''))
</script>

<style scoped lang="scss">
.dashboard-block-text {
  width: 100%;
  height: 100%;
  overflow: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.text-content {
  flex: 1;
  line-height: 1.6;
  word-break: break-word;

  :deep(h1) { font-size: 1.75rem; font-weight: 700; margin: 0 0 0.5em; }
  :deep(h2) { font-size: 1.4rem; font-weight: 600; margin: 0 0 0.4em; }
  :deep(h3) { font-size: 1.15rem; font-weight: 600; margin: 0 0 0.3em; }
  :deep(p) { margin: 0 0 0.5em; }
  :deep(ul), :deep(ol) { margin: 0 0 0.5em; padding-left: 1.5em; }
  :deep(a) { color: var(--bs-primary, #0d6efd); text-decoration: underline; }
  :deep(blockquote) {
    border-left: 3px solid var(--bs-border-color, #dee2e6);
    padding-left: 1em;
    margin: 0 0 0.5em;
    color: var(--bs-secondary, #6c757d);
  }
  :deep(hr) { border: none; border-top: 1px solid var(--bs-border-color, #dee2e6); margin: 0.75em 0; }
  :deep(img) { max-width: 100%; height: auto; border-radius: 4px; }
}

.text-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--bs-secondary, #6c757d);
  font-size: 0.9rem;
  opacity: 0.6;
}

.text-empty-icon {
  opacity: 0.4;
}
</style>
