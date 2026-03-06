import { ref, computed, nextTick } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useToast } from 'vue-toastification'
import {
  getBlockTypesForContext, getNodeTypesMap,
  getBlockLabel, getSingletonTypes
} from './pipelineBlockTypes.js'
import { validateConnection, validatePipeline } from './pipelineValidator.js'
import {
  getOutputFieldsWithTypesForNode,
  getOutputFieldsForNode,
  getAvailableFieldsForNode
} from './pipelineNodeFields.js'

/**
 * @param {string} context - 'pipeline' | 'dashboard' | 'graphs'
 * @param {{ whenChartSettingsRequested?: (nodeId: string) => void, suppressChartModal?: () => boolean }} [options] - когда suppressChartModal() true, по клику на настройки графика не открывать модалку, а вызвать whenChartSettingsRequested(nodeId)
 */
export function usePipelineEditor(context = 'dashboard', options = {}) {
  const toast = useToast()
  const { whenChartSettingsRequested, suppressChartModal } = options
  const { updateNodeInternals, onPaneReady } = useVueFlow()

  const vueFlowInstance = ref(null)
  onPaneReady((instance) => { vueFlowInstance.value = instance })

  const blockTypes = getBlockTypesForContext(context)
  const nodeTypesMap = getNodeTypesMap(context)
  const singletonTypes = getSingletonTypes(context)

  const nodes = ref([])
  const edges = ref([])
  const canvasRef = ref(null)
  const draggedBlockType = ref(null)

  const showDataSourceModal = ref(false)
  const showFilterModal = ref(false)
  const showAggregationModal = ref(false)
  const showJoinModal = ref(false)
  const showChartModal = ref(false)
  const showFormulaModal = ref(false)
  const showPythonScriptModal = ref(false)

  const selectedNodeId = ref(null)
  const selectedNodeConfig = ref(null)
  const availableFields = ref([])
  const availableFieldsSimple = ref([])

  const showDeleteConfirm = ref(false)
  const nodeToDelete = ref(null)
  const showDeleteEdgeConfirm = ref(false)
  const edgeToDelete = ref(null)
  const showClearAllConfirm = ref(false)
  const pipelineWarning = ref('')
  let warningTimeout = null

  function hasSingletonNode(type) {
    return nodes.value.some(n => n.type === type)
  }

  const singletonFlags = computed(() => {
    const flags = {}
    for (const t of singletonTypes) {
      flags[t] = nodes.value.some(n => n.type === t)
    }
    return flags
  })

  function isSingletonFull(type) {
    return singletonTypes.includes(type) && singletonFlags.value[type]
  }

  const edgesMap = computed(() => {
    const map = {}
    for (const e of edges.value) {
      if (!map[e.target]) map[e.target] = []
      map[e.target].push(e.source)
    }
    return map
  })

  function buildEdgesMap() {
    return edgesMap.value
  }

  function findDataSourceConfig(nodeId, map = null) {
    const edgeMap = map ?? edgesMap.value
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node) return null
    if (node.type === 'dataSource') return { config: node.data?.config || {} }
    if (node.type === 'filter' || node.type === 'aggregation') {
      const inputs = edgeMap[nodeId] || []
      if (inputs.length === 1) return findDataSourceConfig(inputs[0], edgeMap)
    }
    return null
  }

  const connectedToJoinIds = computed(() => {
    const joinIds = new Set(nodes.value.filter(n => n.type === 'join').map(n => n.id))
    const set = new Set()
    for (const e of edges.value) {
      if (joinIds.has(e.target)) set.add(e.source)
    }
    return set
  })

  function isNodeConnectedToJoin(nodeId) {
    return connectedToJoinIds.value.has(nodeId)
  }

  const nodesWithDeleteState = computed(() =>
    nodes.value.map(n => ({
      ...n,
      data: {
        ...n.data,
        canDelete: !connectedToJoinIds.value.has(n.id)
      }
    }))
  )

  const joinLeftSource = computed(() => {
    if (!showJoinModal.value || !selectedNodeId.value) return null
    const map = edgesMap.value
    const sources = map[selectedNodeId.value] || []
    if (sources.length < 2) return null
    const [leftId] = sources.slice().sort()
    return findDataSourceConfig(leftId, map)
  })

  const joinRightSource = computed(() => {
    if (!showJoinModal.value || !selectedNodeId.value) return null
    const map = edgesMap.value
    const sources = map[selectedNodeId.value] || []
    if (sources.length < 2) return null
    const [, rightId] = sources.slice().sort()
    return findDataSourceConfig(rightId, map)
  })

  function showWarning(msg, duration = 6000) {
    if (warningTimeout) clearTimeout(warningTimeout)
    pipelineWarning.value = msg
    warningTimeout = setTimeout(() => {
      pipelineWarning.value = ''
      warningTimeout = null
    }, duration)
  }

  function clearWarning() {
    if (warningTimeout) {
      clearTimeout(warningTimeout)
      warningTimeout = null
    }
    pipelineWarning.value = ''
  }

  function generateNodeId() {
    return `node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  function addNode(type, position = { x: 250, y: 250 }) {
    if (isSingletonFull(type)) {
      const label = getBlockLabel(type, context)
      toast.warning(`В пайплайне допускается только один блок "${label}"`)
      return null
    }
    const id = generateNodeId()
    const bt = blockTypes.find(b => b.type === type)
    const newNode = {
      id, type, position,
      data: {
        label: bt?.label || type,
        nodeType: type,
        config: {},
        onSettings: (nodeId) => openNodeSettings(nodeId),
        onDelete: (nodeId) => openDeleteConfirm(nodeId)
      },
      draggable: true
    }
    nodes.value.push(newNode)
    updateNodeInternals(id)
    return id
  }

  function handleToolbarDragStart(blockType, event) {
    if (isSingletonFull(blockType.type)) {
      event.preventDefault()
      const label = getBlockLabel(blockType.type, context)
      toast.warning(`В пайплайне допускается только один блок "${label}"`)
      return
    }
    draggedBlockType.value = blockType
    event.dataTransfer.effectAllowed = 'copy'
  }

  function handleToolbarDragEnd() {
    draggedBlockType.value = null
  }

  function handleCanvasDrop(event) {
    if (!draggedBlockType.value || !vueFlowInstance.value) return
    const rect = canvasRef.value?.getBoundingClientRect()
    if (!rect) return
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    const pos = vueFlowInstance.value.project({ x, y })
    addNode(draggedBlockType.value.type, pos)
    draggedBlockType.value = null
  }

  function onConnect(params) {
    const result = validateConnection(nodes.value, edges.value, params)
    if (!result.valid) {
      showWarning(result.message, 5000)
      return
    }
    edges.value.push({
      id: `edge-${params.source}-${params.target}`,
      source: params.source,
      target: params.target,
      type: 'smoothstep',
      animated: true
    })
    const targetNode = nodes.value.find(n => n.id === params.target)
    if (targetNode?.type === 'join') {
      const { warnings } = validatePipeline(nodes.value, edges.value)
      const sameSourceWarning = warnings.find(
        w => w.nodeId === params.target && w.message?.includes('Оба входа соединения')
      )
      if (sameSourceWarning) {
        showWarning(sameSourceWarning.message, 5000)
      }
    }
  }

  function onNodesChange(changes) {
    for (const change of changes) {
      if (change.type === 'position' && change.position) {
        const node = nodes.value.find(n => n.id === change.id)
        if (node) {
          node.position = { x: change.position.x, y: change.position.y }
        }
      }
    }
  }

  function handleEdgeClick(event) {
    const edgeId = event.edge?.id
    if (!edgeId) return
    edgeToDelete.value = edgeId
    showDeleteEdgeConfirm.value = true
  }

  async function loadFieldsForNode(nodeId) {
    availableFields.value = []
    availableFieldsSimple.value = []
    try {
      const fields = await getAvailableFieldsForNode(nodes.value, edges.value, nodeId)
      availableFields.value = fields || []
      availableFieldsSimple.value = fields.map(f => f.name)
    } catch {
      availableFields.value = []
      availableFieldsSimple.value = []
    }
  }

  async function openNodeSettings(nodeId) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node) return
    selectedNodeId.value = nodeId
    selectedNodeConfig.value = node.data?.config || {}

    switch (node.type) {
      case 'dataSource':
        showDataSourceModal.value = true
        break
      case 'filter':
        await loadFieldsForNode(nodeId)
        showFilterModal.value = true
        break
      case 'aggregation':
        await loadFieldsForNode(nodeId)
        showAggregationModal.value = true
        break
      case 'join':
        showJoinModal.value = true
        nextTick(() => {
          const { warnings } = validatePipeline(nodes.value, edges.value)
          const sameSourceWarning = warnings.find(
            w => w.nodeId === nodeId && w.message?.includes('Оба входа соединения')
          )
          if (sameSourceWarning) {
            showWarning(sameSourceWarning.message, 5000)
          }
        })
        break
      case 'chart':
        if (typeof suppressChartModal === 'function' && suppressChartModal()) {
          if (typeof whenChartSettingsRequested === 'function') {
            whenChartSettingsRequested(nodeId)
          }
          return
        }
        await loadFieldsForNode(nodeId)
        showChartModal.value = true
        break
      case 'formula':
        await loadFieldsForNode(nodeId)
        showFormulaModal.value = true
        break
      case 'pythonScript':
        await loadFieldsForNode(nodeId)
        showPythonScriptModal.value = true
        break
      default:
        break
    }
  }

  function updateNodeConfig(nodeId, config) {
    const idx = nodes.value.findIndex(n => n.id === nodeId)
    if (idx === -1) return
    const node = nodes.value[idx]
    const baseLabel = getBlockLabel(node.type, context)
    let label = baseLabel

    if (node.type === 'dataSource') {
      if (config.sourceMode === 'inline' && config.connectionName) label = config.connectionName
    }
    if (node.type === 'join' && config.joinType) {
      label = `${baseLabel}: ${config.joinType}`
    }
    if (node.type === 'formula' && config.outputField) {
      label = `${baseLabel}: ${config.outputField}`
    }
    if (node.type === 'pythonScript' && config.scriptName) {
      label = `${baseLabel}: ${config.scriptName}`
    }

    nodes.value[idx] = {
      ...node,
      data: {
        ...node.data,
        config: { ...config },
        label,
        conditions: node.type === 'filter' ? config.conditions : undefined
      }
    }
    updateNodeInternals(nodeId)
    // После смены конфига (например, выбора файла в источнике) перепроверяем join'ы на одинаковый источник
    if (node.type === 'dataSource') {
      nextTick(() => {
        const { warnings } = validatePipeline(nodes.value, edges.value)
        const sameSourceWarnings = warnings.filter(
          w => w.message?.includes('Оба входа соединения')
        )
        sameSourceWarnings.forEach(w => showWarning(w.message, 5000))
      })
    }
  }

  function closeAllModals() {
    showDataSourceModal.value = false
    showFilterModal.value = false
    showAggregationModal.value = false
    showJoinModal.value = false
    showChartModal.value = false
    showFormulaModal.value = false
    showPythonScriptModal.value = false
    selectedNodeId.value = null
    selectedNodeConfig.value = null
    availableFields.value = []
    availableFieldsSimple.value = []
  }

  function applyConfig(config) {
    if (selectedNodeId.value) {
      updateNodeConfig(selectedNodeId.value, config)
    }
    closeAllModals()
  }

  function openDeleteConfirm(nodeId) {
    if (isNodeConnectedToJoin(nodeId)) {
      showWarning('Невозможно удалить блок: он подключен к блоку "Соединение". Сначала удалите блок "Соединение".')
      return
    }
    nodeToDelete.value = nodeId
    showDeleteConfirm.value = true
  }

  function confirmDeleteNode() {
    const id = nodeToDelete.value
    if (!id) return
    nodes.value = nodes.value.filter(n => n.id !== id)
    edges.value = edges.value.filter(e => e.source !== id && e.target !== id)
    nodeToDelete.value = null
    showDeleteConfirm.value = false
  }

  function cancelDeleteNode() {
    nodeToDelete.value = null
    showDeleteConfirm.value = false
  }

  function confirmDeleteEdge() {
    if (!edgeToDelete.value) return
    edges.value = edges.value.filter(e => e.id !== edgeToDelete.value)
    edgeToDelete.value = null
    showDeleteEdgeConfirm.value = false
    toast.success('Связь удалена')
  }

  function cancelDeleteEdge() {
    edgeToDelete.value = null
    showDeleteEdgeConfirm.value = false
  }

  function openClearAllConfirm() {
    showClearAllConfirm.value = true
  }

  function confirmClearAll() {
    nodes.value = []
    edges.value = []
    showClearAllConfirm.value = false
  }

  function cancelClearAll() {
    showClearAllConfirm.value = false
  }

  function loadPipelineData(pipelineNodes, pipelineEdges) {
    nodes.value = (pipelineNodes || []).map(n => ({
      ...n,
      data: {
        ...n.data,
        onSettings: (id) => openNodeSettings(id),
        onDelete: (id) => openDeleteConfirm(id)
      }
    }))
    edges.value = pipelineEdges || []
  }

  function getCleanGraphData() {
    const cleanNodes = nodes.value.map(n => ({
      id: n.id,
      type: n.type,
      position: { x: n.position.x, y: n.position.y },
      data: { label: n.data?.label, nodeType: n.data?.nodeType, config: n.data?.config || {} },
      draggable: n.draggable ?? true
    }))
    const cleanEdges = edges.value.map(e => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: e.type || 'smoothstep',
      animated: e.animated ?? true
    }))
    return { nodes: cleanNodes, edges: cleanEdges }
  }

  return {
    blockTypes,
    nodeTypesMap,
    nodes,
    edges,
    canvasRef,
    vueFlowInstance,
    nodesWithDeleteState,
    singletonFlags,
    pipelineWarning,

    showDataSourceModal,
    showFilterModal,
    showAggregationModal,
    showJoinModal,
    showChartModal,
    showFormulaModal,
    showPythonScriptModal,
    selectedNodeId,
    selectedNodeConfig,
    availableFields,
    availableFieldsSimple,
    joinLeftSource,
    joinRightSource,

    showDeleteConfirm,
    nodeToDelete,
    showDeleteEdgeConfirm,
    showClearAllConfirm,

    addNode,
    handleToolbarDragStart,
    handleToolbarDragEnd,
    handleCanvasDrop,
    onConnect,
    onNodesChange,
    handleEdgeClick,
    openNodeSettings,
    updateNodeConfig,
    closeAllModals,
    applyConfig,
    openDeleteConfirm,
    confirmDeleteNode,
    cancelDeleteNode,
    confirmDeleteEdge,
    cancelDeleteEdge,
    openClearAllConfirm,
    confirmClearAll,
    cancelClearAll,
    loadPipelineData,
    getCleanGraphData,
    clearWarning,
    isSingletonFull,
    buildEdgesMap,
    findDataSourceConfig,
  }
}
