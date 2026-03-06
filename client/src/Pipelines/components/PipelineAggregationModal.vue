<template>
  <div v-if="show" class="pm-overlay" @click.self="$emit('close')">
    <div class="pm-modal pm-modal--md">
      <div class="pm-header">
        <div class="pm-header-icon" style="background: rgba(16, 185, 129, 0.12); color: #10b981">
          <BarChart3 :size="20" />
        </div>
        <h3 class="pm-header-title">Настройки агрегации</h3>
        <button class="pm-header-close" @click="$emit('close')">
          <X :size="16" />
        </button>
      </div>

      <div class="pm-body">
        <div class="pm-section">
          <div class="pm-row" style="justify-content: space-between; margin-bottom: 0.75rem">
            <span class="pm-section-title" style="margin: 0">Группировка (GROUP BY)</span>
            <button class="pm-btn pm-btn--outline pm-btn--sm" @click="addGroupField">
              <Plus :size="14" />
              Добавить
            </button>
          </div>

          <div v-if="groupBy.length === 0" class="pm-empty">
            <BarChart3 :size="28" style="opacity: 0.4" />
            <span class="pm-empty-text">Нет полей группировки</span>
            <span class="pm-empty-hint">Добавьте поле для группировки данных</span>
          </div>

          <div v-for="(field, idx) in groupBy" :key="'g' + idx" class="pm-card">
            <div class="pm-row">
              <select
                v-if="availableFields.length > 0"
                v-model="groupBy[idx]"
                class="pm-select"
                style="flex: 1"
              >
                <option value="">-- Поле --</option>
                <option v-for="f in availableFields" :key="f.name" :value="f.name">{{ f.name }}</option>
              </select>
              <input v-else v-model="groupBy[idx]" type="text" class="pm-input" style="flex: 1" placeholder="Имя поля" />
              <button class="pm-btn pm-btn--danger pm-btn--icon pm-btn--sm" @click="removeGroupField(idx)">
                <X :size="14" />
              </button>
            </div>
          </div>
        </div>

        <div class="pm-divider"></div>

        <div class="pm-section">
          <div class="pm-row" style="justify-content: space-between; margin-bottom: 0.75rem">
            <span class="pm-section-title" style="margin: 0">Агрегации</span>
            <button class="pm-btn pm-btn--outline pm-btn--sm" @click="addAggregation">
              <Plus :size="14" />
              Добавить
            </button>
          </div>

          <div v-if="aggregations.length === 0" class="pm-empty">
            <BarChart3 :size="28" style="opacity: 0.4" />
            <span class="pm-empty-text">Нет агрегаций</span>
            <span class="pm-empty-hint">Добавьте агрегацию для расчета значений</span>
          </div>

          <div v-for="(agg, idx) in aggregations" :key="'a' + idx" class="pm-card">
            <div class="pm-row">
              <select
                v-if="availableFields.length > 0"
                v-model="agg.field"
                class="pm-select"
                style="flex: 1; min-width: 100px"
              >
                <option value="">-- Поле --</option>
                <option v-for="f in availableFields" :key="f.name" :value="f.name">{{ f.name }}</option>
              </select>
              <input v-else v-model="agg.field" type="text" class="pm-input" style="flex: 1; min-width: 100px" placeholder="Поле" />

              <select v-model="agg.agg" class="pm-select" style="width: 150px; flex-shrink: 0">
                <option value="count">COUNT</option>
                <option value="ucount">COUNT DISTINCT</option>
                <option value="sum">SUM</option>
                <option value="avg">AVG</option>
                <option value="min">MIN</option>
                <option value="max">MAX</option>
              </select>

              <input
                v-model="agg.outputName"
                type="text"
                class="pm-input"
                style="flex: 1; min-width: 100px"
                placeholder="Выходное имя"
              />

              <button class="pm-btn pm-btn--danger pm-btn--icon pm-btn--sm" @click="removeAggregation(idx)">
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
import { BarChart3, Plus, X } from 'lucide-vue-next'

const props = defineProps({
  show: { type: Boolean, default: false },
  initialConfig: { type: Object, default: null },
  availableFields: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'apply'])
const groupBy = ref([])
const aggregations = ref([])

function addGroupField() { groupBy.value.push('') }
function removeGroupField(idx) { groupBy.value.splice(idx, 1) }

function addAggregation() {
  aggregations.value.push({ field: '', agg: 'sum', outputName: '' })
}
function removeAggregation(idx) { aggregations.value.splice(idx, 1) }

function handleApply() {
  emit('apply', {
    groupBy: groupBy.value.filter(f => f),
    aggregations: aggregations.value.filter(a => a.field).map(a => ({
      ...a,
      outputName: a.outputName || `${a.field}_${a.agg}`
    }))
  })
}

watch(() => props.show, (isOpen) => {
  if (!isOpen) return
  const config = props.initialConfig
  groupBy.value = config?.groupBy ? [...config.groupBy] : []
  aggregations.value = config?.aggregations ? config.aggregations.map(a => ({ ...a })) : []
})
</script>

<style scoped lang="scss">
@import '../scss/pipeline-modals.scss';
</style>
