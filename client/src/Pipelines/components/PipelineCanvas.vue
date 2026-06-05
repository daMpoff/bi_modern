<template>
  <div class="pipeline-canvas-root">
    <div class="pipeline-toolbar">
      <div class="toolbar-section">
        <h3 class="toolbar-title">Блоки</h3>
        <div class="toolbar-items">
          <button
            v-if="showExecuteButton"
            type="button"
            class="toolbar-execute-btn"
            :disabled="executeLoading || !editor.nodes.value.length"
            @click="$emit('execute')"
          >
            <Play v-if="!executeLoading" :size="18" />
            <span v-else class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            <span>Выполнить</span>
          </button>
          <div
            v-for="bt in editor.blockTypes"
            :key="bt.type"
            class="toolbar-item"
            :class="{ 'toolbar-item--disabled': editor.isSingletonFull(bt.type) }"
            :draggable="!editor.isSingletonFull(bt.type)"
            @dragstart="editor.handleToolbarDragStart(bt, $event)"
            @dragend="editor.handleToolbarDragEnd()"
          >
            <component :is="bt.icon" :size="20" />
            <span class="toolbar-item-label">{{ bt.label }}</span>
          </div>
        </div>
      </div>
      <div v-if="showClearAll" class="toolbar-section">
        <button
          type="button"
          class="toolbar-clear-btn"
          :disabled="editor.nodes.value.length === 0"
          @click="editor.openClearAllConfirm()"
        >
          <Trash2 :size="18" />
          <span>Стереть все</span>
        </button>
      </div>
    </div>

    <div
      class="pipeline-canvas"
      ref="canvasEl"
      @drop="onDrop"
      @dragover.prevent
    >
      <div
        v-if="editor.pipelineWarning.value"
        class="pipeline-warning-bar"
      >
        <span>{{ editor.pipelineWarning.value }}</span>
        <button @click="editor.clearWarning()" class="pipeline-warning-close">&times;</button>
      </div>

      <VueFlow
        :nodes="editor.nodesWithDeleteState.value"
        :edges="editor.edges.value"
        :node-types="editor.nodeTypesMap"
        class="vue-flow-editor"
        :apply-default="false"
        @connect="editor.onConnect"
        @node-click="handleNodeClick"
        @nodes-change="editor.onNodesChange"
        @edge-click="editor.handleEdgeClick"
        :fit-view-on-init="false"
      >
        <MiniMap
          v-if="showMinimap"
          pannable
          zoomable
          :node-stroke-width="2"
          :node-border-radius="6"
          class="pipeline-minimap"
        />
      </VueFlow>
    </div>

    <PipelineDataSourceModal
      :show="editor.showDataSourceModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      @close="editor.closeAllModals()"
      @apply="editor.applyConfig"
    />

    <PipelineFilterModal
      :show="editor.showFilterModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      :available-fields="editor.availableFields.value"
      @close="editor.closeAllModals()"
      @apply="editor.applyConfig"
    />

    <PipelineAggregationModal
      :show="editor.showAggregationModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      :available-fields="editor.availableFields.value"
      @close="editor.closeAllModals()"
      @apply="editor.applyConfig"
    />

    <PipelineJoinModal
      :show="editor.showJoinModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      :left-source="editor.joinLeftSource.value"
      :right-source="editor.joinRightSource.value"
      @close="editor.closeAllModals()"
      @apply="editor.applyConfig"
    />

    <PipelineChartSettingsModal
      :show="editor.showChartModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      :available-fields="editor.availableFields.value"
      :preview-data="previewData"
      :preview-columns="previewColumns"
      @close="editor.closeAllModals()"
      @apply="handleChartApply"
    />

    <PipelineFormulaModal
      :show="editor.showFormulaModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      :available-fields="editor.availableFields.value"
      @close="editor.closeAllModals()"
      @apply="editor.applyConfig"
    />

    <PipelinePythonScriptModal
      :show="editor.showPythonScriptModal.value"
      :initial-config="editor.selectedNodeConfig.value"
      :available-fields="editor.availableFields.value"
      @close="editor.closeAllModals()"
      @apply="editor.applyConfig"
    />

    <ConfirmDialog
      :show="editor.showDeleteConfirm.value"
      title="Удаление блока"
      message="Удалить этот блок пайплайна?"
      confirm-text="Удалить"
      cancel-text="Отмена"
      @confirm="editor.confirmDeleteNode()"
      @close="editor.cancelDeleteNode()"
    />

    <ConfirmDialog
      :show="editor.showClearAllConfirm.value"
      title="Стереть все"
      message="Удалить все блоки и связи пайплайна?"
      confirm-text="Стереть все"
      cancel-text="Отмена"
      @confirm="editor.confirmClearAll()"
      @close="editor.cancelClearAll()"
    />

    <ConfirmDialog
      :show="editor.showDeleteEdgeConfirm.value"
      title="Удаление связи"
      message="Удалить эту связь между блоками?"
      confirm-text="Удалить"
      cancel-text="Отмена"
      @confirm="editor.confirmDeleteEdge()"
      @close="editor.cancelDeleteEdge()"
    />
  </div>
</template>

