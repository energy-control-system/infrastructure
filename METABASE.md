# Metabase

Короткая инструкция для оператора стенда.

## Что добавлено

- `metabase` с хранением application DB в PostgreSQL.
- Образ Metabase зафиксирован на `metabase/metabase:v0.59.6.3`.
- `clickhouse-db-init`, который создаёт БД `analytics_service` через `clickhouse-client --port 9123` до старта `analytics-service` и bootstrap Metabase.
- `metabase-init`, который через API делает bootstrap, подключает ClickHouse и создаёт русскую коллекцию `Аналитика энергоконтроля`.
- Два русских дашборда: `Обзор операций` и `Абоненты и объекты`.
- BI-витрины в ClickHouse, которые читают Metabase-вопросы.
- Upgrade migration `analytics-service/database/migrations/clickhouse/00003_bi_inspection_results.sql`, которая добавляет `v_bi_inspection_results`.

## Dev

1. Поднимите стенд:
   ```bash
   docker compose -f infrastructure/docker-compose.dev.yml up -d --build
   ```
2. Откройте Metabase:
   - `http://localhost/metabase/`
3. Если нужен быстрый старт после чистого стенда, дождитесь завершения `clickhouse-db-init`, затем `metabase-init`.
4. В dev по умолчанию используется валидный адрес bootstrap-пользователя: `admin@example.com`.

## Что должно быть в Metabase

- Коллекция: `Аналитика энергоконтроля`
- Дашборды:
  - `Обзор операций`
  - `Абоненты и объекты`

## Prod env

В `infrastructure/docker-compose.prod.yml` для `metabase` нужен только `POSTGRES_PASSWORD`, а для `metabase-init` обязательны:

- `METABASE_URL`
- `METABASE_ADMIN_EMAIL`
- `METABASE_ADMIN_PASSWORD`
- `METABASE_ADMIN_FIRST_NAME`
- `METABASE_ADMIN_LAST_NAME`
- `METABASE_COLLECTION_NAME`
- `METABASE_CLICKHOUSE_NAME`
- `METABASE_CLICKHOUSE_HOST`
- `METABASE_CLICKHOUSE_DB`
- `METABASE_CLICKHOUSE_USER`
- `METABASE_CLICKHOUSE_PASSWORD`

Порт ClickHouse для Metabase зафиксирован на `9123` инфраструктурой, чтобы совпадать с `clickhouse.config.xml`.

## Быстрая проверка

- Health Metabase:
  ```bash
  curl -fsS http://localhost/metabase/api/health
  ```
- Логи bootstrap:
  ```bash
  docker compose -f infrastructure/docker-compose.dev.yml logs --tail=200 metabase-init
  ```
- Проверка BI views в ClickHouse:
  ```bash
  docker compose -f infrastructure/docker-compose.dev.yml exec clickhouse \
    clickhouse-client --port 9123 -u root --password 's4c1A2bgbqK2FJuR20R7' \
    -d analytics_service --query "SHOW TABLES LIKE 'v_bi_%'"
  ```

## Повторный запуск

`metabase-init` идемпотентен: его можно запускать повторно, он не ломает уже созданные коллекцию, карточки и дашборды, а обновляет их под текущую конфигурацию.
