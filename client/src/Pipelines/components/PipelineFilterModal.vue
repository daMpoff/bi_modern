<template>
  <div v-if="show" class="pm-overlay" @click.self="$emit('close')">
    <div class="pm-modal pm-modal--md">
      <div class="pm-header">
        <div class="pm-header-icon" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b">
          <Filter :size="20" />
        </div>
        <h3 class="pm-header-title">Настройки фильтра</h3>
        <button class="pm-header-close" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>

      <div class="pm-body">
        <div class="pm-section">
          <div class="pm-row" style="justify-content: space-between; margin-bottom: 0.75rem">
            <span class="pm-section-title" style="margin: 0">Условия фильтрации</span>
            <button class="pm-btn pm-btn--outline pm-btn--sm" @click="addCondition">
              <Plus :size="14" />
              Добавить
            </button>
          </div>

          <div v-if="conditions.length === 0" class="pm-empty">
            <Filter :size="28" style="opacity: 0.4" />
            <span class="pm-empty-text">Нет условий фильтрации</span>
            <span class="pm-empty-hint">Добавьте условие для фильтрации данных</span>
          </div>

          <div v-for="(cond, idx) in conditions" :key="idx" class="pm-card">
            <div class="pm-row">
              <select
                v-if="availableFields.length > 0"
                v-model="cond.field"
                class="pm-select"
                style="flex: 1; min-width: 110px"
                @change="onFieldChange(cond)"
              >
                <option value="">-- Поле --</option>
                <option v-for="f in availableFields" :key="f.name" :value="f.name">{{ f.name }}</option>
              </select>
              <input
                v-else
                v-model="cond.field"
                type="text"
                class="pm-input"
                style="flex: 1; min-width: 110px"
                placeholder="Поле"
              />

              <select
                v-model="cond.operator"
                class="pm-select"
                style="width: 135px; flex-shrink: 0"
                @change="onOperatorChange(cond)"
              >
                <option
                  v-for="op in operatorsForCondition(cond)"
                  :key="op.value"
                  :value="op.value"
                >{{ op.label }}</option>
              </select>

              <template v-if="needsValue(cond.operator)">
                <template v-if="isBetween(cond.operator)">
                  <input
                    type="text"
                    :value="betweenMin(cond)"
                    class="pm-input"
                    style="flex: 1; min-width: 72px"
                    placeholder="Мин или $параметр"
                    @input="e => setBetweenMin(cond, e.target.value)"
                  />
                  <input
                    type="text"
                    :value="betweenMax(cond)"
                    class="pm-input"
                    style="flex: 1; min-width: 72px"
                    placeholder="Макс или $параметр"
                    @input="e => setBetweenMax(cond, e.target.value)"
                  />
                </template>
                <template v-else-if="valueInputType(cond) === 'boolean'">
                  <select v-model="cond.value" class="pm-select" style="flex: 1; min-width: 80px">
                    <option v-for="opt in BOOLEAN_OPTIONS" :key="String(opt.value)" :value="opt.value">{{ opt.label }}</option>
                  </select>
                </template>
                <input
                  v-else
                  v-model="cond.value"
                  type="text"
                  class="pm-input"
                  style="flex: 1; min-width: 90px"
                  :placeholder="valueInputType(cond) === 'date' ? 'ГГГГ-ММ-ДД или $параметр' : 'Значение или $параметр'"
                />
              </template>

              <button class="pm-btn pm-btn--danger pm-btn--icon pm-btn--sm" @click="removeCondition(idx)">
                <X :size="14" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="pm-footer">
        <button class="pm-btn pm-btn--secondary" @click="$emit('close')">Отмена</button>
        <button class="pm-btn pm-btn--primary" @click="handleApply">Применить</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Filter, Plus, X } from 'lucide-vue-next'
import {
  getOperatorsForFieldType,
  needsValue as needsValueFn,
  isBetweenOperator,
  getValueInputType as getValueInputTypeFn,
  BOOLEAN_OPTIONS
} from '@/modules/bi_analysis_modern/client/src/js/filterFieldTypes.js'

