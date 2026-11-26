import { normalizeChartConfig } from '../../charts/chartConfigUtils.js'
import {
  buildEchartsOption,
  applyPerformanceOpts,
  buildDataZoom,
  getAnimationOpts
} from '../../charts/buildEchartsOption.js'

const SYNTHETIC_CATEGORIES = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн']
const SYNTHETIC_VALUES = [45, 52, 38, 67, 55, 72]

const SIMPLE_CHART_LABELS = {
  bar: 'Столбчатый график',
  line: 'Линейный график',
  area: 'Областной график',
  scatter: 'Точечный график',
  pie: 'Круговой график',
  doughnut: 'Кольцевой график',
  heatmap: 'Тепловая карта'
}

/**
 * Transforms array of row objects into { categories, series, legendData }
 * for standard XY chart types (bar, line, area).
 */
function rawDataToXY(raw, xField, yFields, seriesType, seriesExtra = {}) {
  if (!raw?.length) return null
  const keys = Object.keys(raw[0] || {})
  if (!keys.length) return null

  const firstKey = (xField && keys.includes(xField)) ? xField : keys[0]
  let valueKeys = Array.isArray(yFields) && yFields.length
    ? yFields.filter(f => keys.includes(f))
    : keys.filter(k => k !== firstKey)
  if (!valueKeys.length) valueKeys = keys.filter(k => k !== firstKey)

  const seriesNames = valueKeys.length ? valueKeys : [firstKey]
  const categories = raw.map(r => String(r[firstKey] ?? ''))

  const series = seriesNames.map(name => ({
    name: String(name),
    type: seriesType,
    data: raw.map(r => {
      const v = r[name]
      return typeof v === 'number' && !Number.isNaN(v) ? v : Number(v) || 0
    }),
    ...seriesExtra
  }))

  return { categories, series, legendData: seriesNames }
}

/** Max slices for pie/doughnut before aggregating into "Другое" */
const PIE_MAX_SLICES = 30

/**
 * Transforms array of row objects into pie/doughnut data.
 * Aggregates duplicate categories and limits to top N slices.
 */
function rawDataToPie(raw, xField, yFields) {
  if (!raw?.length) return null
  const keys = Object.keys(raw[0] || {})
  if (!keys.length) return null

  const nameKey = (xField && keys.includes(xField)) ? xField : keys[0]
  const valueKey = (Array.isArray(yFields) && yFields.length && keys.includes(yFields[0]))
    ? yFields[0]
    : (keys.find(k => k !== nameKey) || nameKey)

  // Aggregate by name (sum values per category)
  const aggMap = new Map()
  for (const r of raw) {
    const name = String(r[nameKey] ?? '')
    const v = r[valueKey]
    const num = typeof v === 'number' && !Number.isNaN(v) ? v : Number(v) || 0
    aggMap.set(name, (aggMap.get(name) || 0) + num)
  }

  let entries = Array.from(aggMap, ([name, value]) => ({ name, value }))
  entries.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

  // Top-N with "Другое"
  if (entries.length > PIE_MAX_SLICES) {
    const top = entries.slice(0, PIE_MAX_SLICES)
    const restSum = entries.slice(PIE_MAX_SLICES).reduce((s, e) => s + e.value, 0)
    top.push({ name: `Другое (${entries.length - PIE_MAX_SLICES})`, value: restSum })
    entries = top
  }

  return entries
}

export function resolveSimpleChartType(type) {
  return Object.hasOwn(SIMPLE_CHART_LABELS, type) ? type : 'bar'
}

export function buildSimpleChartOption(config, chartData, type) {
  const { xField, yFields, colorField } = normalizeChartConfig(config)
  const title = {
    text: config.title || config.name || SIMPLE_CHART_LABELS[type],
    left: 'center',
    textStyle: { fontSize: 14, fontWeight: 'bold' }
  }

  // --- Heatmap: delegate to buildEchartsOption ---
  if (type === 'heatmap') {
    const fromApi = chartData?.length && xField && colorField && yFields?.length
      ? buildEchartsOption(chartData, 'heatmap', xField, yFields, null, { colorField })
      : null

    if (fromApi) return { ...fromApi, title }

    const heatmapSyntheticY = ['A', 'B', 'C', 'D', 'E', 'F']
    const heatmapSyntheticData = heatmapSyntheticY.flatMap((y) =>
      SYNTHETIC_CATEGORIES.map((x) => ({ x, y, value: Math.round(Math.random() * 100) }))
    )
    const fallback = buildEchartsOption(heatmapSyntheticData, 'heatmap', 'x', ['value'], null, { colorField: 'y' })
    return { ...fallback, title }
  }

  // --- Pie / Doughnut ---
  if (type === 'pie' || type === 'doughnut') {
    const syntheticPie = SYNTHETIC_CATEGORIES.map((name, i) => ({
      value: SYNTHETIC_VALUES[i],
      name
    }))
    const data = chartData?.length
      ? rawDataToPie(chartData, xField || undefined, yFields.length ? yFields : undefined)
      : syntheticPie

    const sliceCount = data?.length || 0
    return {
      ...getAnimationOpts(sliceCount),
      backgroundColor: 'transparent',
      textStyle: { fontFamily: 'inherit', fontSize: 12 },
      title,
      tooltip: { trigger: 'item', formatter: '{a} <br/>{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left', bottom: 0, type: sliceCount > 10 ? 'scroll' : 'plain' },
      series: [{
        name: 'Значения',
        type: 'pie',
        radius: type === 'doughnut' ? ['40%', '65%'] : '50%',
        data,
        animation: sliceCount < 200,
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
        }
      }]
    }
  }

  // --- Standard XY charts (bar, line, area, scatter) ---
  const effectiveSeriesType = type === 'area' ? 'line' : type
  const extra = {}
  if (effectiveSeriesType === 'line') extra.smooth = true
  if (type === 'area') extra.areaStyle = {}

  const fromApi = chartData?.length
    ? rawDataToXY(
      chartData,
      xField || undefined,
      yFields.length ? yFields : undefined,
      effectiveSeriesType,
      extra
    )
    : null

  const categories = fromApi?.categories ?? SYNTHETIC_CATEGORIES
  const rawSeries = fromApi?.series ?? [{
    name: 'Значения',
    type: effectiveSeriesType,
    data: SYNTHETIC_VALUES,
    ...extra
  }]
  const legendData = fromApi?.legendData ?? ['Значения']
  const len = categories.length

  // Apply performance optimizations to series
  const series = applyPerformanceOpts(rawSeries, len, effectiveSeriesType)

  // Build dataZoom for large datasets
  const dataZoom = buildDataZoom(len)
  const hasSlider = dataZoom.length > 0

  return {
    ...getAnimationOpts(len),
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'inherit', fontSize: 12 },
    title,
    tooltip: { trigger: type === 'scatter' ? 'item' : 'axis', ...(type === 'bar' ? { axisPointer: { type: 'shadow' } } : {}) },
    legend: { data: legendData, bottom: hasSlider ? 30 : 0 },
    grid: {
      left: '5%',
      right: '5%',
      bottom: hasSlider ? '20%' : '15%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      boundaryGap: type !== 'line' && type !== 'area'
    },
    yAxis: { type: 'value' },
    dataZoom,
    series
  }
}
