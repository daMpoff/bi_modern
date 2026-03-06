export function getSourceItemKey(item) {
  if (!item) return ''
  return item.id || item.file_id || item.file_upload_id || `${item.schema || ''}.${item.name || item.table || ''}`
}

export function getSourceItemDisplayName(item) {
  if (!item) return ''
  return item.name || item.table || item.original_filename || 'Без имени'
}
