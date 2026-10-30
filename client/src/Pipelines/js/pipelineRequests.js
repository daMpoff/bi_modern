/** Ответ исполнения содержит data и метаданные, которые обычный API-клиент разворачивает. */
export async function requestPipelinePayload(apiClient, method, endpoint, payload = {}) {
  const token = apiClient.getAuthToken()
  const config = {
    _needToken: true,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  }
  try {
    const response = method === 'get'
      ? await apiClient.client.get(endpoint, { ...config, params: payload })
      : await apiClient.client.post(endpoint, payload, config)
    return response.data
  } catch (error) {
    apiClient.handleError?.(error)
    throw error
  }
}
