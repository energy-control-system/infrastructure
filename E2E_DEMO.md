# E2E Demo Seeder

## Purpose

`tests/test_full_stack_demo_seed.py` запускает тяжелый full-stack black-box сценарий поверх уже поднятого `dev`-стенда и наполняет систему примерно `30` завершенными проверками.

## Preconditions

1. Перейти в каталог `infrastructure`.
2. Поднять стенд:

```bash
docker compose -f docker-compose.dev.yml up --build -d
```

3. Убедиться, что `Nginx` отвечает по `http://localhost`.
4. Дождаться завершения `kafka-topics-init`, который заранее создает `tasks-topic` и `inspections-topic` для Kafka consumers.

## Run

```bash
ENERGO_E2E_RUN_FULL_STACK=1 uv run python -m unittest tests.test_full_stack_demo_seed -v
```

Если стенд опубликован не на `http://localhost`, задать `ENERGO_E2E_BASE_URL`:

```bash
ENERGO_E2E_RUN_FULL_STACK=1 ENERGO_E2E_BASE_URL=http://localhost uv run python -m unittest tests.test_full_stack_demo_seed -v
```

## Expected Result

- создаются `3` новые бригады;
- создаются и завершаются `30` новых задач и проверок;
- `analytics-service` создает хотя бы один basic report за текущий день;
- в конце тест печатает краткую сводку с идентификаторами созданных сущностей.
- типичный live-прогон на локальном стенде занимает около `2` минут.

## Repeat Run

Если нужен повторный прогон на чистом стенде, предварительно сбросить volumes:

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build -d
```

## Year Database Seed

Для демонстрации годовой истории аналитики можно наполнить базы напрямую:

```bash
uv run python year_demo_seed.py
```

По умолчанию скрипт создает `1000` завершенных проверок, распределенных по году с разным количеством проверок в разные дни.
Абоненты, адреса, даты, типы проверок, бригады и потребление распределяются псевдослучайно, но воспроизводимо через `--random-seed`.
Он пишет связанные данные в PostgreSQL БД `subscriber_service`, `brigade_service`, `task_service`, `inspection_service`
и в ClickHouse таблицу `analytics_service.finished_tasks`.

Параметры:

```bash
uv run python year_demo_seed.py --rows 1000 --start-date 2025-01-01 --compose-file docker-compose.dev.yml --random-seed 20250505
```

Если стенд поднят с явным именем проекта Docker Compose:

```bash
uv run python year_demo_seed.py --compose-file ./infrastructure/docker-compose.dev.yml --project-name energy-control-system
```

Скрипт детерминированный и перед вставкой удаляет свои предыдущие строки в выделенном диапазоне ID, поэтому его можно запускать повторно на том же dev-стенде.
