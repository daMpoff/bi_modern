import { apiClient } from '@/js/api/manager.js'
import { biEndpoints } from '@/modules/bi_analysis_modern/client/src/js/endpoints.js'
import { requestPipelinePayload } from './pipelineRequests.js'

export async function fetchPipelines(options = {}) {
  const params = {}
  if (options.includeDashboardOnly) {
    params.include_dashboard_only = 'true'
  }
  const { data } = await apiClient.get(biEndpoints.bi.pipelineList, params)
  return Array.isArray(data) ? data : (data.results || [])
}

export async function createPipeline(payload) {
  const { data } = await apiClient.post(biEndpoints.bi.pipelineList, payload)
  return data
}

export async function updatePipeline(id, payload) {
  const { data } = await apiClient.patch(biEndpoints.bi.pipelineDetail(id), payload)
  return data
}

export async function deletePipeline(id) {
  return apiClient.delete(biEndpoints.bi.pipelineDetail(id))
}

function normalizeParamKeys(obj) {
  if (!obj || typeof obj !== 'object') return {}
  const out = {}
  for (const [k, v] of Object.entries(obj)) {
    const key = typeof k === 'string' && k.startsWith('$') ? k.slice(1) : k
    out[key] = v
  }
  return out
}

export async function executePipeline(id, params = {}) {
  const normalized = normalizeParamKeys(params)
  return requestPipelinePayload(apiClient, 'post', biEndpoints.bi.pipelineExecute(id), { params: normalized })
}

export async function getExecuteChunk(pipelineId, resultSetId, offset, limit = 5000) {
  const resp = await apiClient.get(biEndpoints.bi.pipelineExecuteChunk(pipelineId), {
    result_set_id: resultSetId, offset, limit
  })
  return resp?.data ?? []
}

export async function previewPipeline(id, params = {}) {
  const normalized = normalizeParamKeys(params)
  return requestPipelinePayload(apiClient, 'post', biEndpoints.bi.pipelinePreview(id), { params: normalized })
}

export async function fetchPipelineCharts(pipelineId) {
  const params = pipelineId ? { pipeline: pipelineId } : {}
  const { data } = await apiClient.get(biEndpoints.bi.pipelineChartList, params)
  return Array.isArray(data) ? data : (data.results || [])
}

export async function fetchPipelineChartDetail(id) {
  const { data } = await apiClient.get(biEndpoints.bi.pipelineChartDetail(id))
  return data
}

export async function fetchPipelineDetail(id) {
  const { data } = await apiClient.get(biEndpoints.bi.pipelineDetail(id))
  return data
}

export async function fetchPipelineFields(pipelineId, params = {}) {
  const normalized = normalizeParamKeys(params)
  const { data } = await apiClient.get(biEndpoints.bi.pipelineFields(pipelineId), normalized)
  return { fields: data?.fields ?? [], error: data?.error }
}

export async function fetchPipelineFieldValues(pipelineId, fieldName, params = {}, limit = 100) {
  const normalized = normalizeParamKeys(params)
  const { data } = await apiClient.get(biEndpoints.bi.pipelineFieldValues(pipelineId, fieldName), {
    ...normalized,
    limit
  })
  return { values: data?.values ?? [], error: data?.error }
}

export async function createPipelineChart(payload) {
  const { data } = await apiClient.post(biEndpoints.bi.pipelineChartList, payload)
  return data
}

export async function savePipelineChart(id, payload) {
  const { data } = await apiClient.patch(biEndpoints.bi.pipelineChartDetail(id), payload)
  return data
}

export async function deletePipelineChart(id) {
  return apiClient.delete(biEndpoints.bi.pipelineChartDetail(id))
}

export async function fetchPipelineChartData(id, params = {}) {
  const normalized = normalizeParamKeys(params)
  const data = await requestPipelinePayload(apiClient, 'get', biEndpoints.bi.pipelineChartData(id), normalized)
  return {
    data: data?.rows || data?.data || (Array.isArray(data) ? data : []),
    chart_config: data?.chart_config || {},
    chart_type: data?.chart_type || 'bar',
    engine: data?.engine || 'echarts',
    name: data?.name || '',
    error: data?.error
  }
}
