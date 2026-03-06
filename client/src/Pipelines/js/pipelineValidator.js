/**
 * Валидация пайплайн-графа: обнаружение циклов, проверка связей, проверка конфигурации.
 */

function buildAdjacencyList(edges) {
  const adj = {}
  for (const e of edges) {
    if (!adj[e.source]) adj[e.source] = []
    adj[e.source].push(e.target)
  }
  return adj
}

function buildReverseAdjacencyList(edges) {
  const rev = {}
  for (const e of edges) {
    if (!rev[e.target]) rev[e.target] = []
    rev[e.target].push(e.source)
  }
  return rev
}

export function hasCycles(nodes, edges) {
  const adj = buildAdjacencyList(edges)
  const nodeIds = new Set(nodes.map(n => n.id))
  const WHITE = 0, GRAY = 1, BLACK = 2
  const color = {}
  for (const id of nodeIds) color[id] = WHITE

  function dfs(nodeId) {
    color[nodeId] = GRAY
    for (const neighbor of (adj[nodeId] || [])) {
      if (color[neighbor] === GRAY) return true
      if (color[neighbor] === WHITE && dfs(neighbor)) return true
    }
    color[nodeId] = BLACK
    return false
  }

  for (const id of nodeIds) {
    if (color[id] === WHITE && dfs(id)) return true
  }
  return false
}

function getIncomingCount(nodeId, reverseAdj) {
  return (reverseAdj[nodeId] || []).length
}

/** Карта рёбер: target -> [source1, source2, ...] */
function buildEdgesMap(edges) {
  const map = {}
  for (const e of edges) {
    if (!map[e.target]) map[e.target] = []
    map[e.target].push(e.source)
  }
  return map
}

/**
 * Найти конфиг источника данных для узла (идём по цепочке к dataSource).
 * Возвращает config источника или null.
 */
function findDataSourceConfigForNode(nodeId, nodes, edgesMap) {
  const node = nodes.find(n => n.id === nodeId)
  if (!node) return null
  if (node.type === 'dataSource') return node.data?.config || {}
  if (node.type === 'filter' || node.type === 'aggregation') {
    const inputs = edgesMap[nodeId] || []
    if (inputs.length === 1) return findDataSourceConfigForNode(inputs[0], nodes, edgesMap)
  }
  return null
}

/** Ключ для сравнения main_table (объект или строка) */
function mainTableKey(mt) {
  if (mt == null) return ''
  if (typeof mt === 'string') return mt
  const id = mt.id ?? mt.file_id
  if (id != null) return String(id)
  return (mt.name ?? mt.original_filename ?? '') || ''
}

/** Один и тот же источник? (inline: connection + table/file) */
function isSameSource(config1, config2) {
  if (!config1 || !config2) return false
  if (config1.sourceMode === 'inline' && config2.sourceMode === 'inline') {
    return (
      config1.connection_id === config2.connection_id &&
      mainTableKey(config1.main_table) === mainTableKey(config2.main_table)
    )
  }
  return false
}

function checkConnectivity(nodes, edges) {
  const errors = []
  const reverseAdj = buildReverseAdjacencyList(edges)

  for (const node of nodes) {
    if (node.type === 'dataSource') continue
    const incoming = getIncomingCount(node.id, reverseAdj)
    if (incoming === 0) {
      errors.push({
        nodeId: node.id,
        type: 'error',
        message: `Блок "${node.data?.label || node.type}" не имеет входящих связей`
      })
    }
  }
  return errors
}

function checkConnectionRequirements(nodes, edges) {
  const errors = []
  const reverseAdj = buildReverseAdjacencyList(edges)

  for (const node of nodes) {
    const incoming = getIncomingCount(node.id, reverseAdj)

    if (node.type === 'join' && incoming !== 2) {
      errors.push({
        nodeId: node.id,
        type: 'error',
        message: `Блок "Соединение" требует ровно 2 входящих связи (сейчас: ${incoming})`
      })
    }

    const singleInputTypes = ['filter', 'aggregation', 'formula', 'pythonScript', 'chart', 'output']
    if (singleInputTypes.includes(node.type) && incoming > 1) {
      errors.push({
        nodeId: node.id,
        type: 'error',
        message: `Блок "${node.data?.label || node.type}" принимает только 1 входящую связь (сейчас: ${incoming})`
      })
    }
  }
  return errors
}