const props = defineProps({
  show: { type: Boolean, default: false },
  initialConfig: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'apply'])
const conditions = ref([])

function fieldTypeForCondition(cond) {
  if (cond.fieldType) return cond.fieldType
  const f = props.availableFields.find(af => af.name === cond.field)
  return f?.type || 'string'
}

function operatorsForCondition(cond) {
  return getOperatorsForFieldType(fieldTypeForCondition(cond))
}

function needsValue(operator) { return needsValueFn(operator) }
function isBetween(operator) { return isBetweenOperator(operator) }

function valueInputType(cond) {
  return getValueInputTypeFn(fieldTypeForCondition(cond), cond.operator)
}

function betweenInputType(cond) {
  const t = fieldTypeForCondition(cond)
  if (t === 'date') return 'date'
  if (t === 'number') return 'number'
  return 'text'
}

function ensureBetweenValue(cond) {
  if (typeof cond.value !== 'object' || cond.value === null) {
    cond.value = { min: cond.value ?? '', max: '' }
  }
  if (cond.value.min === undefined) cond.value.min = ''
  if (cond.value.max === undefined) cond.value.max = ''
}

function betweenMin(cond) { ensureBetweenValue(cond); return cond.value.min }
function betweenMax(cond) { ensureBetweenValue(cond); return cond.value.max }
function setBetweenMin(cond, val) { ensureBetweenValue(cond); cond.value = { ...cond.value, min: val } }
function setBetweenMax(cond, val) { ensureBetweenValue(cond); cond.value = { ...cond.value, max: val } }

function onFieldChange(cond) {
  const f = props.availableFields.find(af => af.name === cond.field)
  cond.fieldType = f?.type || 'string'
  if (!needsValue(cond.operator)) return
  if (isBetween(cond.operator)) ensureBetweenValue(cond)
  else if (cond.fieldType === 'boolean') cond.value = true
  else if (cond.fieldType === 'number') cond.value = null
  else cond.value = ''
}

function onOperatorChange(cond) {
  if (!needsValue(cond.operator)) { cond.value = ''; return }
  if (isBetween(cond.operator)) {
    const prev = cond.value
    cond.value = {
      min: typeof prev === 'object' && prev && 'min' in prev ? prev.min : (prev ?? ''),
      max: typeof prev === 'object' && prev && 'max' in prev ? prev.max : ''
    }
  } else if (cond.fieldType === 'boolean' && cond.value !== true && cond.value !== false) {
    cond.value = true
  } else if (typeof cond.value === 'object' && cond.value !== null) {
    cond.value = cond.value.min ?? ''
  }
}

function addCondition() {
  conditions.value.push({ field: '', fieldType: 'string', operator: '=', value: '' })
}

function removeCondition(idx) {
  conditions.value.splice(idx, 1)
}

function handleApply() {
  const serialized = conditions.value
    .filter(c => c.field)
    .map(c => {
      const value = isBetween(c.operator) && c.value && typeof c.value === 'object'
        ? { min: c.value.min, max: c.value.max }
        : c.value
      return { field: c.field, operator: c.operator, value }
    })
  emit('apply', { conditions: serialized })
}

watch(() => props.show, (isOpen) => {
  if (!isOpen) return
  const config = props.initialConfig
  if (config?.conditions && Array.isArray(config.conditions)) {
    conditions.value = config.conditions.map(c => {
      const field = c.field ?? ''
      const fieldType = c.fieldType || props.availableFields.find(af => af.name === field)?.type || 'string'
      let value = c.value
      if (isBetweenOperator(c.operator)) {
        value = typeof value === 'object' && value && 'min' in value && 'max' in value
          ? { ...value } : { min: value ?? '', max: '' }
      }
      return { field, fieldType, operator: c.operator ?? '=', value }
    })
  } else {
    conditions.value = []
  }
})
</script>

<style scoped lang="scss">
@import '../scss/pipeline-modals.scss';
</style>
