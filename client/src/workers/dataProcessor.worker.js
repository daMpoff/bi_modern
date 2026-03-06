/**
 * Web Worker for off-main-thread data processing.
 *
 * Handles:
 * - JSON parsing of large payloads
 * - Data transformation for chart rendering (rawDataToXY, rawDataToPie)
 * - Client-side LTTB downsampling for zoom
 * - Aggregation helpers for cross-filtering
 *
 * Communication: postMessage({ id, action, payload }) / onmessage
 */

// ---------------------------------------------------------------------------
// LTTB Downsampling (client-side)
// ---------------------------------------------------------------------------

function lttbDownsample(xVals, yVals, target) {
  const n = xVals.length
  if (n <= target || target < 3) return { x: xVals, y: yVals }

  const selectedX = [xVals[0]]
  const selectedY = [yVals[0]]
  const bucketSize = (n - 2) / (target - 2)
  let aIdx = 0

  for (let i = 1; i < target - 1; i++) {
    const bucketStart = Math.floor(1 + (i - 1) * bucketSize)
    const bucketEnd = Math.min(Math.floor(1 + i * bucketSize), n - 1)
    const nextStart = Math.floor(1 + i * bucketSize)
    const nextEnd = Math.min(Math.floor(1 + (i + 1) * bucketSize), n)

    let avgX = 0, avgY = 0
    const nextLen = Math.max(1, nextEnd - nextStart)
    for (let j = nextStart; j < nextEnd; j++) {
      avgX += xVals[j]; avgY += yVals[j]
    }
    avgX /= nextLen; avgY /= nextLen

    let maxArea = -1, maxIdx = bucketStart
    const ax = xVals[aIdx], ay = yVals[aIdx]

    for (let j = bucketStart; j <= bucketEnd && j < n; j++) {
      const area = Math.abs((xVals[j] - ax) * (avgY - ay) - (avgX - ax) * (yVals[j] - ay))
      if (area > maxArea) { maxArea = area; maxIdx = j }
    }

    selectedX.push(xVals[maxIdx])
    selectedY.push(yVals[maxIdx])
    aIdx = maxIdx
  }

  selectedX.push(xVals[n - 1])
  selectedY.push(yVals[n - 1])
  return { x: selectedX, y: selectedY }
}

// ---------------------------------------------------------------------------
// Data Transformation
// ---------------------------------------------------------------------------

const PIE_MAX_SLICES = 30

function transformForXY(rows, xField, yFields, seriesType) {
  if (!rows?.length) return null
  const keys = Object.keys(rows[0] || {})
  if (!keys.length) return null

  const firstKey = (xField && keys.includes(xField)) ? xField : keys[0]
  let valueKeys = Array.isArray(yFields) && yFields.length
    ? yFields.filter(f => keys.includes(f))
    : keys.filter(k => k !== firstKey)
  if (!valueKeys.length) valueKeys = keys.filter(k => k !== firstKey)

  const categories = new Array(rows.length)
  for (let i = 0; i < rows.length; i++) categories[i] = String(rows[i][firstKey] ?? '')

  const series = valueKeys.map(name => {
    const data = new Array(rows.length)
    for (let i = 0; i < rows.length; i++) {
      const v = rows[i][name]
      data[i] = typeof v === 'number' && !Number.isNaN(v) ? v : Number(v) || 0
    }
    return { name: String(name), type: seriesType, data }
  })

  return { categories, series, legendData: valueKeys.map(String) }
}

function transformForPie(rows, xField, yFields) {
  if (!rows?.length) return null
  const keys = Object.keys(rows[0] || {})
  if (!keys.length) return null

  const nameKey = (xField && keys.includes(xField)) ? xField : keys[0]
  const valueKey = (Array.isArray(yFields) && yFields.length && keys.includes(yFields[0]))
    ? yFields[0]
    : (keys.find(k => k !== nameKey) || nameKey)

  // Aggregate by name
  const aggMap = new Map()
  for (const r of rows) {
    const name = String(r[nameKey] ?? '')
    const v = r[valueKey]
    const num = typeof v === 'number' && !Number.isNaN(v) ? v : Number(v) || 0
    aggMap.set(name, (aggMap.get(name) || 0) + num)
  }

  let entries = Array.from(aggMap, ([name, value]) => ({ name, value }))
  entries.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

  if (entries.length > PIE_MAX_SLICES) {
    const top = entries.slice(0, PIE_MAX_SLICES)
    const restSum = entries.slice(PIE_MAX_SLICES).reduce((s, e) => s + e.value, 0)
    top.push({ name: `Другое (${entries.length - PIE_MAX_SLICES})`, value: restSum })
    entries = top
  }

  return entries
}

function parseJSON(raw) {
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Aggregation helpers for cross-filtering
// ---------------------------------------------------------------------------

function groupBy(rows, field) {
  const groups = {}
  for (const row of rows) {
    const key = String(row[field] ?? '')
    if (!groups[key]) groups[key] = []
    groups[key].push(row)
  }
  return groups
}

function filterRows(rows, filters) {
  if (!filters || !Object.keys(filters).length) return rows
  return rows.filter(row => {
    for (const [field, values] of Object.entries(filters)) {
      const v = String(row[field] ?? '')
      if (Array.isArray(values) && !values.includes(v)) return false
    }
    return true
  })
}

// ---------------------------------------------------------------------------
// Message handler
// ---------------------------------------------------------------------------

const ACTIONS = {
  transformForXY: ({ rows, xField, yFields, seriesType }) =>
    transformForXY(rows, xField, yFields, seriesType || 'bar'),

  transformForPie: ({ rows, xField, yFields }) =>
    transformForPie(rows, xField, yFields),

  lttbDownsample: ({ xVals, yVals, target }) =>
    lttbDownsample(xVals, yVals, target),

  parseJSON: ({ raw }) =>
    parseJSON(raw),

  groupBy: ({ rows, field }) =>
    groupBy(rows, field),

  filterRows: ({ rows, filters }) =>
    filterRows(rows, filters),

  ping: () => 'pong'
}

self.onmessage = function (e) {
  const { id, action, payload } = e.data || {}
  const handler = ACTIONS[action]
  if (!handler) {
    self.postMessage({ id, error: `Unknown action: ${action}` })
    return
  }
  try {
    const result = handler(payload || {})
    self.postMessage({ id, result })
  } catch (err) {
    self.postMessage({ id, error: String(err?.message || err) })
  }
}
