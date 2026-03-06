export function getConnectionType(conn) {
  if (!conn) return ''
  return conn.connector_type_display || conn.connector_type || ''
}

export function isFileConnection(connectionType) {
  const type = (connectionType || '').toLowerCase().trim()
  return type.includes('file') || type.includes('файл')
}

export function getConnectionTypeLabel(connectionType) {
  const type = (connectionType || '').toLowerCase().trim()
  if (type.includes('clickhouse')) return 'ClickHouse'
  if (type.includes('postgres')) return 'PostgreSQL'
  if (type.includes('mssql') || type.includes('sql server')) return 'MS SQL Server'
  if (type.includes('file') || type.includes('файл')) return 'Файлы'
  return connectionType || 'Неизвестно'
}
