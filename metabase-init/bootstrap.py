import json
import os
import time
import urllib.error
import urllib.request


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


class MetabaseClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session_token = None

    def request(self, method: str, path: str, payload=None):
        data = None
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["X-Metabase-Session"] = self.session_token
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    def wait_for_health(self) -> None:
        deadline = time.time() + 300
        while time.time() < deadline:
            try:
                payload = self.request("GET", "/api/health")
                if payload.get("status") == "ok":
                    return
            except Exception:
                time.sleep(2)
        raise RuntimeError("metabase did not become healthy in time")

    def is_setup_complete(self) -> bool:
        props = self.request("GET", "/api/session/properties")
        return not bool(props.get("setup-token"))

    def setup(self) -> None:
        props = self.request("GET", "/api/session/properties")
        token = props["setup-token"]
        payload = {
            "token": token,
            "prefs": {
                "site_name": env("MB_SITE_NAME", "Энергоконтроль"),
                "site_locale": "ru",
            },
            "user": {
                "first_name": env("METABASE_ADMIN_FIRST_NAME", "Демо"),
                "last_name": env("METABASE_ADMIN_LAST_NAME", "Администратор"),
                "email": env("METABASE_ADMIN_EMAIL", "admin@localhost"),
                "password": env("METABASE_ADMIN_PASSWORD", "MetabaseAdmin123"),
            },
            "database": None,
        }
        self.request("POST", "/api/setup", payload)

    def login(self) -> None:
        payload = {
            "username": env("METABASE_ADMIN_EMAIL", "admin@localhost"),
            "password": env("METABASE_ADMIN_PASSWORD", "MetabaseAdmin123"),
        }
        session = self.request("POST", "/api/session", payload)
        self.session_token = session["id"]

    def list_databases(self):
        return self.request("GET", "/api/database/")

    def create_database(self):
        payload = {
            "engine": "clickhouse",
            "name": env("METABASE_CLICKHOUSE_NAME", "Analytics BI"),
            "details": {
                "host": env("METABASE_CLICKHOUSE_HOST", "clickhouse"),
                "port": int(env("METABASE_CLICKHOUSE_PORT", "8123")),
                "dbname": env("METABASE_CLICKHOUSE_DB", "analytics_service"),
                "user": env("METABASE_CLICKHOUSE_USER", "root"),
                "password": env("METABASE_CLICKHOUSE_PASSWORD", "s4c1A2bgbqK2FJuR20R7"),
                "ssl": False,
                "tunnel-enabled": False,
            },
            "is_full_sync": True,
        }
        return self.request("POST", "/api/database/", payload)

    def sync_database(self, database_id: int):
        return self.request("POST", f"/api/database/{database_id}/sync_schema")

    def list_collections(self):
        return self.request("GET", "/api/collection/")

    def create_collection(self, name: str):
        return self.request("POST", "/api/collection/", {"name": name})

    def list_collection_items(self, collection_id: int):
        return self.request("GET", f"/api/collection/{collection_id}/items")

    def create_card(self, payload):
        return self.request("POST", "/api/card", payload)

    def update_card(self, card_id: int, payload):
        return self.request("PUT", f"/api/card/{card_id}", payload)

    def list_dashboards(self):
        return self.request("GET", "/api/dashboard/")

    def create_dashboard(self, payload):
        return self.request("POST", "/api/dashboard/", payload)

    def update_dashboard(self, dashboard_id: int, payload):
        return self.request("PUT", f"/api/dashboard/{dashboard_id}", payload)

    def replace_dashboard_cards(self, dashboard_id: int, payload):
        return self.request("PUT", f"/api/dashboard/{dashboard_id}/cards", payload)


def default_collection_name() -> str:
    return os.environ.get("METABASE_COLLECTION_NAME", "Аналитика энергоконтроля")


def find_by_name(items, name):
    for item in items:
        if item.get("name") == name:
            return item
    return None


