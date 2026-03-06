/**
 * Universal composable for chart components.
 *
 * Provides a computed `chartOption` that:
 * - Extracts xField/yFields from block config
 * - Transforms raw API data (Array<Object>) into ECharts series
 * - Falls back to synthetic demo data when no chartData is provided
 * - Automatically applies performance optimizations (large, progressive, dataZoom, sampling)
 *
 * Usage in a chart component:
 *   const { chartOption, dataLength } = useChartData(props, 'bar')
 *   // or with extra series options:
 *   const { chartOption } = useChartData(props, 'line', { smooth: true })
 */
import { computed } from 'vue'
import { normalizeChartConfig } from '@/modules/bi_analysis_modern/client/src/js/chartConfigUtils.js'
import {
  buildEchartsOption,
  applyPerformanceOpts,
  buildDataZoom,
  getAnimationOpts
} from '@/modules/bi_analysis_modern/client/src/js/buildEchartsOption.js'

// ---------------------------------------------------------------------------
// Synthetic (demo) data per chart type
// ---------------------------------------------------------------------------

const SYNTHETIC_CATEGORIES = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн']
const SYNTHETIC_VALUES = [45, 52, 38, 67, 55, 72]

const CHART_TYPE_LABELS = {
  bar: 'Столбчатый график',
  line: 'Линейный график',
  area: 'Областной график',
  scatter: 'Точечный график',
  pie: 'Круговой график',
  doughnut: 'Кольцевой график',
  heatmap: 'Тепловая карта',
  radar: 'Радарный график',
  gauge: 'Измерительный график',
  funnel: 'Воронка',
  candlestick: 'Свечной график',
  treemap: 'Карта дерева',
  tree: 'Дерево',
  sunburst: 'Солнечная диаграмма',
  sankey: 'Диаграмма Санкей',
  graph: 'Граф',
  boxplot: 'Ящик с усами',
  parallel: 'Параллельные координаты',
  map: 'Карта',
  lines: 'Линии на карте',
  effectScatter: 'Эффект-точки',
  pictorialBar: 'Пиктограммы',
  themeRiver: 'Тематическая река',
  calendar: 'Календарь'
}

// ---------------------------------------------------------------------------
// Raw data transformation
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Chart types that support dataZoom
// ---------------------------------------------------------------------------

const DATAZOOM_TYPES = new Set(['bar', 'line', 'area', 'scatter', 'candlestick', 'effectScatter'])

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

/**
 * @param {Object} props - component props with { block, chartData }
 * @param {string} chartType - 'bar' | 'line' | 'area' | 'pie' | 'heatmap' | etc.
 * @param {Object} [seriesOpts={}] - extra options to merge into each series (e.g. { smooth: true, areaStyle: {} })
 * @returns {{ chartOption: ComputedRef<Object|null>, dataLength: ComputedRef<number> }}
 */
export function useChartData(props, chartType, seriesOpts = {}) {
  const dataLength = computed(() => props.chartData?.length ?? 0)

  const chartOption = computed(() => {
    const cfg = props.block?.config || {}
    const { xField, yFields, colorField } = normalizeChartConfig(cfg)
    const title = cfg.title || cfg.name || CHART_TYPE_LABELS[chartType] || 'График'

    // --- Heatmap: delegate to buildEchartsOption ---
    if (chartType === 'heatmap') {
      const heatmapSyntheticY = ['A', 'B', 'C', 'D', 'E', 'F']
      const heatmapSyntheticData = heatmapSyntheticY.flatMap((y) =>
        SYNTHETIC_CATEGORIES.map((x) => ({ x, y, value: Math.round(Math.random() * 100) }))
      )

      const fromApi = props.chartData?.length && xField && colorField && yFields?.length
        ? buildEchartsOption(props.chartData, 'heatmap', xField, yFields, null, { colorField })
        : null

      if (fromApi) {
        return {
          ...fromApi,
          title: { text: title, left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } }
        }
      }
      const fallback = buildEchartsOption(heatmapSyntheticData, 'heatmap', 'x', ['value'], null, { colorField: 'y' })
      return {
        ...fallback,
        title: { text: title, left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } }
      }
    }

    // --- Pie / Doughnut ---
    if (chartType === 'pie' || chartType === 'doughnut') {
      const syntheticPie = SYNTHETIC_CATEGORIES.map((name, i) => ({
        value: SYNTHETIC_VALUES[i],
        name
      }))
      const data = props.chartData?.length
        ? rawDataToPie(props.chartData, xField || undefined, yFields.length ? yFields : undefined)
        : syntheticPie

      const sliceCount = data?.length || 0
      return {
        ...getAnimationOpts(sliceCount),
        backgroundColor: 'transparent',
        textStyle: { fontFamily: 'inherit', fontSize: 12 },
        title: { text: title, left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } },
        tooltip: { trigger: 'item', formatter: '{a} <br/>{b}: {c} ({d}%)' },
        legend: { orient: 'vertical', left: 'left', bottom: 0, type: sliceCount > 10 ? 'scroll' : 'plain' },
        series: [{
          name: 'Значения',
          type: 'pie',
          radius: chartType === 'doughnut' ? ['40%', '65%'] : '50%',
          data,
          animation: sliceCount < 200,
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
          }
        }]
      }
    }

    // --- Standard XY charts (bar, line, area, scatter) ---
    const effectiveSeriesType = chartType === 'area' ? 'line' : (chartType === 'scatter' ? 'scatter' : chartType)
    const extra = { ...seriesOpts }
    if (chartType === 'area') extra.areaStyle = extra.areaStyle || {}

    const fromApi = props.chartData?.length
      ? rawDataToXY(
        props.chartData,
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
    const dataZoom = DATAZOOM_TYPES.has(chartType) ? buildDataZoom(len) : []
    const hasSlider = dataZoom.length > 0

    return {
      ...getAnimationOpts(len),
      backgroundColor: 'transparent',
      textStyle: { fontFamily: 'inherit', fontSize: 12 },
      title: { text: title, left: 'center', textStyle: { fontSize: 14, fontWeight: 'bold' } },
      tooltip: { trigger: chartType === 'scatter' ? 'item' : 'axis', ...(chartType === 'bar' ? { axisPointer: { type: 'shadow' } } : {}) },
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
        boundaryGap: chartType !== 'line' && chartType !== 'area'
      },
      yAxis: { type: 'value' },
      dataZoom,
      series
    }
  })

  return { chartOption, dataLength }
}
