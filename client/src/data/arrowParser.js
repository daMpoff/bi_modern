/**
 * Arrow IPC Parser — decode binary Arrow IPC streams into JS objects.
 *
 * Uses `apache-arrow` for decoding. Falls back to JSON when Arrow is
 * unavailable or the response is not in Arrow format.
 *
 * ## Usage
 *
 * ```js
 * import { fetchArrowOrJson } from '@/modules/bi_analysis_modern/client/src/data/arrowParser.js'
 *
 * const { rows, columns, format } = await fetchArrowOrJson(url, params)
 * ```
 */

const ARROW_MIME = 'application/vnd.apache.arrow.stream'

// ---------------------------------------------------------------------------
// Core decoding
// ---------------------------------------------------------------------------

/**
 * Decode an Arrow IPC buffer into an array of plain objects.
 *
 * @param {ArrayBuffer|Uint8Array} buffer — raw Arrow IPC bytes
 * @returns {Promise<{ rows: Object[], columns: string[] }>}
 */
export async function decodeArrowBuffer(buffer) {
  const { tableFromIPC } = await import('apache-arrow')
  const table = tableFromIPC(buffer)

  const columns = table.schema.fields.map(f => f.name)
  const rows = []

  for (const row of table) {
    const obj = {}
    for (const col of columns) {
      obj[col] = row[col]
    }
    rows.push(obj)
  }

  return { rows, columns }
}

/**
 * Decode Arrow IPC into typed column arrays (more efficient for charts).
 *
 * @param {ArrayBuffer|Uint8Array} buffer
 * @returns {Promise<{ columns: string[], arrays: Record<string, any[]> }>}
 */
export async function decodeArrowColumns(buffer) {
  const { tableFromIPC } = await import('apache-arrow')
  const table = tableFromIPC(buffer)

  const columns = table.schema.fields.map(f => f.name)
  const arrays = {}

  for (const col of columns) {
    const vector = table.getChild(col)
    arrays[col] = vector ? vector.toArray() : []
  }

  return { columns, arrays }
}

// ---------------------------------------------------------------------------
// Fetch with content negotiation
// ---------------------------------------------------------------------------

/**
 * Fetch data from a URL, preferring Arrow IPC format when available,
 * with automatic fallback to JSON.
 *
 * @param {string} url — API endpoint
 * @param {Object} [params] — query parameters
 * @param {Object} [options] — { preferArrow: boolean }
 * @returns {Promise<{ rows: Object[], columns: string[], format: 'arrow'|'json' }>}
 */
export async function fetchArrowOrJson(url, params = {}, options = {}) {
  const { preferArrow = true } = options

  const query = new URLSearchParams(params).toString()
  const fullUrl = query ? `${url}?${query}` : url

  const headers = {}
  if (preferArrow) {
    headers['Accept'] = `${ARROW_MIME}, application/json;q=0.9`
  }

  const response = await fetch(fullUrl, {
    method: 'GET',
    headers,
    credentials: 'include'
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes(ARROW_MIME)) {
    const buffer = await response.arrayBuffer()
    const { rows, columns } = await decodeArrowBuffer(buffer)
    return { rows, columns, format: 'arrow' }
  }

  // Fallback: JSON
  const data = await response.json()
  const rows = Array.isArray(data)
    ? data
    : (Array.isArray(data?.rows) ? data.rows : (Array.isArray(data?.data) ? data.data : []))

  const columns = data?.columns
    || (rows.length > 0 ? Object.keys(rows[0]) : [])

  return { rows, columns, format: 'json' }
}

/**
 * Get raw Arrow IPC buffer from a URL (for loading into DuckDB).
 *
 * @param {string} url
 * @param {Object} [params]
 * @returns {Promise<Uint8Array|null>} — Arrow buffer, or null if JSON response
 */
export async function fetchArrowBuffer(url, params = {}) {
  const query = new URLSearchParams(params).toString()
  const fullUrl = query ? `${url}?${query}` : url

  const response = await fetch(fullUrl, {
    method: 'GET',
    headers: { 'Accept': ARROW_MIME },
    credentials: 'include'
  })

  if (!response.ok) return null

  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes(ARROW_MIME)) return null

  const buffer = await response.arrayBuffer()
  return new Uint8Array(buffer)
}
