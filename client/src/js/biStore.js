/**
 * Pinia BI Store — centralised state management for dashboards.
 *
 * Provides:
 * - Datasets loaded into memory (keyed by block/chart id)
 * - Active cross-filters from chart interactions
 * - Dashboard params (previously only via provide/inject)
 * - Real-time subscriptions registry
 *
 * This store replaces the provide/inject pattern so that *any* component in
 * the BI module can access shared dashboard state without prop drilling.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useBiStore = defineStore('bi', () => {
  // -----------------------------------------------------------------------
  // Datasets — raw data loaded per block (Map<blockId, Array<Object>>)
  // -----------------------------------------------------------------------
  const datasets = ref(new Map())

  function setDataset(blockId, rows) {
    datasets.value.set(blockId, rows)
  }

  function getDataset(blockId) {
    return datasets.value.get(blockId) ?? null
  }

  function removeDataset(blockId) {
    datasets.value.delete(blockId)
  }

  function clearDatasets() {
    datasets.value.clear()
  }

  // -----------------------------------------------------------------------
  // Cross-filters — { [sourceChartId]: { field, values } }
  // -----------------------------------------------------------------------
  const crossFilters = ref({})

  /**
   * Apply a filter originating from a chart interaction.
   * @param {string|number} sourceChartId
   * @param {{ field: string, values: any[] }} filter
   */
  function applyFilter(sourceChartId, filter) {
    if (!filter || !filter.field) return
    crossFilters.value = { ...crossFilters.value, [sourceChartId]: filter }
  }

  function removeFilter(sourceChartId) {
    const next = { ...crossFilters.value }
    delete next[sourceChartId]
    crossFilters.value = next
  }

  function clearFilters() {
    crossFilters.value = {}
  }

  const hasActiveFilters = computed(() => Object.keys(crossFilters.value).length > 0)

  /**
   * Get filtered rows for a given dataset by applying all cross-filters
   * (except the one originating from the same chart).
   */
  function getFilteredData(blockId) {
    const raw = getDataset(blockId)
    if (!raw) return null
    if (!hasActiveFilters.value) return raw

    return raw.filter(row => {
      for (const [srcId, filter] of Object.entries(crossFilters.value)) {
        if (String(srcId) === String(blockId)) continue // skip self
        const val = String(row[filter.field] ?? '')
        if (Array.isArray(filter.values) && !filter.values.map(String).includes(val)) {
          return false
        }
      }
      return true
    })
  }

  // -----------------------------------------------------------------------
  // Dashboard params (replaces provide/inject 'dashboardParams')
  // -----------------------------------------------------------------------
  const dashboardParams = ref({})

  function updateDashboardParams(patch) {
    if (!patch || typeof patch !== 'object') return
    const next = { ...dashboardParams.value }
    for (const [k, v] of Object.entries(patch)) {
      if (v === undefined || v === null || v === '') delete next[k]
      else next[k] = v
    }
    dashboardParams.value = next
  }

  function setDashboardParams(params) {
    dashboardParams.value = params && typeof params === 'object' ? { ...params } : {}
  }

  // -----------------------------------------------------------------------
  // Real-time subscriptions registry
  // -----------------------------------------------------------------------
  const subscriptions = ref(new Map())

  function addSubscription(key, sub) {
    subscriptions.value.set(key, sub)
  }

  function removeSubscription(key) {
    const sub = subscriptions.value.get(key)
    if (sub && typeof sub.close === 'function') sub.close()
    subscriptions.value.delete(key)
  }

  function clearSubscriptions() {
    for (const [, sub] of subscriptions.value) {
      if (typeof sub.close === 'function') sub.close()
    }
    subscriptions.value.clear()
  }

  // -----------------------------------------------------------------------
  // Current dashboard metadata
  // -----------------------------------------------------------------------
  const currentDashboardId = ref(null)

  function setCurrentDashboard(id) {
    currentDashboardId.value = id
  }

  // -----------------------------------------------------------------------
  // Full reset (e.g. when navigating away from the dashboard page)
  // -----------------------------------------------------------------------
  function $reset() {
    clearDatasets()
    clearFilters()
    clearSubscriptions()
    dashboardParams.value = {}
    currentDashboardId.value = null
  }

  return {
    // Datasets
    datasets,
    setDataset,
    getDataset,
    removeDataset,
    clearDatasets,

    // Cross-filters
    crossFilters,
    applyFilter,
    removeFilter,
    clearFilters,
    hasActiveFilters,
    getFilteredData,

    // Dashboard params
    dashboardParams,
    updateDashboardParams,
    setDashboardParams,

    // Subscriptions
    subscriptions,
    addSubscription,
    removeSubscription,
    clearSubscriptions,

    // Dashboard
    currentDashboardId,
    setCurrentDashboard,

    // Reset
    $reset
  }
})
