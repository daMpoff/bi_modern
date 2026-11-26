import assert from 'node:assert/strict'
import test from 'node:test'
import { buildSimpleChartOption, resolveSimpleChartType } from '../src/Dashboards/Charts/simpleChartOptions.js'

const rows = [
  { quarter: 'Q1', region: 'North', sales: 10 },
  { quarter: 'Q1', region: 'South', sales: 20 },
]
const config = { xField: 'quarter', yFields: ['sales'], colorField: 'region' }

test('simple dashboard charts keep their series and smoothing options', () => {
  for (const type of ['bar', 'line', 'area', 'scatter']) {
    const { series } = buildSimpleChartOption(config, rows, resolveSimpleChartType(type))
    assert.equal(series[0].type, type === 'area' ? 'line' : type)
    assert.deepEqual(series[0].data, [10, 20])
    assert.equal(Boolean(series[0].smooth), ['area', 'line'].includes(type))
    assert.equal(Boolean(series[0].areaStyle), type === 'area')
  }
  assert.equal(resolveSimpleChartType(), 'bar')
  assert.equal(resolveSimpleChartType('unknown'), 'bar')
})

test('pie and doughnut charts aggregate repeated categories with distinct radii', () => {
  for (const type of ['pie', 'doughnut']) {
    const { series } = buildSimpleChartOption(config, rows, resolveSimpleChartType(type))
    assert.equal(series[0].type, 'pie')
    assert.deepEqual(series[0].data, [{ name: 'Q1', value: 30 }])
    assert.deepEqual(series[0].radius, type === 'pie' ? '50%' : ['40%', '65%'])
  }
})

test('heatmap keeps the category axes and values supplied by the block', () => {
  const { xAxis, yAxis, series } = buildSimpleChartOption(config, rows, resolveSimpleChartType('heatmap'))
  assert.deepEqual(xAxis.data, ['Q1'])
  assert.deepEqual(yAxis.data, ['North', 'South'])
  assert.deepEqual(series[0].data, [[0, 0, 10], [0, 1, 20]])
})
