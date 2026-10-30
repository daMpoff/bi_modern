import assert from 'node:assert/strict'
import test from 'node:test'
import { getJoinInputIds, serializeEdge, normalizeGraphEdges } from '../src/Pipelines/js/graphConnections.js'
import { validateConnection } from '../src/Pipelines/js/pipelineValidator.js'
import { requestPipelinePayload } from '../src/Pipelines/js/pipelineRequests.js'

const nodes = [{ id: 'z', type: 'dataSource' }, { id: 'a', type: 'dataSource' }, { id: 'join', type: 'join' }]

test('JOIN ports survive saving and remain independent of ids and edge order', () => {
  const edges = [
    { source: 'a', target: 'join', targetHandle: 'right-target' },
    { source: 'z', target: 'join', targetHandle: 'left-target' },
  ]
  assert.deepEqual(getJoinInputIds(edges.map(serializeEdge), 'join'), ['z', 'a'])
  assert.deepEqual(getJoinInputIds(edges.toReversed(), 'join'), ['z', 'a'])
})

test('legacy graphs acquire explicit ports without changing their join direction', () => {
  const legacy = [{ source: 'z', target: 'join' }, { source: 'a', target: 'join' }]
  const normalized = normalizeGraphEdges(nodes, legacy)
  assert.deepEqual(getJoinInputIds(legacy, 'join'), getJoinInputIds(normalized, 'join'))
  assert.deepEqual(new Set(normalized.map(edge => edge.targetHandle)), new Set(['left-target', 'right-target']))
  assert.equal(legacy[0].targetHandle, undefined)
})

test('connecting two sources to the same join port is rejected', () => {
  const edges = [{ source: 'z', target: 'join', targetHandle: 'left-target' }]
  assert.equal(validateConnection(nodes, edges, { source: 'a', target: 'join', targetHandle: 'left-target' }).valid, false)
  assert.equal(validateConnection(nodes, edges, { source: 'a', target: 'join', targetHandle: 'right-target' }).valid, true)
})

test('execution preserves total row count, columns, errors and result_set_id', async () => {
  const response = { data: [{ x: 1 }], rows_count: 6000, columns: ['x'], result_set_id: 'run-1', error: null }
  let request
  const client = {
    getAuthToken: () => 'test-access-token',
    client: { post: async (...args) => { request = args; return { data: response } } },
  }
  const result = await requestPipelinePayload(client, 'post', 'execute/', { params: { rate: 2 } })
  assert.deepEqual(result, response)
  assert.deepEqual(request[1], { params: { rate: 2 } })
  assert.equal(request[2].headers.Authorization, 'Bearer test-access-token')
  assert.equal(request[2]._needToken, true)
})

test('chart requests preserve chart metadata and use query parameters', async () => {
  const payload = { data: [{ x: 1 }], chart_type: 'line', engine: 'uplot' }
  let request
  const client = {
    getAuthToken: () => '',
    client: { get: async (...args) => { request = args; return { data: payload } } },
  }
  assert.deepEqual(await requestPipelinePayload(client, 'get', 'chart/', { year: 2026 }), payload)
  assert.deepEqual(request[1].params, { year: 2026 })
  assert.deepEqual(request[1].headers, {})
})

test('failed requests retain core error handling and reject', async () => {
  const failure = new Error('save failed')
  let handled
  const client = {
    getAuthToken: () => '',
    handleError: error => { handled = error },
    client: { post: async () => { throw failure } },
  }
  await assert.rejects(requestPipelinePayload(client, 'post', 'execute/'), failure)
  assert.equal(handled, failure)
})