<script setup>
import { ref, watch, defineAsyncComponent } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { MiniMap } from '@vue-flow/minimap'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/minimap/dist/style.css'
import { Play, Trash2 } from 'lucide-vue-next'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const PipelineDataSourceModal = defineAsyncComponent(() => import('@/modules/bi_analysis_modern/client/src/Dashboards/PipelineDataSourceModal.vue'))
const PipelineFilterModal = defineAsyncComponent(() => import('./PipelineFilterModal.vue'))
const PipelineAggregationModal = defineAsyncComponent(() => import('./PipelineAggregationModal.vue'))
const PipelineJoinModal = defineAsyncComponent(() => import('./PipelineJoinModal.vue'))
const PipelineChartSettingsModal = defineAsyncComponent(() => import('./PipelineChartSettingsModal.vue'))
const PipelineFormulaModal = defineAsyncComponent(() => import('./PipelineFormulaModal.vue'))
const PipelinePythonScriptModal = defineAsyncComponent(() => import('./PipelinePythonScriptModal.vue'))

import { usePipelineEditor } from '../js/usePipelineEditor.js'

const props = defineProps({
  context: { type: String, default: 'dashboard' },
  initialNodes: { type: Array, default: () => [] },
  initialEdges: { type: Array, default: () => [] },
  showMinimap: { type: Boolean, default: true },
  showClearAll: { type: Boolean, default: true },
  showExecuteButton: { type: Boolean, default: false },
  executeLoading: { type: Boolean, default: false },
  previewData: { type: Array, default: () => [] },
  previewColumns: { type: Array, default: () => [] },
  onExecute: { type: Function, default: null },
  suppressChartModal: { type: Boolean, default: false }
})

const emit = defineEmits([
  'nodes-update', 'edges-update', 'block-config-update', 'execute', 'chart-node-click'
])

const editor = usePipelineEditor(props.context, {
  suppressChartModal: () => props.suppressChartModal,
  whenChartSettingsRequested: (nodeId) => emit('chart-node-click', nodeId)
})
const canvasEl = ref(null)

watch(canvasEl, (el) => {
  if (el) editor.canvasRef.value = el
})

function onDrop(event) {
  editor.canvasRef.value = canvasEl.value
  editor.handleCanvasDrop(event)
}

watch(() => [props.initialNodes, props.initialEdges], ([n, e]) => {
  if (n && n.length > 0) {
    editor.loadPipelineData(n, e)
  }
}, { immediate: true, deep: true })

watch(editor.nodes, (val) => { emit('nodes-update', val) }, { deep: true, immediate: true })
watch(editor.edges, (val) => { emit('edges-update', val) }, { deep: true })

function handleNodeClick(event) {
  const nodeId = event?.node?.id
  const nodeType = event?.node?.type
  if (!nodeId) return
  if ((props.suppressChartModal || props.context === 'graphs') && nodeType === 'chart') {
    emit('chart-node-click', nodeId)
    return
  }
  editor.openNodeSettings(nodeId)
}

function handleChartApply(config) {
  editor.applyConfig(config)
  emit('block-config-update', config)
}

defineExpose({
  nodes: editor.nodes,
  edges: editor.edges,
  getCleanGraphData: editor.getCleanGraphData,
  loadPipelineData: editor.loadPipelineData,
  addNode: editor.addNode,
})
</script>

<style scoped lang="scss">
.pipeline-canvas-root {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
  height: 100%;
}

.pipeline-toolbar {
  width: 220px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(0, 0, 0, 0.08);
  padding: 1.25rem;
  overflow-y: auto;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.toolbar-section {
  display: flex;
  flex-direction: column;
}

.toolbar-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-secondary-text);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 0.75rem 0;
}

.toolbar-items {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.toolbar-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.625rem 0.75rem;
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  cursor: grab;
  transition: all 0.15s ease;
  user-select: none;

  &:hover:not(.toolbar-item--disabled) {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.12);
    transform: translateX(3px);
  }

  &:active:not(.toolbar-item--disabled) { cursor: grabbing; }

  &--disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.toolbar-item-label {
  font-size: 13px;
  color: var(--color-primary-text);
  font-weight: 500;
}

.toolbar-execute-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.875rem;
  margin-bottom: 0.5rem;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  background: var(--bs-primary, #007aff);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover:not(:disabled) { filter: brightness(1.08); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

.toolbar-clear-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.5rem 0.875rem;
  font-size: 13px;
  font-weight: 500;
  color: #ff3b30;
  background: rgba(255, 59, 48, 0.08);
  border: 1px solid rgba(255, 59, 48, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover:not(:disabled) { background: rgba(255, 59, 48, 0.14); }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
}

.pipeline-canvas {
  flex: 1;
  position: relative;
  background: #fafafa;
}

.pipeline-warning-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.625rem 1rem;
  background: #fef3c7;
  border-bottom: 1px solid #f59e0b;
  color: #92400e;
  font-size: 13px;
  font-weight: 500;
}

.pipeline-warning-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #92400e;
  font-size: 18px;
  cursor: pointer;

  &:hover { background: rgba(146, 64, 14, 0.15); }
}

.vue-flow-editor {
  width: 100%;
  height: 100%;

  :deep(.vue-flow__node) {
    overflow: visible;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    border-radius: 0 !important;
    width: auto !important;
    height: auto !important;

    &.selected,
    &:focus,
    &:focus-visible {
      outline: none !important;
      box-shadow: none !important;
    }
  }

  :deep(.vue-flow__handle) {
    width: 12px;
    height: 12px;
    background: #94a3b8;
    border: 2px solid #fff;
    border-radius: 50%;
    transition: all 0.15s ease;

    &:hover {
      width: 16px;
      height: 16px;
      background: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
    }
  }

  :deep(.vue-flow__edge) {
    cursor: pointer;
    &:hover .vue-flow__edge-path { stroke-width: 3px; }
  }
}

.pipeline-minimap {
  right: 12px;
  bottom: 12px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
</style>
