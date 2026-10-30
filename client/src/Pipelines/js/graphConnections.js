/** Порты JOIN сохраняются вместе с графом; старые графы сохраняют прежний порядок. */
export function getJoinInputIds(edges, nodeId) {
  const incoming = (edges || []).filter(edge => edge.target === nodeId)
  if (incoming.length !== 2) return []
  const explicit = incoming.filter(edge => ['left-target', 'right-target'].includes(edge.targetHandle))
  if (!explicit.length) return incoming.map(edge => edge.source).sort()
  const slots = {}
  for (const edge of explicit) {
    if (slots[edge.targetHandle] !== undefined) return []
    slots[edge.targetHandle] = edge.source
  }
  for (const edge of incoming.filter(edge => !explicit.includes(edge))) {
    slots[slots['left-target'] === undefined ? 'left-target' : 'right-target'] = edge.source
  }
  return [slots['left-target'], slots['right-target']]
}

export function serializeEdge(edge) {
  return {
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle ?? null,
    targetHandle: edge.targetHandle ?? null,
    type: edge.type || 'smoothstep',
    animated: edge.animated ?? true,
  }
}

export function normalizeGraphEdges(nodes, edges) {
  const normalized = (edges || []).map(serializeEdge)
  for (const node of nodes || []) {
    if (node.type !== 'join') continue
    const ids = getJoinInputIds(normalized, node.id)
    if (ids.length !== 2) continue
    const incoming = normalized.filter(edge => edge.target === node.id)
    if (incoming.every(edge => !edge.targetHandle)) {
      incoming.sort((a, b) => a.source < b.source ? -1 : a.source > b.source ? 1 : 0)
      incoming[0].targetHandle = 'left-target'
      incoming[1].targetHandle = 'right-target'
    } else {
      for (const edge of incoming) {
        if (!edge.targetHandle) {
          edge.targetHandle = incoming.some(item => item.targetHandle === 'left-target')
            ? 'right-target' : 'left-target'
        }
      }
    }
  }
  return normalized
}
