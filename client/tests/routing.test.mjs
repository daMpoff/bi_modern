import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import modernRoutes from '../js/routes.js'
import { biEndpoints } from '../src/js/endpoints.js'

const client = fileURLToPath(new URL('../', import.meta.url))
const regularRoutesUrl = new URL('../../../bi_analysis/client/js/routes.js', import.meta.url)
const require = createRequire(import.meta.url)
const routerPath = require.resolve('vue-router', {
  paths: [client, path.resolve(client, '../../../virtual_env/npm')],
})
const { createRouter, createMemoryHistory } = require(routerPath)

const modernPaths = [
  ['/bi-modern/dashboard/', 'DashboardsModern'],
  ['/bi-modern/dashboard/new', 'NewDashboardModern'],
  ['/bi-modern/dashboard/42', 'DashboardPageModern'],
  ['/bi-modern/connections/new', 'NewConnectionModern'],
  ['/bi-modern/connections/new/file', 'NewFileModern'],
  ['/bi-modern/connections/42/files', 'ConnectionFilesModern'],
  ['/bi-modern/pipelines/new', 'NewPipeline'],
  ['/bi-modern/pipelines/42', 'PipelineEditor'],
]

function assertRoutes(routes, expected) {
  const records = Object.entries(routes).map(([name, route]) => ({ ...route, name, component: {} }))
  const router = createRouter({ history: createMemoryHistory(), routes: records })
  for (const [url, name] of expected) assert.equal(router.resolve(url).name, name, url)
}

test('modern dashboard, connection and pipeline URLs resolve', () => {
  assertRoutes(modernRoutes, modernPaths)
})

test('both BI routers keep their own dashboard and connection routes', {
  skip: !existsSync(regularRoutesUrl) && 'Classic BI router is not installed alongside BI Modern',
}, async () => {
  const { default: regularRoutes } = await import(regularRoutesUrl.href)
  const routes = { ...regularRoutes, ...modernRoutes }
  assert.equal(Object.keys(routes).length, Object.keys(regularRoutes).length + Object.keys(modernRoutes).length)
  assertRoutes(routes, [['/bi/dashboards/', 'Dashboards'], ...modernPaths])
})

test('route components exist and every API endpoint belongs to modern', () => {
  for (const route of Object.values(modernRoutes)) {
    const prefix = '@/modules/bi_analysis_modern/client/'
    assert.ok(route.component.startsWith(prefix), route.component)
    assert.ok(existsSync(path.join(client, route.component.slice(prefix.length))), route.component)
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
  function check(directory) {
    for (const item of readdirSync(directory, { withFileTypes: true })) {
      const filename = path.join(directory, item.name)
      if (item.isDirectory()) {
        if (item.name !== 'tests' && item.name !== 'node_modules') check(filename)
        continue
      }
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
