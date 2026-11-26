# Работа с BI Modern

Эти инструкции действуют во всём репозитории. BI Modern — модуль ERGO MS на Django и Vue. В установленном ядре он находится в `modules/bi_analysis_modern/`. Команды установки приведены в [README](README.md).

## Перед изменениями

- Проверь текущую ветку и `git status`. Сохраняй изменения, которые уже есть в рабочем дереве.
- До правок согласуй с владельцем изменение публичного API, добавление зависимости или действие с риском потери данных. Опиши, что изменится и кого это затронет.

## Ориентиры по коду

- **API и задачи.** Django-пакет — `modules.bi_analysis_modern.api`, очередь Celery — `bi_analysis_modern`. Движок конвейеров находится в [api/execution/](api/execution/). При его изменении учитывай ранее сохранённые графы. [Устройство конвейеров](docs/pipelines.md)
- **Клиент.** Маршруты начинаются с `/bi-modern` и объявлены в [client/js/routes.js](client/js/routes.js). В компонентах используй `biEndpoints` из [client/src/js/endpoints.js](client/src/js/endpoints.js). Для сборки модуля явно импортируй `logError` и `logWarn` из `@/js/utils/logError.js`.
- **Python-блоки.** Код исполнителя находится в [sandbox/](sandbox/). Его запуск и ограничения описаны в [руководстве по Python-блокам](docs/python-blocks.md).

## Проверки

Выбирай проверки по затронутой части. Запускай команды из корня настроенного ERGO MS с Python и Node.js из его окружения.

| Что изменилось | Что выполнить |
| --- | --- |
| Клиент | `node --test modules/bi_analysis_modern/client/tests/*.test.mjs` |
| Компоненты, импорты или сборка клиента | `node core/client/scripts/build-client-remote.js --module=bi_analysis_modern` |
| Сервер | `ergoms api test modules.bi_analysis_modern.api` |
| Исполнитель Python-блоков | `python -m unittest modules.bi_analysis_modern.sandbox.test_executor` |
| Только Markdown | Проверь относительные ссылки, изображения и отображение изменённого блока. |

## Публикация

Начинай работу в отдельной ветке от актуальной `dev`. Для публикации отправь рабочую ветку на GitHub и открой pull request в `dev`. В описании укажи, что изменилось, как это проверено и какие проверки были пропущены.
