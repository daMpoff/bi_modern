/**
 * Worker Pool Manager for BI data processing.
 *
 * - Pool of Web Workers (sized by navigator.hardwareConcurrency, max 4)
 * - Promise-based API
 * - Automatic fallback to main-thread when Workers unavailable
 */

const MAX_WORKERS = 4
const TIMEOUT_MS = 30_000

let pool = null
let nextId = 1

// ---------------------------------------------------------------------------
// Worker pool initialisation (lazy)
// ---------------------------------------------------------------------------

function getPool() {
  if (pool) return pool

  const size = Math.min(navigator.hardwareConcurrency || 2, MAX_WORKERS)
  pool = []

  for (let i = 0; i < size; i++) {
    try {
      const w = new Worker(
        new URL('./dataProcessor.worker.js', import.meta.url),
        { type: 'module' }
      )
      const pending = new Map()

      w.onmessage = (e) => {
        const { id, result, error } = e.data || {}
        const p = pending.get(id)
        if (!p) return
        pending.delete(id)
        clearTimeout(p.timer)
        if (error) p.reject(new Error(error))
        else p.resolve(result)
      }

      w.onerror = (err) => {
        // Reject all pending requests for this worker
        for (const [, p] of pending) {
          clearTimeout(p.timer)
          p.reject(err)
        }
        pending.clear()
      }

      pool.push({ worker: w, pending, busy: false })
    } catch {
      // Workers not supported — fall back to main thread
      break
    }
  }

  return pool
}

// Pick the least-busy worker (round-robin / smallest pending queue)
function pickWorker() {
  const p = getPool()
  if (!p.length) return null
  let best = p[0]
  for (const w of p) {
    if (w.pending.size < best.pending.size) best = w
  }
  return best
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Execute an action in a Web Worker.
 *
 * @param {string} action — handler name registered in the worker
 * @param {Object} payload — serialisable data
 * @param {number} [timeout] — timeout in ms (default 30 s)
 * @returns {Promise<any>}
 */
export function workerExec(action, payload, timeout = TIMEOUT_MS) {
  const w = pickWorker()
  if (!w) {
    // Fallback: run inline (best effort)
    return Promise.resolve(null)
  }

  const id = nextId++
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      w.pending.delete(id)
      reject(new Error(`Worker timeout (${action})`))
    }, timeout)

    w.pending.set(id, { resolve, reject, timer })
    w.worker.postMessage({ id, action, payload })
  })
}

/**
 * Convenience: process chart data in a worker.
 */
export async function processChartData(rawData, chartType, config) {
  if (!rawData?.length) return null

  const xField = config?.xField || ''
  const yFields = config?.yFields || []

  const isPie = chartType === 'pie' || chartType === 'doughnut'
  const action = isPie ? 'transformForPie' : 'transformForXY'
  const payload = isPie
    ? { rows: rawData, xField, yFields }
    : { rows: rawData, xField, yFields, seriesType: chartType || 'bar' }

  return workerExec(action, payload)
}

/**
 * Terminate all workers and release resources.
 */
export function terminateWorkers() {
  if (!pool) return
  for (const w of pool) {
    for (const [, p] of w.pending) {
      clearTimeout(p.timer)
      p.reject(new Error('Worker terminated'))
    }
    w.pending.clear()
    w.worker.terminate()
  }
  pool = null
}

/**
 * Check if workers are available.
 */
export function workersAvailable() {
  return getPool().length > 0
}
