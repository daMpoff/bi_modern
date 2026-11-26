import { Plug, Workflow, PanelsTopLeft } from 'lucide-vue-next'

export const sections = [
  { name: 'Подключения', to: '/bi-modern/connections/', description: 'Базы данных и файлы', icon: Plug },
  { name: 'Данные', to: '/bi-modern/pipelines/', description: 'Конвейеры обработки и графики', icon: Workflow },
  { name: 'Дашборды', to: '/bi-modern/dashboard/', description: 'Отчёты и визуализации', icon: PanelsTopLeft }
]
