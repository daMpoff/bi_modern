/**
 * Single registration point for ECharts components used by pipeline/dashboard simple charts
 * (bar, line, pie, scatter, heatmap). Import this module once in components that use buildEchartsOption
 * or VChart with these chart types to avoid duplicate use() calls.
 */
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart, ScatterChart, HeatmapChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  VisualMapComponent,
  DataZoomComponent,
  DataZoomInsideComponent,
  DataZoomSliderComponent
} from 'echarts/components'

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  HeatmapChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  VisualMapComponent,
  DataZoomComponent,
  DataZoomInsideComponent,
  DataZoomSliderComponent
])
