<template>
  <ModalCenter
    modal-id="pipelineDataSourceModal"
    standalone
    :visible="show"
    :dialog-style="{ maxWidth: '600px' }"
    :z-index="10050"
    :close-on-esc="false"
    @close="handleClose"
  >
    <template #title>
      <Database :size="22" class="text-primary" />
      <span>Источник данных</span>
    </template>

    <!-- Режим: Собрать из подключения -->
    <div class="mode-content">
          <div class="inline-steps">
            <!-- Шаг 1: Подключение -->
            <div class="step-panel" :class="{ completed: !!selectedConnection }">
              <div class="step-header" @click="toggleStep('connection')">
                <div class="step-number">1</div>
                <div class="step-info">
                  <span class="step-title">Подключение</span>
                  <span v-if="selectedConnection" class="step-value">{{ selectedConnection.name }}</span>
                </div>
                <ChevronDown :size="18" class="step-chevron" :class="{ expanded: expandedStep === 'connection' }" />
              </div>
              <div v-if="expandedStep === 'connection'" class="step-content">
                <ConnectionPicker
                  v-model="selectedConnection"
                  @select="onConnectionSelect"
                />
              </div>
            </div>

            <!-- Шаг 2: Главная таблица -->
            <div class="step-panel" :class="{ completed: !!mainTable, disabled: !selectedConnection }">
              <div class="step-header" @click="toggleStep('table')">
                <div class="step-number">2</div>
                <div class="step-info">
                  <span class="step-title">Таблица / файл</span>
                  <span v-if="mainTable" class="step-value">{{ getSourceItemDisplayName(mainTable) }}</span>
                </div>
                <ChevronDown :size="18" class="step-chevron" :class="{ expanded: expandedStep === 'table' }" />
              </div>
              <div v-if="expandedStep === 'table' && selectedConnection" class="step-content">
                <TablePicker
                  ref="tablePickerRef"
                  v-model="mainTable"
                  :connection-id="selectedConnection?.id"
                  :connection-type="connectionType"
                  @select="onTableSelect"
                  @tables-loaded="onTablesLoaded"
                />
              </div>
            </div>
          </div>
    </div>

    <template #footer>
      <button type="button" class="btn btn-secondary" @click="handleClose">
        Отмена
      </button>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="!canApply"
        @click="handleApply"
      >
        Применить
      </button>
    </template>
  </ModalCenter>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Database, ChevronDown } from 'lucide-vue-next'
import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'
import ModalCenter from '@/components/ModalCenter.vue'
import ConnectionPicker from './DataSource/ConnectionPicker.vue'
import TablePicker from './DataSource/TablePicker.vue'
import { getConnectionType } from './DataSource/js/connectionType.js'
import { getSourceItemKey, getSourceItemDisplayName } from './DataSource/js/sourceItemUtils.js'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  initialConfig: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'apply'])

const expandedStep = ref('connection')
const selectedConnection = ref(null)
const mainTable = ref(null)
const allTables = ref([])
const tablePickerRef = ref(null)

const connectionType = computed(() => getConnectionType(selectedConnection.value))

const canApply = computed(() => {
  return !!selectedConnection.value && !!mainTable.value
})

function toggleStep(step) {
  if (step === 'table' && !selectedConnection.value) return
  expandedStep.value = expandedStep.value === step ? null : step
}

function onConnectionSelect(conn) {
  if (selectedConnection.value?.id !== conn.id) {
    mainTable.value = null
    allTables.value = []
  }
  expandedStep.value = 'table'
}

function onTableSelect() {
  expandedStep.value = 'table'
}

function onTablesLoaded(tables) {
  allTables.value = tables
}

function handleClose() {
  emit('close')
}

function handleApply() {
  if (!canApply.value) return

  const conn = selectedConnection.value
  const table = mainTable.value
  const config = {
    sourceMode: 'inline',
    connection_id: conn.id,
    connectionName: conn.name,
    connectionType: getConnectionType(conn),
    main_table: {
      id: getSourceItemKey(table),
      name: getSourceItemDisplayName(table),
      schema: table.schema || null,
      file_id: table.file_id || table.file_upload_id || null,
      original_filename: table.original_filename || null
    }
  }
  emit('apply', config)
}

async function enrichConnectionFromList(connectionId) {
  try {
    const res = await apiClient.get(biEndpoints.bi.ConnectionsList)
    if (res.success && res.data && Array.isArray(res.data)) {
      const found = res.data.find(c => String(c.id) === String(connectionId))
      if (found) {
        selectedConnection.value = {
          ...selectedConnection.value,
          connector_type: found.connector_type,
          connector_type_display: found.connector_type_display
        }
      }
    }
  } catch (err) {
    logWarn('Не удалось подгрузить тип подключения:', err)
  }
}

function loadFromConfig(config) {
  if (!config) {
    selectedConnection.value = null
    mainTable.value = null
    expandedStep.value = 'connection'
    return
  }

  if (config.sourceMode === 'inline' || (config.connection_id && config.main_table)) {
    const connectionTypeValue = config.connectionType || config.connector_type_display || config.connector_type
    selectedConnection.value = {
      id: config.connection_id,
      name: config.connectionName || 'Подключение',
      connector_type: config.connector_type || connectionTypeValue,
      connector_type_display: config.connector_type_display || connectionTypeValue
    }
    mainTable.value = config.main_table || null
    expandedStep.value = mainTable.value ? 'table' : 'connection'

    if (config.connection_id && !connectionTypeValue) {
      enrichConnectionFromList(config.connection_id)
    }
  } else {
    selectedConnection.value = null
    mainTable.value = null
    expandedStep.value = 'connection'
  }
}

watch(() => props.show, (isOpen) => {
  if (isOpen) {
    loadFromConfig(props.initialConfig)
  }
})

watch(() => props.initialConfig, (config) => {
  if (props.show) {
    loadFromConfig(config)
  }
}, { deep: true })
</script>

<style scoped lang="scss">
.mode-content {
  min-height: 300px;
}

.inline-steps {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.step-panel {
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.15s ease;

  &.completed {
    border-color: rgba(59, 130, 246, 0.3);
  }

  &.disabled {
    opacity: 0.5;
    pointer-events: none;
  }
}

.step-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  cursor: pointer;
  transition: background 0.15s ease;

  &:hover {
    background: rgba(0, 0, 0, 0.02);
  }
}

.step-number {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-secondary-text);
  flex-shrink: 0;

  .completed & {
    background: #3b82f6;
    color: #fff;
  }
}

.step-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary-text);
}

.step-value {
  font-size: 12px;
  color: var(--color-secondary-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-chevron {
  color: var(--color-secondary-text);
  transition: transform 0.2s ease;
  flex-shrink: 0;

  &.expanded {
    transform: rotate(180deg);
  }
}

.step-content {
  padding: 0 1rem 1rem 1rem;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  max-height: 300px;
  overflow-y: auto;
}
</style>
