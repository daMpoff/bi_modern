/**
 * ECharts option builder with automatic performance optimizations.
 *
 * Features:
 * - `large` mode for datasets > LARGE_THRESHOLD points
 * - `progressive` rendering for datasets > PROGRESSIVE_THRESHOLD
 * - `sampling: 'lttb'` for line/area charts with dense data
 * - Automatic `dataZoom` (slider + inside) for large datasets
 * - Animation disabled for heavy renders
 */

// ---------------------------------------------------------------------------
// Performance thresholds
// ---------------------------------------------------------------------------

/** Above this — enable ECharts `large` mode (GPU-like Canvas batching) */
const LARGE_THRESHOLD = 5000

/** Above this — enable progressive (incremental) rendering */
const PROGRESSIVE_THRESHOLD = 10000

/** Above this — auto-attach dataZoom slider + inside */
const DATAZOOM_THRESHOLD = 1000

/** Target visible points when dataZoom is auto-attached */
const DATAZOOM_VISIBLE_POINTS = 2000

// ---------------------------------------------------------------------------
// Base option
// ---------------------------------------------------------------------------

const ECHARTS_BASE_OPTION = {
  backgroundColor: 'transparent',
  textStyle: { fontFamily: 'inherit', fontSize: 12 }
}

function applyBaseOption(chartOption) {
  return { ...ECHARTS_BASE_OPTION, ...chartOption }
}

// ---------------------------------------------------------------------------
// Performance helpers (exported for use in chart components)
// ---------------------------------------------------------------------------

/**
 * Applies large/progressive/sampling optimizations to series based on data length.
 * @param {Array} series - ECharts series array
 * @param {number} dataLength - total data points
 * @param {string} chartType - chart type string
 * @returns {Array} optimized series
 */
export function applyPerformanceOpts(series, dataLength, chartType) {
  if (dataLength < LARGE_THRESHOLD) return series

  const supportsLarge = ['bar', 'line', 'scatter', 'effectScatter'].includes(chartType)
  const supportsSampling = ['line', 'area'].includes(chartType)

  return series.map(s => {
    const opts = { ...s }

    if (supportsLarge) {
      opts.large = true
      opts.largeThreshold = LARGE_THRESHOLD
    }

    if (dataLength > PROGRESSIVE_THRESHOLD) {
      opts.progressive = 5000
      opts.progressiveThreshold = PROGRESSIVE_THRESHOLD
      opts.animation = false
    }

    if (supportsSampling && dataLength > LARGE_THRESHOLD) {
      opts.sampling = 'lttb'
    }

    // Disable animation for large datasets regardless
    if (dataLength > LARGE_THRESHOLD) {
      opts.animation = false
    }

    return opts
  })
}

/**
 * Builds dataZoom config for large datasets.
 * Returns empty array for small datasets (no zoom needed).
 * @param {number} dataLength - total data points
 * @returns {Array} dataZoom config (slider + inside) or []
 */
export function buildDataZoom(dataLength) {
  if (dataLength < DATAZOOM_THRESHOLD) return []

  // Show last N points by default; user can scroll back
  const visiblePercent = Math.min(100, (DATAZOOM_VISIBLE_POINTS / dataLength) * 100)
  const startPercent = Math.max(0, 100 - visiblePercent)

  return [
    {
      type: 'slider',
      start: startPercent,
      end: 100,
      bottom: 4,
      height: 20,
      borderColor: 'transparent',
      backgroundColor: 'rgba(0,0,0,0.04)',
      fillerColor: 'rgba(59,130,246,0.15)',
      handleSize: '60%',
      textStyle: { fontSize: 10 }
    },
    {
      type: 'inside',
      start: startPercent,
      end: 100,
      zoomOnMouseWheel: true,
      moveOnMouseMove: true
    }
  ]
}

/**
 * Returns animation config based on data length.
 * @param {number} dataLength - total data points
 * @returns {Object} animation options to merge into chart option
 */
