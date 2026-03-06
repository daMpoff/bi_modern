import { apiClient } from '@/js/api/manager'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints'

function buildEdgesMap(edges) {
  const map = {}
  for (const e of edges || []) {
    if (e.target && e.source) {
      if (!map[e.target]) map[e.target] = []
      map[e.target].push(e.source)
    }
  }
  return map
}

function getNodeById(nodes, nodeId) {
  return (nodes || []).find(n => n.id === nodeId) || null
}

const FIELD_TYPE_STRING = 'string'
const FIELD_TYPE_NUMBER = 'number'
const FIELD_TYPE_DATE = 'date'
const FIELD_TYPE_BOOLEAN = 'boolean'

function normalizeFieldType(raw) {
  const t = (raw || '').toLowerCase().trim()
  if (t === 'integer' || t === 'float') return FIELD_TYPE_NUMBER
  if (t === 'date' || t === 'date&time' || t === 'datetime') return FIELD_TYPE_DATE
  if (t === 'bool' || t === 'boolean') return FIELD_TYPE_BOOLEAN
  return FIELD_TYPE_STRING
}

function toFieldWithType(name, rawType) {
  return { name: String(name), type: normalizeFieldType(rawType) }
}

export async function fetchDataSourceColumns(connectionId, mainTable) {
  if (!connectionId || !mainTable) return []
  try {
    const res = await apiClient.post(biEndpoints.bi.dataSourceColumns, {
      connection_id: connectionId,
      main_table: mainTable
    })
    const cols = res?.data?.columns
    return Array.isArray(cols) ? cols : []
  } catch {
    return []
  }
}

async function getDataSourceOutputFields(config) {
  const sourceMode = config.sourceMode || 'inline'

  if (sourceMode === 'inline') {
    const connectionId = config.connection_id
    const mainTable = config.main_table
    if (!connectionId || !mainTable) return []
    const columns = await fetchDataSourceColumns(connectionId, mainTable)
    return columns.map(c => (c && typeof c === 'object' && c.name != null) ? c.name : String(c))
  }

  return []
}

async function getDataSourceOutputFieldsWithTypes(config) {
  const sourceMode = config.sourceMode || 'inline'

  if (sourceMode === 'inline') {
    const connectionId = config.connection_id
    const mainTable = config.main_table
    if (!connectionId || !mainTable) return []
    const columns = await fetchDataSourceColumns(connectionId, mainTable)
    return columns.map(c => {
      const name = c && typeof c === 'object' && c.name != null ? c.name : String(c)
      const rawType = c && typeof c === 'object' && c.type != null ? c.type : 'string'
      return toFieldWithType(name, rawType)
    })
  }

  return []
}

function getAggregationOutputFieldsWithTypes(config, upstreamFieldsWithTypes) {
  const groupBy = config.groupBy || []
  const aggregations = config.aggregations || []
  const upstreamMap = new Map((upstreamFieldsWithTypes || []).map(f => [f.name, f.type]))
  const out = []
  for (const name of groupBy) {
    out.push(toFieldWithType(name, upstreamMap.get(name) || 'string'))
  }
  for (const agg of aggregations) {
    const name = agg.outputName || (agg.field ? `${agg.field}_${agg.agg || 'count'}` : null)
    if (name) out.push({ name, type: FIELD_TYPE_NUMBER })
  }
  return out
}

function getAggregationOutputFields(config) {
  const groupBy = config.groupBy || []
  const aggregations = config.aggregations || []
  const out = [...groupBy]
  for (const agg of aggregations) {
    const name = agg.outputName || (agg.field ? `${agg.field}_${agg.agg || 'count'}` : null)
    if (name) out.push(name)
  }
  return out
}

function getFormulaOutputFieldsWithTypes(config, upstreamFieldsWithTypes) {
  const upstream = [...(upstreamFieldsWithTypes || [])]
  const outputField = config.outputField
  if (outputField) {
    const outputType = config.outputType || 'number'
    const exists = upstream.findIndex(f => f.name === outputField)
    if (exists >= 0) {
      upstream[exists] = toFieldWithType(outputField, outputType)
    } else {
      upstream.push(toFieldWithType(outputField, outputType))
    }
  }
  return upstream
}

function getPythonScriptOutputFieldsWithTypes(config, upstreamFieldsWithTypes) {
  const outputFields = config.outputFields
  if (Array.isArray(outputFields) && outputFields.length > 0) {
    return outputFields.map(f => {
      if (typeof f === 'object' && f.name) return toFieldWithType(f.name, f.type || 'string')
      return toFieldWithType(String(f), 'string')
    })
  }
  return [...(upstreamFieldsWithTypes || [])]
}

