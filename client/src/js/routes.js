export default {
  "BIModern": {
    "path": "/bi-modern",
    "component": "@/modules/bi_analysis_modern/client/src/MainPage/HomePageBI.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "Dashboards": {
    "path": "/bi-modern/dashboard/",
    "component": "@/modules/bi_analysis_modern/client/src/Dashboards/DashboardListPage.vue",
    "meta": {
      "title": "Дашборды",
      "requiresAuth": true
    }
  },
  "DashboardPageModern": {
    "path": "/bi-modern/dashboard/:id(\\d+)?",
    "component": "@/modules/bi_analysis_modern/client/src/Dashboards/DashboardPage.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "NewDashboardModern": {
    "path": "/bi-modern/dashboard/new",
    "component": "@/modules/bi_analysis_modern/client/src/Dashboards/DashboardPage.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "Pipelines": {
    "path": "/bi-modern/pipelines/",
    "component": "@/modules/bi_analysis_modern/client/src/Pipelines/pages/PipelineListPage.vue",
    "meta": {
      "title": "Пайплайны",
      "requiresAuth": true
    }
  },
  "PipelineEditor": {
    "path": "/bi-modern/pipelines/:id(\\d+)",
    "component": "@/modules/bi_analysis_modern/client/src/Pipelines/pages/PipelineEditorPage.vue",
    "meta": {
      "title": "Редактор пайплайна",
      "requiresAuth": true
    }
  },
  "NewPipeline": {
    "path": "/bi-modern/pipelines/new",
    "component": "@/modules/bi_analysis_modern/client/src/Pipelines/pages/PipelineEditorPage.vue",
    "meta": {
      "title": "Новый пайплайн",
      "requiresAuth": true
    }
  },
  "ConnectionsModern": {
    "path": "/bi-modern/connections/",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/ConnectionsPage.vue",
    "meta": {
      "title": "Подключения",
      "requiresAuth": true
    }
  },
  "NewFileModern": {
    "path": "/bi-modern/connections/new/file",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/Files/NewFile.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "ClickHouseModern": {
    "path": "/bi-modern/connections/new/clickhouse",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/ClickHouse.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "MSSQLModern": {
    "path": "/bi-modern/connections/new/mssql",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/MSSQL.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "PostgreSQLModern": {
    "path": "/bi-modern/connections/new/postgresql",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/PostgreSQL.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "ConnectionDetailModern": {
    "path": "/bi-modern/connections/:pk",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/ConnectionDetail.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "ConnectionFilesModern": {
    "path": "/bi-modern/connections/:pk/files",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/Files/ConnectionFiles.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "NewConnectionModern": {
    "path": "/bi-modern/connections/new",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/NewConnection.vue",
    "meta": {
      "requiresAuth": true
    }
  }
}
