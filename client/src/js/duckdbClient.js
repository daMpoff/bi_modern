import { logError } from '@/js/utils/logError.js'
/**
 * DuckDB-WASM Client Manager for Client-Side OLAP.
 *
 * Provides:
 * - Lazy initialization of DuckDB-WASM instance
 * - Loading JSON/Arrow data into DuckDB tables
 * - SQL query execution for aggregation and filtering
 * - Cross-filtering API for dashboard interactions
 *
 * The WASM binary is loaded lazily (~4 MB) on first use, so dashboards
 * that never need client-side OLAP pay no startup cost.
 */

let db = null
let conn = null
let initPromise = null

// ---------------------------------------------------------------------------
// Lazy initialization
// ---------------------------------------------------------------------------

async function init() {
  if (db) return
  if (initPromise) return initPromise

  initPromise = (async () => {
    try {
      const duckdb = await import('@duckdb/duckdb-wasm')

      // Pick the best bundle for this browser
      const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles()
      const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES)

      const worker = new Worker(bundle.mainWorker)
      const logger = new duckdb.ConsoleLogger()

      db = new duckdb.AsyncDuckDB(logger, worker)
      await db.instantiate(bundle.mainModule, bundle.pthreadWorker)

      conn = await db.connect()
    } catch (err) {
      logError('[BiDuckDB] Initialization failed:', err)
      db = null
      conn = null
      throw err
    } finally {
      initPromise = null
    }
  })()

  return initPromise
}

// ---------------------------------------------------------------------------
// Table management
// ---------------------------------------------------------------------------

/**
 * Load a JSON array of objects into a DuckDB table.
 *
 * @param {string} tableId — unique table name (e.g. `block_123`)
 * @param {Array<Object>} rows — data rows
 */
export async function loadDataset(tableId, rows) {
  if (!rows?.length) return
  await init()

  const safeName = sanitize(tableId)

  // Use DuckDB's JSON import via INSERT
  await conn.query(`DROP TABLE IF EXISTS ${safeName}`)

  // Create table from first batch using CREATE TABLE AS
  const jsonStr = JSON.stringify(rows)
  await db.registerFileText(`${safeName}.json`, jsonStr)
  await conn.query(`CREATE TABLE ${safeName} AS SELECT * FROM read_json_auto('${safeName}.json')`)
}

/**
 * Load an Arrow IPC buffer into a DuckDB table.
 *
 * @param {string} tableId
 * @param {Uint8Array|ArrayBuffer} arrowBuffer
 */
export async function loadArrowDataset(tableId, arrowBuffer) {
  await init()
  const safeName = sanitize(tableId)
  await conn.query(`DROP TABLE IF EXISTS ${safeName}`)

  const buf = arrowBuffer instanceof Uint8Array ? arrowBuffer : new Uint8Array(arrowBuffer)
  await db.registerFileBuffer(`${safeName}.arrow`, buf)
  await conn.query(`CREATE TABLE ${safeName} AS SELECT * FROM '${safeName}.arrow'`)
}

/**
 * Drop a table.
 */
export async function dropDataset(tableId) {
  if (!conn) return
  const safeName = sanitize(tableId)
  try {
    await conn.query(`DROP TABLE IF EXISTS ${safeName}`)
  } catch { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Querying
// ---------------------------------------------------------------------------

/**
 * Execute an arbitrary SQL query and return results as Array<Object>.
 *
 * @param {string} sql
 * @returns {Promise<Array<Object>>}
 */
export async function query(sql) {
  await init()
  const result = await conn.query(sql)
  return arrowTableToObjects(result)
}

/**
 * Apply cross-filters and return filtered rows for a given table.
 *
 * @param {string} tableId — the target table
 * @param {Object} filters — { [field]: values[] }
 * @param {string} [exceptSource] — table id to exclude from filtering (self)
 * @returns {Promise<Array<Object>>}
 */
export async function crossFilter(tableId, filters, exceptSource = null) {
  await init()
  const safeName = sanitize(tableId)

  const whereClauses = []
  for (const [field, values] of Object.entries(filters || {})) {
    if (exceptSource && field === exceptSource) continue
    if (!Array.isArray(values) || !values.length) continue
    const escaped = values.map(v => `'${String(v).replace(/'/g, "''")}'`).join(',')
    whereClauses.push(`"${field}" IN (${escaped})`)
  }

  const where = whereClauses.length ? ` WHERE ${whereClauses.join(' AND ')}` : ''
  const sql = `SELECT * FROM ${safeName}${where}`
  return query(sql)
}

/**
 * Get row count for a table.
 */
export async function tableRowCount(tableId) {
  const safeName = sanitize(tableId)
  const rows = await query(`SELECT COUNT(*) AS cnt FROM ${safeName}`)
  return rows[0]?.cnt ?? 0
}

/**
 * Get column names for a table.
 */
export async function tableColumns(tableId) {
  const safeName = sanitize(tableId)
  const rows = await query(`SELECT column_name FROM information_schema.columns WHERE table_name = '${safeName}'`)
  return rows.map(r => r.column_name)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sanitize(name) {
  return String(name).replace(/[^a-zA-Z0-9_]/g, '_')
}

function arrowTableToObjects(arrowTable) {
  if (!arrowTable) return []
  try {
    return arrowTable.toArray().map(row => {
      if (typeof row.toJSON === 'function') return row.toJSON()
      const obj = {}
      for (const field of arrowTable.schema.fields) {
        obj[field.name] = row[field.name]
      }
      return obj
    })
  } catch {
    return []
  }
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

/**
 * Close the connection and terminate the DuckDB instance.
 */
export async function terminate() {
  try {
    if (conn) { await conn.close(); conn = null }
    if (db) { await db.terminate(); db = null }
  } catch { /* best effort */ }
}

/**
 * Check if DuckDB is initialized.
 */
export function isReady() {
  return db !== null && conn !== null
}
