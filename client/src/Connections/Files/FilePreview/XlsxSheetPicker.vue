<template>
  <ModalCenter
    modal-id="xlsxSheetPickerModal"
    standalone
    :visible="visible"
    :title="singleSelect ? 'Выбрать лист для замены' : 'Добавить листы'"
    :dialog-style="{ maxWidth: '480px', width: '90%' }"
    :z-index="10050"
    @close="cancel"
  >
    <div v-if="!singleSelect" class="select-all">
      <div class="form-check mb-2">
        <input class="form-check-input" type="checkbox" id="select-all" @change="toggleAll" :disabled="!sheets?.length"/>
        <label class="form-check-label" for="select-all">
          Выбрать все
        </label>
      </div>
    </div>
    <div class="sheet-list">
      <div class="form-check" v-for="sheet in safeSheets" :key="sheet">
        <input
          class="form-check-input"
          :type="singleSelect ? 'radio' : 'checkbox'"
          :name="singleSelect ? 'sheet-selection' : undefined"
          :id="'sheet-' + sheet"
          :value="sheet"
          :checked="isSheetSelected(sheet)"
          @change="handleSheetChange(sheet, $event)"
        />
        <label class="form-check-label" :for="'sheet-' + sheet">
          {{ filename || 'Файл' }} – {{ sheet }}
        </label>
      </div>
      <div v-if="!safeSheets.length">Листы не найдены</div>
    </div>

    <template #footer>
      <button class="btn-cancel" @click="cancel">Отмена</button>
      <button class="btn-confirm" :disabled="singleSelect ? !selectedSheet : !selectedSheets.length" @click="confirm">{{ singleSelect ? 'Выбрать' : 'Добавить' }}</button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import ModalCenter from '@/components/ModalCenter.vue'

const props = defineProps({
  visible: Boolean,
  filename: String,
  sheets: Array,
  currentSheet: String,
  singleSelect: Boolean
})

const emit = defineEmits(['confirm', 'cancel'])

const selectedSheets = ref([])
const selectedSheet = ref('')
const selectAll = ref(false)
const safeSheets = computed(() => props.sheets || [])

watch(selectAll, (val) => {
  selectedSheets.value = val ? [...safeSheets.value] : []
})

function toggleAll() {
  const allSelected = selectedSheets.value.length === safeSheets.value.length
  selectedSheets.value = allSelected ? [] : [...safeSheets.value]
}

function isSheetSelected(sheet) {
  if (props.singleSelect) {
    return selectedSheet.value === sheet
  } else {
    return selectedSheets.value.includes(sheet)
  }
}

function handleSheetChange(sheet, event) {
  if (props.singleSelect) {
    selectedSheet.value = event.target.checked ? sheet : ''
  } else {
    if (event.target.checked) {
      if (!selectedSheets.value.includes(sheet)) {
        selectedSheets.value.push(sheet)
      }
    } else {
      const index = selectedSheets.value.indexOf(sheet)
      if (index > -1) {
        selectedSheets.value.splice(index, 1)
      }
    }
  }
}

function confirm() {
  if (props.singleSelect) {
    emit('confirm', selectedSheet.value ? [selectedSheet.value] : [])
  } else {
    emit('confirm', selectedSheets.value)
  }
}

function cancel() {
  emit('cancel')
}

watch(() => props.visible, (val) => {
  if (val) {
    selectedSheets.value = []
    selectedSheet.value = props.singleSelect && props.currentSheet ? props.currentSheet : ''
    selectAll.value = false
  }
})
</script>

<style scoped>
.sheet-list {
  max-height: 300px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-cancel {
  background: transparent;
  color: var(--color-secondary-text);
  border: 1px solid var(--color-border);
  padding: 6px 12px;
  border-radius: 6px;
}

.btn-confirm {
  background: var(--color-accent);
  color: var(--color-primary-text);
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