export function getAnimationOpts(dataLength) {
  if (dataLength > PROGRESSIVE_THRESHOLD) {
    return { animation: false }
  }
  if (dataLength > LARGE_THRESHOLD) {
    return { animation: false }
  }
  return {
    animation: true,
    animationDuration: 300,
    animationEasing: 'cubicOut'
  }
}

// ---------------------------------------------------------------------------
// Chart type helpers
// ---------------------------------------------------------------------------

/** Types that support dataZoom (have category/value X axis) */
const DATAZOOM_CHART_TYPES = new Set([
  'bar', 'line', 'area', 'scatter', 'candlestick', 'effectScatter'
])

/** Types that don't benefit from large/progressive */
const NO_PERF_CHART_TYPES = new Set([
  'pie', 'doughnut', 'gauge', 'funnel', 'radar', 'tree', 'treemap',
  'sunburst', 'sankey', 'graph', 'themeRiver', 'calendar'
])

/** Max slices for pie/doughnut/funnel before aggregating into "Другое" */
const PIE_MAX_SLICES = 30

// ---------------------------------------------------------------------------
// Main builder
// ---------------------------------------------------------------------------

/**
 * Builds an ECharts option object from pipeline data and chart configuration.
 * Automatically applies performance optimizations based on data size.
 *
 * @param {Array} data - Array of row objects
 * @param {string} chartType - 'bar' | 'line' | 'pie' | 'scatter' | 'heatmap' | ...
 * @param {string} xField - Name of the X-axis / category field
 * @param {string[]} yFields - Names of Y-axis / value fields
 * @param {number|null} [maxRows=null] - Maximum rows for the chart preview; null = no limit
 * @param {Object} [opts={}] - Extra options: colorField (for heatmap = Y axis category)
 * @returns {Object|null} ECharts option or null if insufficient config
 */
