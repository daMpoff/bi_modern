/**
 * Единый реестр типов графиков для пайплайна и дашборда.
 * Изменение набора или подписей типов графика — только здесь.
 */
export const CHART_TYPES = [
  { type: 'line', label: 'Линейный', iconKey: 'TrendingUp', chartType: 'line' },
  { type: 'bar', label: 'Столбчатый', iconKey: 'BarChart3', chartType: 'bar' },
  { type: 'pie', label: 'Круговой', iconKey: 'ChartPie', chartType: 'pie' },
  { type: 'doughnut', label: 'Кольцевой', iconKey: 'ChartPie', chartType: 'doughnut' },
  { type: 'scatter', label: 'Точечный', iconKey: 'Dot', chartType: 'scatter' },
  { type: 'radar', label: 'Радарный', iconKey: 'Activity', chartType: 'radar' },
  { type: 'heatmap', label: 'Тепловая карта', iconKey: 'Grid3x3', chartType: 'heatmap' },
  { type: 'area', label: 'Областной', iconKey: 'TrendingUp', chartType: 'area' },
  { type: 'candlestick', label: 'Свечной', iconKey: 'BarChart3', chartType: 'candlestick' },
  { type: 'gauge', label: 'Измерительный', iconKey: 'Gauge', chartType: 'gauge' },
  { type: 'funnel', label: 'Воронка', iconKey: 'Filter', chartType: 'funnel' },
  { type: 'tree', label: 'Дерево', iconKey: 'Network', chartType: 'tree' },
  { type: 'treemap', label: 'Древовидная карта', iconKey: 'Layers', chartType: 'treemap' },
  { type: 'sunburst', label: 'Солнечная диаграмма', iconKey: 'Sun', chartType: 'sunburst' },
  { type: 'parallel', label: 'Параллельные координаты', iconKey: 'GitBranch', chartType: 'parallel' },
  { type: 'sankey', label: 'Диаграмма Санкей', iconKey: 'GitBranch', chartType: 'sankey' },
  { type: 'graph', label: 'Граф', iconKey: 'Network', chartType: 'graph' },
  { type: 'boxplot', label: 'Ящик с усами', iconKey: 'Package', chartType: 'boxplot' },
  { type: 'map', label: 'Карта', iconKey: 'Map', chartType: 'map' },
  { type: 'lines', label: 'Линии на карте', iconKey: 'Route', chartType: 'lines' },
  { type: 'effectScatter', label: 'Эффект рассеяния', iconKey: 'Sparkles', chartType: 'effectScatter' },
  { type: 'pictorialBar', label: 'Изобразительный бар', iconKey: 'BarChart3', chartType: 'pictorialBar' },
  { type: 'themeRiver', label: 'Река тем', iconKey: 'GitBranch', chartType: 'themeRiver' },
  { type: 'calendar', label: 'Календарь', iconKey: 'Calendar', chartType: 'calendar' }
]
