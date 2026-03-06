import { endpoints } from '@/js/api/endpoints.js'

export class ConnectionDTO {
  constructor({ id, name, connector_type_display, created_at, config, owner }) {
    this.id = id
    this.name = name || '—'
    this.connector_type_display = connector_type_display || '—'
    this.created_at = created_at
    this.config = config
    this.owner = owner
    this.type = 'connection'
  }
}

export class DashboardDTO {
  constructor({ id, name, owner_username, created_at, description, charts_count }) {
    this.id = id
    this.name = name
    this.owner_username = owner_username
    this.created_at = created_at
    this.description = description
    this.charts_count = charts_count
  }
}

export const listConfigs = {
  connections: {
    type: 'connections',
    endpoint: endpoints.bi.ConnectionsList,
    createRoute: '/bi/connections/new',
    createButtonText: 'Создать подключение',
    createButtonWidth: '15.0rem',
    searchPlaceholder: 'Поиск...',
    mapData: (item) => new ConnectionDTO({
      id: item.id,
      name: item.name,
      connector_type_display: item.connector_type_display || item.connector_type,
      created_at: item.created_at,
      config: item.config,
      owner: item.owner
    }),
    filterFunction: (term) => (item) =>
      item.name?.toLowerCase().includes(term) ||
      item.connector_type_display?.toLowerCase().includes(term)
  },

  dashboards: {
    type: 'dashboards',
    endpoint: endpoints.bi.DashboardList,
    createRoute: '/bi/dashboard/new',
    createButtonText: 'Создать дашборд',
    createButtonWidth: '11rem',
    searchPlaceholder: 'Введите для поиска...',
    mapData: (item) => new DashboardDTO({
      id: item.id,
      name: item.name,
      owner_username: item.owner_username,
      created_at: item.created_at,
      description: item.description,
      charts_count: item.charts_count
    }),
    filterFunction: (term) => (item) =>
      item.name?.toLowerCase().includes(term) ||
      item.owner_username?.toLowerCase().includes(term)
  }
}

export function getListConfig(type) {
  return listConfigs[type]
}
