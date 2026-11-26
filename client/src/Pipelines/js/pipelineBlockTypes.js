/**
 * Реестр типов блоков пайплайна.
 * Импортирует из единого реестра blocksRegistry.js.
 */
export {
  CONTEXT_ALL,
  CONTEXT_DASHBOARD,
  CONTEXT_GRAPHS,
  CONTEXT_PIPELINE,
  getBlockTypesForContext,
  getNodeTypesMap,
  getBlockTypeByType,
  getBlockLabel,
  getSingletonTypes
} from '@/modules/bi_analysis_modern/client/src/Graphs/blocksRegistry.js'
