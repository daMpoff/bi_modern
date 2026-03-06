/**
 * Real-time WebSocket Client for BI Dashboard updates.
 *
 * Connects to `ws://.../ws/bi/dashboard/{dashboardId}/` and handles:
 *   - data_update  — incremental data push (append / replace / refresh)
 *   - notification  — toast-style messages
 *   - status        — block loading states
 *
 * Features:
 *   - Automatic reconnection with exponential backoff
 *   - Heartbeat (ping/pong) to detect stale connections
 *   - Event-based API: on('data_update', handler)
 *   - Integration with Pinia BI Store
 */

const WS_RECONNECT_BASE = 1000   // 1 second
const WS_RECONNECT_MAX = 30000   // 30 seconds
const WS_HEARTBEAT_MS = 25000    // 25 seconds

export class BiRealtimeClient {
  /**
   * @param {string} dashboardId
   * @param {Object} [options]
   * @param {string} [options.baseUrl] — WebSocket base URL (auto-detected if omitted)
   */
  constructor(dashboardId, options = {}) {
    this.dashboardId = dashboardId
    this.baseUrl = options.baseUrl || this._autoBaseUrl()
    this.ws = null
    this._listeners = {}
    this._reconnectAttempt = 0
    this._reconnectTimer = null
    this._heartbeatTimer = null
    this._closed = false
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /** Open the WebSocket connection. */
  connect() {
    if (this._closed) return
    this._cleanup()

    const url = `${this.baseUrl}/ws/bi/dashboard/${this.dashboardId}/`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this._reconnectAttempt = 0
      this._startHeartbeat()
      this._emit('open')
    }

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        this._handleMessage(msg)
      } catch { /* ignore bad JSON */ }
    }

    this.ws.onclose = (event) => {
      this._stopHeartbeat()
      this._emit('close', event)
      if (!this._closed) this._scheduleReconnect()
    }

    this.ws.onerror = (err) => {
      this._emit('error', err)
    }
  }

  /** Subscribe to updates for specific block IDs. */
  subscribe(blockIds) {
    this._send({ action: 'subscribe', block_ids: blockIds })
  }

  /** Register an event handler. */
  on(event, handler) {
    if (!this._listeners[event]) this._listeners[event] = []
    this._listeners[event].push(handler)
    return this
  }

  /** Remove an event handler. */
  off(event, handler) {
    const list = this._listeners[event]
    if (!list) return
    this._listeners[event] = list.filter(h => h !== handler)
  }

  /** Close the connection permanently. */
  close() {
    this._closed = true
    this._cleanup()
  }

  /** Check if connected. */
  get connected() {
    return this.ws?.readyState === WebSocket.OPEN
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  _handleMessage(msg) {
    const type = msg.type

    if (type === 'pong') return // heartbeat response

    if (type === 'data_update') {
      this._emit('data_update', {
        blockId: msg.block_id,
        action: msg.action,   // 'append' | 'replace' | 'refresh'
        rows: msg.rows || [],
        totalRows: msg.total_rows,
      })
      return
    }

    if (type === 'notification') {
      this._emit('notification', {
        level: msg.level || 'info',
        message: msg.message || '',
      })
      return
    }

    if (type === 'status') {
      this._emit('status', {
        blockId: msg.block_id,
        status: msg.status,
        error: msg.error,
      })
      return
    }

    if (type === 'subscribed') {
      this._emit('subscribed', msg.block_ids)
      return
    }

    // Unknown type — emit as generic message
    this._emit('message', msg)
  }

  _send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  _emit(event, data) {
    const handlers = this._listeners[event]
    if (!handlers) return
    for (const h of handlers) {
      try { h(data) } catch (e) { console.error(`[BiRealtime] handler error (${event}):`, e) }
    }
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this._heartbeatTimer = setInterval(() => {
      this._send({ action: 'ping' })
    }, WS_HEARTBEAT_MS)
  }

  _stopHeartbeat() {
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer)
      this._heartbeatTimer = null
    }
  }

  _scheduleReconnect() {
    if (this._reconnectTimer) return
    const delay = Math.min(
      WS_RECONNECT_BASE * Math.pow(2, this._reconnectAttempt),
      WS_RECONNECT_MAX,
    )
    this._reconnectAttempt++
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null
      this.connect()
    }, delay)
  }

  _cleanup() {
    this._stopHeartbeat()
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer)
      this._reconnectTimer = null
    }
    if (this.ws) {
      this.ws.onopen = null
      this.ws.onmessage = null
      this.ws.onclose = null
      this.ws.onerror = null
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close()
      }
      this.ws = null
    }
  }

  _autoBaseUrl() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    // Use the API host/port from env if available, otherwise same origin
    const apiHost = import.meta.env?.VITE_API_HOST
    const apiPort = import.meta.env?.VITE_API_PORT
    if (apiHost) {
      const host = apiHost.replace(/^https?:\/\//, '')
      return `${proto}://${host}${apiPort ? ':' + apiPort : ''}`
    }
    return `${proto}://${window.location.host}`
  }
}

// ---------------------------------------------------------------------------
// Factory helper
// ---------------------------------------------------------------------------

/**
 * Create and connect a real-time client for a dashboard.
 *
 * @param {string} dashboardId
 * @param {Object} [options]
 * @returns {BiRealtimeClient}
 */
export function createRealtimeClient(dashboardId, options) {
  const client = new BiRealtimeClient(dashboardId, options)
  client.connect()
  return client
}