export async function getOutputFieldsWithTypesForNode(nodes, edges, nodeId) {
  const edgesMap = buildEdgesMap(edges)
  const node = getNodeById(nodes, nodeId)
  if (!node) return []

  const config = (node.data || {}).config || {}
  const type = node.type || ''

  switch (type) {
    case 'dataSource':
      return getDataSourceOutputFieldsWithTypes(config)

    case 'filter': {
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      return getOutputFieldsWithTypesForNode(nodes, edges, sources[0])
    }

    case 'aggregation': {
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      const upstream = await getOutputFieldsWithTypesForNode(nodes, edges, sources[0])
      return getAggregationOutputFieldsWithTypes(config, upstream)
    }

    case 'join': {
      const sources = (edgesMap[nodeId] || []).slice().sort()
      if (sources.length !== 2) return []
      const [leftId, rightId] = sources
      const [leftFields, rightFields] = await Promise.all([
        getOutputFieldsWithTypesForNode(nodes, edges, leftId),
        getOutputFieldsWithTypesForNode(nodes, edges, rightId)
      ])
      const leftSet = new Set(leftFields.map(f => f.name))
      const merged = [...leftFields]
      for (const f of rightFields) {
        merged.push(leftSet.has(f.name) ? toFieldWithType(`${f.name}_right`, f.type) : { ...f })
      }
      return merged
    }

    case 'formula': {
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      const upstream = await getOutputFieldsWithTypesForNode(nodes, edges, sources[0])
      return getFormulaOutputFieldsWithTypes(config, upstream)
    }

    case 'pythonScript': {
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      const upstream = await getOutputFieldsWithTypesForNode(nodes, edges, sources[0])
      return getPythonScriptOutputFieldsWithTypes(config, upstream)
    }

    default:
      return []
  }
}

export async function getOutputFieldsForNode(nodes, edges, nodeId) {
  const edgesMap = buildEdgesMap(edges)
  const node = getNodeById(nodes, nodeId)
  if (!node) return []

  const config = (node.data || {}).config || {}
  const type = node.type || ''

  switch (type) {
    case 'dataSource':
      return getDataSourceOutputFields(config)

    case 'filter': {
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      return getOutputFieldsForNode(nodes, edges, sources[0])
    }

    case 'aggregation':
      return getAggregationOutputFields(config)

    case 'join': {
      const sources = (edgesMap[nodeId] || []).slice().sort()
      if (sources.length !== 2) return []
      const [leftId, rightId] = sources
      const [leftFields, rightFields] = await Promise.all([
        getOutputFieldsForNode(nodes, edges, leftId),
        getOutputFieldsForNode(nodes, edges, rightId)
      ])
      const leftSet = new Set(leftFields)
      const merged = [...leftFields]
      for (const f of rightFields) {
        merged.push(leftSet.has(f) ? `${f}_right` : f)
      }
      return merged
    }

    case 'formula': {
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      const upstream = await getOutputFieldsForNode(nodes, edges, sources[0])
      const outputField = config.outputField
      if (outputField && !upstream.includes(outputField)) upstream.push(outputField)
      return upstream
    }

    case 'pythonScript': {
      const outputFields = config.outputFields
      if (Array.isArray(outputFields) && outputFields.length > 0) {
        return outputFields.map(f => typeof f === 'object' && f.name ? f.name : String(f))
      }
      const sources = edgesMap[nodeId] || []
      if (sources.length !== 1) return []
      return getOutputFieldsForNode(nodes, edges, sources[0])
    }

    default:
      return []
  }
}

export async function getAvailableFieldsForNode(nodes, edges, nodeId) {
  const reverseAdj = {}
  for (const e of edges || []) {
    if (!reverseAdj[e.target]) reverseAdj[e.target] = []
    reverseAdj[e.target].push(e.source)
  }

  const sources = reverseAdj[nodeId] || []
  if (sources.length === 0) return []

  if (sources.length === 1) {
    return getOutputFieldsWithTypesForNode(nodes, edges, sources[0])
  }

  const allFields = await Promise.all(
    sources.map(srcId => getOutputFieldsWithTypesForNode(nodes, edges, srcId))
  )
  const merged = []
  const seen = new Set()
  for (const fields of allFields) {
    for (const f of fields) {
      if (!seen.has(f.name)) {
        seen.add(f.name)
        merged.push(f)
      }
    }
  }
  return merged
}