function checkConfiguration(nodes, edges) {
  const warnings = []
  const edgesMap = buildEdgesMap(edges || [])

  for (const node of nodes) {
    const config = node.data?.config || {}

    if (node.type === 'dataSource') {
      const hasInline = config.sourceMode === 'inline' && !!config.connection_id
      if (!hasInline) {
        warnings.push({
          nodeId: node.id,
          type: 'warning',
          message: 'Источник данных не настроен'
        })
      }
    }

    if (node.type === 'filter') {
      const conditions = config.conditions || []
      if (conditions.length === 0) {
        warnings.push({
          nodeId: node.id,
          type: 'warning',
          message: 'Фильтр не содержит условий'
        })
      }
    }

    if (node.type === 'aggregation') {
      const aggregations = config.aggregations || []
      if (aggregations.length === 0) {
        warnings.push({
          nodeId: node.id,
          type: 'warning',
          message: 'Агрегация не содержит операций'
        })
      }
    }

    if (node.type === 'join') {
      if (!config.joinType || !config.leftKey || !config.rightKey) {
        warnings.push({
          nodeId: node.id,
          type: 'warning',
          message: 'Соединение не полностью настроено'
        })
      }
      const sources = (edgesMap[node.id] || []).slice().sort()
      if (sources.length === 2) {
        const leftConfig = findDataSourceConfigForNode(sources[0], nodes, edgesMap)
        const rightConfig = findDataSourceConfigForNode(sources[1], nodes, edgesMap)
        const same = !!(leftConfig && rightConfig && isSameSource(leftConfig, rightConfig))
        if (leftConfig && rightConfig && same) {
          warnings.push({
            nodeId: node.id,
            type: 'warning',
            message: 'Оба входа соединения используют один и тот же источник данных. Убедитесь, что это намеренно (self-join).'
          })
        }
      }
    }
  }
  return warnings
}

export function validatePipeline(nodes, edges) {
  if (!nodes || nodes.length === 0) {
    return { valid: true, errors: [], warnings: [] }
  }

  const errors = []
  const warnings = []

  if (hasCycles(nodes, edges)) {
    errors.push({
      nodeId: null,
      type: 'error',
      message: 'Обнаружен цикл в пайплайне. Удалите циклическую связь.'
    })
  }

  errors.push(...checkConnectivity(nodes, edges))
  errors.push(...checkConnectionRequirements(nodes, edges))
  warnings.push(...checkConfiguration(nodes, edges))

  return {
    valid: errors.length === 0,
    errors,
    warnings
  }
}

export function validateConnection(nodes, edges, newEdge) {
  if (newEdge.source === newEdge.target) {
    return { valid: false, message: 'Нельзя соединить блок с самим собой' }
  }

  const duplicate = edges.some(
    e => e.source === newEdge.source && e.target === newEdge.target
  )
  if (duplicate) {
    return { valid: false, message: 'Такая связь уже существует' }
  }

  const sourceNode = nodes.find(n => n.id === newEdge.source)
  const targetNode = nodes.find(n => n.id === newEdge.target)
  if (sourceNode?.type === 'dataSource' && targetNode?.type === 'dataSource') {
    return { valid: false, message: 'Нельзя соединять источник с источником' }
  }

  const testEdges = [...edges, { source: newEdge.source, target: newEdge.target }]
  if (hasCycles(nodes, testEdges)) {
    return { valid: false, message: 'Эта связь создаст цикл в пайплайне' }
  }

  return { valid: true, message: null }
}