export function buildEchartsOption(data, chartType, xField, yFields, maxRows = null, opts = {}) {
  if (!data?.length || !xField || !yFields?.length) return null

  const rows = maxRows != null && maxRows > 0 ? data.slice(0, maxRows) : data
  const dataLength = rows.length

  // --- Pie / Doughnut ---
  if (chartType === 'pie' || chartType === 'doughnut') {
    const yf = yFields[0]

    // Aggregate by xField (sum values per category), then Top-N + "Другое"
    const aggMap = new Map()
    for (const row of rows) {
      const name = String(row[xField] ?? '')
      const val = Number(row[yf]) || 0
      aggMap.set(name, (aggMap.get(name) || 0) + val)
    }
    let pieEntries = Array.from(aggMap, ([name, value]) => ({ name, value }))
    pieEntries.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))

    if (pieEntries.length > PIE_MAX_SLICES) {
      const top = pieEntries.slice(0, PIE_MAX_SLICES)
      const restSum = pieEntries.slice(PIE_MAX_SLICES).reduce((s, e) => s + e.value, 0)
      top.push({ name: `Другое (${pieEntries.length - PIE_MAX_SLICES})`, value: restSum })
      pieEntries = top
    }

    return applyBaseOption({
      ...getAnimationOpts(pieEntries.length),
      tooltip: { trigger: 'item' },
      legend: { bottom: 10, type: pieEntries.length > 10 ? 'scroll' : 'plain' },
      series: [{
        type: 'pie',
        radius: chartType === 'doughnut' ? ['30%', '60%'] : ['30%', '60%'],
        data: pieEntries,
        animation: pieEntries.length < 200
      }]
    })
  }

  // --- Heatmap ---
  if (chartType === 'heatmap') {
    const yCategoryField = opts.colorField || opts.yCategoryField
    if (!yCategoryField || !yFields.length) return null
    let valueField = yFields.find(f => f !== xField && f !== yCategoryField) || yFields[0]
    if (valueField === xField || valueField === yCategoryField) {
      const firstRow = rows[0]
      if (firstRow && typeof firstRow === 'object') {
        const numericKey = Object.keys(firstRow).find(
          k => k !== xField && k !== yCategoryField && Number.isFinite(Number(firstRow[k]))
        )
        if (numericKey) valueField = numericKey
      }
    }
    const xCategories = [...new Set(rows.map(row => String(row[xField] ?? '')))].filter(Boolean)
    const yCategories = [...new Set(rows.map(row => String(row[yCategoryField] ?? '')))].filter(Boolean)
    const xIndex = Object.fromEntries(xCategories.map((c, i) => [c, i]))
    const yIndex = Object.fromEntries(yCategories.map((c, i) => [c, i]))
    const heatmapData = rows.map(row => {
      const xVal = String(row[xField] ?? '')
      const yVal = String(row[yCategoryField] ?? '')
      const xi = xIndex[xVal]
      const yi = yIndex[yVal]
      if (xi === undefined || yi === undefined) return null
      const v = Number(row[valueField])
      return [xi, yi, Number.isFinite(v) ? v : 0]
    }).filter(Boolean)
    const values = heatmapData.map(d => d[2])
    const minVal = values.length ? Math.min(...values) : 0
    let maxVal = values.length ? Math.max(...values) : 100
    if (maxVal <= minVal) maxVal = minVal + 1

    const heatmapSeries = [{
      type: 'heatmap',
      data: heatmapData,
      large: dataLength > LARGE_THRESHOLD,
      progressive: dataLength > PROGRESSIVE_THRESHOLD ? 5000 : 0,
      itemStyle: { borderWidth: 0 },
      label: { show: false },
      emphasis: {
        itemStyle: { borderWidth: 1, borderColor: '#1e3a5f', shadowBlur: 4, shadowColor: 'rgba(0,0,0,0.2)' },
        label: { show: true, color: '#fff', fontSize: 11 }
      }
    }]

    return applyBaseOption({
      ...getAnimationOpts(dataLength),
      tooltip: {
        position: 'top',
        formatter: (params) => {
          const [xi, yi, v] = params.value
          const xLabel = xCategories[xi] ?? ''
          const yLabel = yCategories[yi] ?? ''
          return `${yLabel} / ${xLabel}: ${v}`
        }
      },
      grid: { left: '3%', right: '4%', bottom: '12%', top: '6%', containLabel: true },
      xAxis: {
        type: 'category',
        data: xCategories,
        splitArea: { show: false }
      },
      yAxis: {
        type: 'category',
        data: yCategories,
        splitArea: { show: false }
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        show: true,
        calculable: true,
        orient: 'horizontal',
        left: 'center',
        bottom: '2%',
        inRange: { color: ['#f0f9ff', '#0ea5e9', '#0369a1'] },
        textStyle: { fontSize: 11 }
      },
      series: heatmapSeries
    })
  }

  // --- Standard XY charts (bar, line, scatter, area, candlestick, etc.) ---
  const effectiveType = chartType === 'area' ? 'line' : chartType
  const xData = rows.map(row => String(row[xField] ?? ''))

  let series = yFields.map(yf => {
    const s = {
      name: yf,
      type: effectiveType === 'scatter' ? 'scatter' : effectiveType,
      data: rows.map(row => Number(row[yf]) || 0)
    }
    // Area style for area charts
    if (chartType === 'area') {
      s.areaStyle = {}
    }
    return s
  })

  // Apply performance optimizations
  if (!NO_PERF_CHART_TYPES.has(chartType)) {
    series = applyPerformanceOpts(series, dataLength, effectiveType)
  }

  // Build dataZoom for supported types
  const dataZoom = DATAZOOM_CHART_TYPES.has(chartType) ? buildDataZoom(dataLength) : []

  // Adjust grid bottom when dataZoom slider is present
  const hasSlider = dataZoom.length > 0
  const gridBottom = hasSlider ? '20%' : '15%'

  return applyBaseOption({
    ...getAnimationOpts(dataLength),
    tooltip: { trigger: chartType === 'scatter' ? 'item' : 'axis' },
    legend: { bottom: hasSlider ? 30 : 10 },
    grid: { left: '3%', right: '4%', bottom: gridBottom, containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: chartType !== 'line' && chartType !== 'area'
    },
    yAxis: { type: 'value' },
    dataZoom,
    series
  })
}
