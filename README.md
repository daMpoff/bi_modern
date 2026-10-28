# BI Modern

Отдельный модуль бизнес-аналитики: подключения к PostgreSQL, ClickHouse и MSSQL,
файлы, визуальные конвейеры обработки данных, графики и дашборды.

## Подключение

Каталог модуля — `modules/bi_analysis_modern`. Сервер находит `api/**/apps.py`,
клиент — единственный каталог маршрутов `client/js/routes.js`. Главная страница:
`/bi-modern`; API: `/api/bi_analysis_modern/`.

Python-зависимости объявлены в `pyproject.toml`, клиентские — в
`client/package.json`; устанавливаются штатными `ergoms python-install` и
`ergoms npm run install:all`. Схема БД и меню применяются через
`ergoms api migrate_module --module=bi_analysis_modern`.

Модуль может работать одновременно с обычным `bi_analysis`. Клиентские запросы
должны использовать `client/src/js/endpoints.js` (`biEndpoints.bi`) или
центральный ключ `biModern`, а не ключ `bi` обычного BI. Имена маршрутов modern
не должны пересекаться с обычным BI; список дашбордов называется `DashboardsModern`.
Иконки подключаются через импорты, без абсолютных адресов старого `core/bi`.
Загрузки выполняются через `apiClient.post` с `FormData`, списки файлов — через
`apiClient.get`. Удалённые методы `upload` и `getUploadedFiles` не используются.
Очередь фоновых задач — `bi_analysis_modern`, схема PostgreSQL — `m_bi_analysis_modern`.
Переименование подключения сохраняет его конфигурацию; частичное изменение
конфигурации сохраняет пропущенные поля. Для PostgreSQL форма передаёт
`connector_type: postgres`, при редактировании тип берётся из самого подключения.

## Проверка

Клиентские регрессии: `node --test modules/bi_analysis_modern/client/tests/*.test.mjs`
из корня проекта с Node.js из окружения ERGO MS. Проверка API:
`ergoms api test modules.bi_analysis_modern.api.tests`. Проверки маршрутов и API
не требуют запущенных внешних источников данных.