def build_question_specs(database_id: int):
    return [
        {
            "name": "Всего завершенных задач",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {"query": "select sum(tasks_count) as \"Всего завершенных задач\" from v_bi_tasks_daily"},
            },
        },
        {
            "name": "Нарушения выявлены",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {"query": "select sum(violations_detected_count) as \"Нарушения выявлены\" from v_bi_tasks_daily"},
            },
        },
        {
            "name": "Средняя длительность выполнения",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {"query": "select round(avg(avg_duration_minutes), 2) as \"Средняя длительность выполнения\" from v_bi_tasks_daily"},
            },
        },
        {
            "name": "Случаи несанкционированного потребления",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {"query": "select sum(unauthorized_consumers_count) as \"Случаи несанкционированного потребления\" from v_bi_tasks_daily"},
            },
        },
        {
            "name": "Динамика выполненных задач по дням",
            "display": "line",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": """
select
  day as "Дата",
  tasks_count as "Количество задач"
from v_bi_tasks_daily
order by day
""".strip(),
                    "template-tags": {},
                },
            },
        },
        {
            "name": "Распределение по типам проверок",
            "display": "bar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": """
select
  inspection_type_ru as "Тип проверки",
  sum(tasks_count) as "Количество"
from v_bi_inspection_results
group by inspection_type_ru
order by "Количество" desc
""".strip()
                },
            },
        },
        {
            "name": "Результаты проверок",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select inspection_type_ru as \"Тип проверки\", inspection_result_ru as \"Результат\", sum(tasks_count) as \"Количество\" from v_bi_inspection_results group by inspection_type_ru, inspection_result_ru order by \"Количество\" desc"
                },
            },
        },
        {
            "name": "Рейтинг бригад по числу выполненных задач",
            "display": "bar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select brigade_id as \"Бригада\", sum(tasks_count) as \"Количество задач\" from v_bi_brigade_performance group by brigade_id order by \"Количество задач\" desc"
                },
            },
        },
        {
            "name": "Распределение абонентов по статусам",
            "display": "pie",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select subscriber_status_ru as \"Статус\", count() as \"Количество\" from v_bi_subscriber_object_profile group by subscriber_status_ru order by \"Количество\" desc"
                },
            },
        },
        {
            "name": "Объекты с автоматом и без автомата",
            "display": "pie",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select automaton_state_ru as \"Состояние\", count() as \"Количество\" from v_bi_subscriber_object_profile group by automaton_state_ru"
                },
            },
        },
        {
            "name": "Наиболее частые адреса проверок",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select object_address as \"Адрес\", sum(total_tasks_count) as \"Количество проверок\" from v_bi_subscriber_object_profile group by object_address order by \"Количество проверок\" desc limit 20"
                },
            },
        },
        {
            "name": "Статусы абонентов по типам проверок",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": """
select
  r.inspection_type_ru as "Тип проверки",
  p.subscriber_status_ru as "Статус абонента",
  count() as "Количество"
from v_bi_inspection_results r
cross join (
  select distinct subscriber_status_ru
  from v_bi_subscriber_object_profile
) p
group by r.inspection_type_ru, p.subscriber_status_ru
order by 1, 2
""".strip()
                },
            },
        },
        {
            "name": "Таблица объектов и абонентов",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select subscriber_account_number as \"Лицевой счет\", subscriber_status_ru as \"Статус\", object_address as \"Адрес\", automaton_state_ru as \"Автомат\", total_tasks_count as \"Проверок\", violations_detected_count as \"Нарушений\" from v_bi_subscriber_object_profile order by last_task_day desc, total_tasks_count desc"
                },
            },
        },
    ]


def dashboard_parameters():
    return [
        {"id": "filter-period", "name": "Период", "slug": "period", "type": "date/all-options"},
        {"id": "filter-inspection-type", "name": "Тип проверки", "slug": "inspection_type", "type": "string/="},
        {"id": "filter-brigade", "name": "Бригада", "slug": "brigade_id", "type": "number/="},
        {"id": "filter-subscriber-status", "name": "Статус абонента", "slug": "subscriber_status", "type": "string/="},
        {"id": "filter-automaton-state", "name": "Наличие автомата", "slug": "automaton_state", "type": "string/="},
    ]


def build_dashboard_specs(cards_by_name):
    return [
        {
            "name": "Обзор операций",
            "description": "Ключевые показатели выполнения проверок и эффективности бригад.",
            "parameters": dashboard_parameters(),
            "cards": [
                {"card_name": "Всего завершенных задач", "card_id": cards_by_name["Всего завершенных задач"], "row": 0, "col": 0, "size_x": 6, "size_y": 3, "parameter_mappings": []},
                {"card_name": "Нарушения выявлены", "card_id": cards_by_name["Нарушения выявлены"], "row": 0, "col": 6, "size_x": 6, "size_y": 3, "parameter_mappings": []},
                {"card_name": "Средняя длительность выполнения", "card_id": cards_by_name["Средняя длительность выполнения"], "row": 0, "col": 12, "size_x": 6, "size_y": 3, "parameter_mappings": []},
                {"card_name": "Случаи несанкционированного потребления", "card_id": cards_by_name["Случаи несанкционированного потребления"], "row": 0, "col": 18, "size_x": 6, "size_y": 3, "parameter_mappings": []},
                {"card_name": "Динамика выполненных задач по дням", "card_id": cards_by_name["Динамика выполненных задач по дням"], "row": 3, "col": 0, "size_x": 12, "size_y": 6, "parameter_mappings": []},
                {"card_name": "Распределение по типам проверок", "card_id": cards_by_name["Распределение по типам проверок"], "row": 3, "col": 12, "size_x": 12, "size_y": 6, "parameter_mappings": []},
                {"card_name": "Результаты проверок", "card_id": cards_by_name["Результаты проверок"], "row": 9, "col": 0, "size_x": 12, "size_y": 8, "parameter_mappings": []},
                {"card_name": "Рейтинг бригад по числу выполненных задач", "card_id": cards_by_name["Рейтинг бригад по числу выполненных задач"], "row": 9, "col": 12, "size_x": 12, "size_y": 8, "parameter_mappings": []},
            ],
        },
        {
            "name": "Абоненты и объекты",
            "description": "Срезы по статусам абонентов, объектам и адресам проверок.",
            "parameters": dashboard_parameters(),
            "cards": [
                {"card_name": "Распределение абонентов по статусам", "card_id": cards_by_name["Распределение абонентов по статусам"], "row": 0, "col": 0, "size_x": 8, "size_y": 6, "parameter_mappings": []},
                {"card_name": "Объекты с автоматом и без автомата", "card_id": cards_by_name["Объекты с автоматом и без автомата"], "row": 0, "col": 8, "size_x": 8, "size_y": 6, "parameter_mappings": []},
                {"card_name": "Наиболее частые адреса проверок", "card_id": cards_by_name["Наиболее частые адреса проверок"], "row": 0, "col": 16, "size_x": 8, "size_y": 6, "parameter_mappings": []},
                {"card_name": "Статусы абонентов по типам проверок", "card_id": cards_by_name["Статусы абонентов по типам проверок"], "row": 6, "col": 0, "size_x": 12, "size_y": 8, "parameter_mappings": []},
                {"card_name": "Таблица объектов и абонентов", "card_id": cards_by_name["Таблица объектов и абонентов"], "row": 6, "col": 12, "size_x": 12, "size_y": 8, "parameter_mappings": []},
            ],
        },
    ]


def main() -> None:
    client = MetabaseClient(env("METABASE_URL", "http://metabase:3000"))
    client.wait_for_health()
    if not client.is_setup_complete():
        client.setup()
    client.login()

    database = find_by_name(client.list_databases(), env("METABASE_CLICKHOUSE_NAME", "Analytics BI"))
    if database is None:
        database = client.create_database()
        client.sync_database(database["id"])

    collection = find_by_name(client.list_collections(), default_collection_name())
    if collection is None:
        collection = client.create_collection(default_collection_name())

    items = client.list_collection_items(collection["id"])
    cards_by_name = {}
    for spec in build_question_specs(database["id"]):
        payload = {**spec, "collection_id": collection["id"]}
        existing = find_by_name(items, spec["name"])
        if existing is None:
            created = client.create_card(payload)
            cards_by_name[spec["name"]] = created["id"]
        else:
            updated = client.update_card(existing["id"], payload)
            cards_by_name[spec["name"]] = updated["id"]

    dashboards = client.list_dashboards()
    for dashboard_spec in build_dashboard_specs(cards_by_name):
        dashboard = find_by_name(dashboards, dashboard_spec["name"])
        metadata = {
            "name": dashboard_spec["name"],
            "description": dashboard_spec["description"],
            "collection_id": collection["id"],
            "parameters": dashboard_spec["parameters"],
        }
        if dashboard is None:
            dashboard = client.create_dashboard(metadata)
        else:
            dashboard = client.update_dashboard(dashboard["id"], metadata)

        client.replace_dashboard_cards(
            dashboard["id"],
            {
                "cards": [
                    {
                        "card_id": item["card_id"],
                        "row": item["row"],
                        "col": item["col"],
                        "size_x": item["size_x"],
                        "size_y": item["size_y"],
                        "parameter_mappings": item.get("parameter_mappings", []),
                    }
                    for item in dashboard_spec["cards"]
                ]
            },
        )


if __name__ == "__main__":
    main()
