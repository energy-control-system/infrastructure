# E2E Demo Seeder

## Purpose

`tests/test_full_stack_demo_seed.py` запускает тяжелый full-stack black-box сценарий поверх уже поднятого `dev`-стенда и наполняет систему примерно `30` завершенными проверками.

## Preconditions

1. Перейти в каталог `infrastructure`.
2. Поднять стенд:

```bash
docker compose -f docker-compose.dev.yml up --build
```

3. Убедиться, что `Nginx` отвечает по `http://localhost`.

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
