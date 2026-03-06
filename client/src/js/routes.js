export default {
  "BI": {
    "path": "/bi",
    "component": "@/modules/bi_analysis_modern/client/src/MainPage/HomePageBI.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "Dashboards": {
    "path": "/bi/dashboard/",
    "component": "@/modules/bi_analysis_modern/client/src/Dashboards/DashboardListPage.vue",
    "meta": {
      "title": "Дашборды",
      "requiresAuth": true
    }
  },
  "DashboardPage": {
    "path": "/bi/dashboard/:id(\\d+)?",
    "component": "@/modules/bi_analysis_modern/client/src/Dashboards/DashboardPage.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "NewDashboard": {
    "path": "/bi/dashboard/new",
    "component": "@/modules/bi_analysis_modern/client/src/Dashboards/DashboardPage.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "Pipelines": {
    "path": "/bi/pipelines/",
    "component": "@/modules/bi_analysis_modern/client/src/Pipelines/pages/PipelineListPage.vue",
    "meta": {
      "title": "Пайплайны",
      "requiresAuth": true
    }
  },
  "PipelineEditor": {
    "path": "/bi/pipelines/:id(\\d+)",
    "component": "@/modules/bi_analysis_modern/client/src/Pipelines/pages/PipelineEditorPage.vue",
    "meta": {
      "title": "Редактор пайплайна",
      "requiresAuth": true
    }
  },
  "NewPipeline": {
    "path": "/bi/pipelines/new",
    "component": "@/modules/bi_analysis_modern/client/src/Pipelines/pages/PipelineEditorPage.vue",
    "meta": {
      "title": "Новый пайплайн",
      "requiresAuth": true
    }
  },
  "Connections": {
    "path": "/bi/connections/",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/ConnectionsPage.vue",
    "meta": {
      "title": "Подключения",
      "requiresAuth": true
    }
  },
  "NewFile": {
    "path": "/bi/connections/new/file",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/Files/NewFile.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "ClickHouse": {
    "path": "/bi/connections/new/clickhouse",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/ClickHouse.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "MSSQL": {
    "path": "/bi/connections/new/mssql",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/MSSQL.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "PostgreSQL": {
    "path": "/bi/connections/new/postgresql",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/PostgreSQL.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "ConnectionDetail": {
    "path": "/bi/connections/:pk",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/components/db-settings/ConnectionDetail.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "ConnectionFiles": {
    "path": "/bi/connections/:pk/files",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/Files/ConnectionFiles.vue",
    "meta": {
      "requiresAuth": true
    }
  },
  "NewConnection": {
    "path": "/bi/connections/new",
    "component": "@/modules/bi_analysis_modern/client/src/Connections/NewConnection.vue",
    "meta": {
      "requiresAuth": true
    }
  }
}

