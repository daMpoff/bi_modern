import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import modernRoutes from '../js/routes.js'
import regularRoutes from '../../../bi_analysis/client/js/routes.js'
import { biEndpoints } from '../src/js/endpoints.js'

const root = fileURLToPath(new URL('../../../../', import.meta.url))
const require = createRequire(path.join(root, 'virtual_env/npm/package.json'))
const { createRouter, createMemoryHistory } = require('vue-router')

test('both BI routers keep their own dashboard and connection routes', () => {
  const records = Object.entries({ ...regularRoutes, ...modernRoutes }).map(([name, route]) => ({
    ...route, name, component: {},
  }))
  assert.equal(new Set([...Object.keys(regularRoutes), ...Object.keys(modernRoutes)]).size,
    Object.keys(regularRoutes).length + Object.keys(modernRoutes).length)
  const router = createRouter({ history: createMemoryHistory(), routes: records })
  for (const [url, name] of [
    ['/bi/dashboards/', 'Dashboards'],
    ['/bi-modern/dashboard/', 'DashboardsModern'],
    ['/bi-modern/dashboard/new', 'NewDashboardModern'],
    ['/bi-modern/dashboard/42', 'DashboardPageModern'],
    ['/bi-modern/connections/new', 'NewConnectionModern'],
    ['/bi-modern/connections/new/file', 'NewFileModern'],
    ['/bi-modern/connections/42/files', 'ConnectionFilesModern'],
    ['/bi-modern/pipelines/new', 'NewPipeline'],
    ['/bi-modern/pipelines/42', 'PipelineEditor'],
  ]) assert.equal(router.resolve(url).name, name, url)
})

test('route components exist and every API endpoint belongs to modern', () => {
  for (const route of Object.values(modernRoutes)) {
    assert.ok(existsSync(path.join(root, route.component.replace(/^@\//, ''))), route.component)
  }
  function check(values) {
    for (let value of Object.values(values)) {
      if (typeof value === 'function') value = value(42, 'a/b')
      if (typeof value === 'object') check(value)
      else assert.ok(value.startsWith('bi_analysis_modern/'), value)
    }
  }
  check(biEndpoints)
})

test('modern components use existing API methods and never address the regular BI', () => {
  const client = path.join(root, 'modules/bi_analysis_modern/client')
  function check(directory) {
    for (const item of readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, item.name)
      if (item.isDirectory()) { if (item.name !== 'tests') check(filename); continue }
      if (!/\.(js|vue|scss)$/.test(filename)) continue
      const source = readFileSync(filename, 'utf8')
      assert.doesNotMatch(source, /(?:["'`])\/?bi_analysis\//, filename)
      assert.doesNotMatch(source, /\/src\/core\/bi\//, filename)
      assert.doesNotMatch(source, /apiClient\.(?:upload|getUploadedFiles)\(/, filename)
      if (/endpoints\.bi\./.test(source)) {
        assert.doesNotMatch(source, /from ['"]@\/js\/api\/endpoints/, filename)
      }
    }
  }
  check(client)
  assert.ok(!existsSync(path.join(client, 'src/js/routes.js')), 'only one route discovery entry')
})
