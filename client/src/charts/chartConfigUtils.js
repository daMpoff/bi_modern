/**
 * Resolves chart config from any block / chart config format.
 * Handles both top-level fields (xField, yFields) and nested chartConfig / chart_config,
 * as well as snake_case (chart_type) vs camelCase (chartType) naming.
 * Returns a consistent camelCase object.
 */
export function resolveBlockChartConfig(blockConfig) {
  const c = blockConfig || {}
  const inner = c.chartConfig || c.chart_config || {}
  return {
    chartType: c.chartType || inner.chartType || c.chart_type || 'bar',
    xField: c.xField || inner.xField || null,
    yFields: c.yFields || inner.yFields || null,
    colorField: c.colorField || inner.colorField || null,
    title: c.title || c.name || null,
  }
}

/**
 * Нормализация конфига графика к формату buildEchartsOption и компонентов:
 * xField — строка, yFields — массив строк, colorField — строка (для heatmap = ось Y).
 */
export function normalizeChartConfig(config) {
  if (!config || typeof config !== 'object') {
    return { xField: '', yFields: [], colorField: '' }
  }
  const xRaw = config.xField
  const xField = typeof xRaw === 'object' && xRaw != null && typeof xRaw.name === 'string'
    ? xRaw.name
    : (typeof xRaw === 'string' ? xRaw : '')
  const yRaw = config.yFields || config.fields
  let yFields = []
  if (Array.isArray(yRaw)) {
    yFields = yRaw.map(f => {
      if (typeof f === 'string') return f
      if (typeof f === 'object' && f != null && typeof f.name === 'string') return f.name
      return ''
    }).filter(Boolean)
  } else if (typeof yRaw === 'string' && yRaw) {
    yFields = [yRaw]
  }
  const colorRaw = config.colorField
  const colorField = typeof colorRaw === 'string' ? colorRaw : ''
  return { xField, yFields, colorField }
}
