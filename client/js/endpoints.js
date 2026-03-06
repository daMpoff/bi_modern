// Ключ biModern используется для центрального реестра (EndpointManager),
// чтобы избежать коллизии с core/bi, который использует ключ bi.
// Компоненты импортируют из client/src/js/endpoints.js (с ключом bi).
export const biEndpoints = {
    biModern: {
        ConnectionsList: 'bi_analysis_modern/bi_connections/',
        CheckConnection: 'bi_analysis_modern/bi_connections/check-connection/',
        ChartsList: 'bi_analysis_modern/bi_charts/',
        DashboardList: 'bi_analysis_modern/bi_dashboards/',
        dashboardDetail: id => `bi_analysis_modern/bi_dashboards/${id}/`,
        dashboardItemList: () => 'bi_analysis_modern/bi_dashboards/items/',
        dashboardItemDetail: id => `bi_analysis_modern/bi_dashboards/items/${id}/`,
        dashboardItemData: id => `bi_analysis_modern/bi_dashboards/items/${id}/data/`,
        ChartsColumns: id => `bi_analysis_modern/bi_charts/${id}/columns/`,
        ChartsRows: id => `bi_analysis_modern/bi_charts/${id}/rows/`,
        Upload: 'bi_analysis_modern/bi_datasets/upload/',

        // Connections
        connectionDetail: id => `bi_analysis_modern/bi_connections/${id}/`,
        connectionFiles: id => `bi_analysis_modern/bi_datasets/connection/${id}/files/`,
        connectionTables: id => `bi_analysis_modern/bi_connections/${id}/tables/`,
        connectionTableColumns: id => `bi_analysis_modern/bi_connections/${id}/tables/columns/`,
        connectionTablePreview: id => `bi_analysis_modern/bi_connections/${id}/tables/preview/`,

        // Upload / file operations (connection files)
        uploadFinalize: 'bi_analysis_modern/bi_datasets/upload/finalize/',
        uploadDelete: id => `bi_analysis_modern/bi_datasets/upload/${id}/`,
        xlsxSheets: 'bi_analysis_modern/bi_datasets/xlsx/sheets/',

        // Chart operations
        chart: {
            checkAccess: (chartId) => `bi_analysis_modern/bi_charts/${chartId}/`,
            get: (chartId) => `bi_analysis_modern/bi_charts/${chartId}/`,
        },

        // Data source: единый endpoint колонок (таблица или файл)
        dataSourceColumns: 'bi_analysis_modern/data_source/columns/',
        // Graphs: выполнение пайплайна графа (POST nodes, edges)
        graphExecute: 'bi_analysis_modern/graphs/execute/',
        suggestJoinKeys: 'bi_analysis_modern/graphs/suggest-join-keys/',

        // Pipelines
        pipelineList: 'bi_analysis_modern/pipelines/',
        pipelineDetail: id => `bi_analysis_modern/pipelines/${id}/`,
        pipelineExecute: id => `bi_analysis_modern/pipelines/${id}/execute/`,
        pipelineExecuteChunk: id => `bi_analysis_modern/pipelines/${id}/execute-chunk/`,
        pipelinePreview: id => `bi_analysis_modern/pipelines/${id}/preview/`,
        pipelineFields: id => `bi_analysis_modern/pipelines/${id}/fields/`,
        pipelineFieldValues: (id, fieldName) => `bi_analysis_modern/pipelines/${id}/fields/${encodeURIComponent(fieldName)}/values/`,
        pipelineLineage: id => `bi_analysis_modern/pipelines/${id}/lineage/`,
        pipelineChartList: 'bi_analysis_modern/pipelines/charts/',
        pipelineChartDetail: id => `bi_analysis_modern/pipelines/charts/${id}/`,
        pipelineChartData: id => `bi_analysis_modern/pipelines/charts/${id}/data/`,
    }
};
