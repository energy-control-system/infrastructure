# Metabase

Короткая инструкция для оператора стенда.

## Что добавлено

- `metabase` с хранением application DB в PostgreSQL.
- Образ Metabase зафиксирован на `metabase/metabase:v0.59.6.3`.
- `clickhouse-db-init`, который создаёт БД `analytics_service` через `clickhouse-client --port 9123` до старта `analytics-service` и bootstrap Metabase.
- `metabase-init`, который через API делает bootstrap, подключает ClickHouse и создаёт русскую коллекцию `Аналитика энергоконтроля`.
- Три русских дашборда: `Обзор операций`, `Абоненты и объекты` и `Аномалии потребления`.
- BI-витрины в ClickHouse, которые читают Metabase-вопросы.
- Upgrade migration `analytics-service/database/migrations/clickhouse/00003_bi_inspection_results.sql`, которая добавляет `v_bi_inspection_results`.
- Upgrade migration `analytics-service/database/migrations/clickhouse/00004_consumption_anomaly_views.sql`, которая добавляет показания проверенных приборов в `finished_tasks` и BI-витрины `v_bi_consumption_monthly`, `v_bi_consumption_anomalies`.

## Dev

1. Полный стенд с `Nginx` и маршрутом `/metabase`:
   ```bash
   docker compose -f infrastructure/docker-compose.dev.yml -p energy-control-system up -d --build
   ```
2. Откройте Metabase:
   - `http://localhost/metabase/`
3. Если нужен быстрый старт после чистого стенда, дождитесь завершения `clickhouse-db-init`, затем `metabase-init`.
4. В dev по умолчанию используется валидный адрес bootstrap-пользователя: `admin@example.com`.

## Minimal run

Если нужно поднять только `analytics-service`, его зависимости и Metabase, без полного стенда:

```bash
MB_SITE_URL=http://localhost:3000/ docker compose -f infrastructure/docker-compose.dev.yml -p energy-control-system up -d --build \
  postgres kafka clickhouse clickhouse-db-init analytics-service \
  metabase-db-init metabase metabase-init
```

Для такого запуска `Nginx` не нужен; Metabase доступен напрямую по порту `3000`:

- `http://localhost:3000/`
- `http://localhost:3000/api/health`

Для полного dev-стенда без override сохраняется путь через `Nginx`: `http://localhost/metabase/`.

## Что должно быть в Metabase

- Коллекция: `Аналитика энергоконтроля`
- Дашборды:
  - `Обзор операций`
  - `Абоненты и объекты`
  - `Аномалии потребления`

## Аномалии потребления

Дашборд `Аномалии потребления` строится по фактическим расходам из завершенных проверок. Значения попадают в ClickHouse из `inspection-service.inspected_devices.consumption` через `analytics-service`.

Витрина считает два типа отклонений:

- отклонение месячного расхода абонента от его собственной истории на 50% и больше, если по абоненту накоплено не менее 3 месяцев;
- превышение среднего значения по району в 2.5 раза и больше.

Район в текущей модели проекта выводится из адреса объекта как часть до первой запятой, например `ул. Ленина` из `ул. Ленина, д. 1, кв. 10`. Если в доменной модели появится отдельное поле района или состава семьи, витрину можно переключить на него без изменения Metabase API-слоя.

## Быстрая проверка

- Health Metabase через `Nginx`:
  ```bash
  curl -fsS http://localhost/metabase/api/health
  ```
- Health Metabase для `minimal run`:
  ```bash
  curl -fsS http://localhost:3000/api/health
  ```
- Логи bootstrap:
  ```bash
  docker compose -p energy-control-system logs --tail=200 metabase-init
  ```
- Проверка BI views в ClickHouse:
  ```bash
  docker compose -p energy-control-system exec clickhouse \
    clickhouse-client --port 9123 -u root --password 's4c1A2bgbqK2FJuR20R7' \
    -d analytics_service --query "SHOW TABLES LIKE 'v_bi_%'"
  ```

## Повторный запуск

`metabase-init` идемпотентен: его можно запускать повторно, он не ломает уже созданные коллекцию, карточки и дашборды, а обновляет их под текущую конфигурацию.
