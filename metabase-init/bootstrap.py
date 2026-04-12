import json
import os
import time
import urllib.error
import urllib.request


FILTERS = {
    "period": {"label": "Период", "type": "date", "parameter_id": "filter-period"},
    "inspection_type": {"label": "Тип проверки", "type": "text", "parameter_id": "filter-inspection-type"},
    "brigade_id": {"label": "Бригада", "type": "number", "parameter_id": "filter-brigade"},
    "subscriber_status": {"label": "Статус абонента", "type": "text", "parameter_id": "filter-subscriber-status"},
    "automaton_state": {"label": "Наличие автомата", "type": "text", "parameter_id": "filter-automaton-state"},
}


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def filter_template_tag(tag_name: str) -> dict:
    spec = FILTERS[tag_name]
    return {
        "id": tag_name,
        "name": tag_name,
        "display-name": spec["label"],
        "type": spec["type"],
    }


def filter_parameter_mapping(tag_name: str) -> dict:
    spec = FILTERS[tag_name]
    return {
        "parameter_id": spec["parameter_id"],
        "target": ["variable", ["template-tag", tag_name]],
    }


def build_native_query(sql: str, tag_names=None) -> dict:
    tag_names = tag_names or []
    template_tags = {tag_name: filter_template_tag(tag_name) for tag_name in tag_names}
    native = {"query": sql.strip()}
    if template_tags:
        native["template-tags"] = template_tags
    return native


def build_parameter_mappings(tag_names=None) -> list:
    return [filter_parameter_mapping(tag_name) for tag_name in (tag_names or [])]


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
            except urllib.error.URLError:
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

    def create_database(self, payload=None):
        return self.request("POST", "/api/database/", payload or build_database_payload())

    def update_database(self, database_id: int, payload=None):
        return self.request("PUT", f"/api/database/{database_id}", payload or build_database_payload())

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


def build_database_payload() -> dict:
    return {
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


def default_collection_name() -> str:
    return env("METABASE_COLLECTION_NAME", "Аналитика энергоконтроля")


def find_by_name(items, name):
    for item in items or []:
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
                "native": build_native_query(
                    """
select sum(tasks_count) as "Всего завершенных задач"
from v_bi_tasks_daily
where 1 = 1
[[and day >= {{period}}]]
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Нарушения выявлены",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select sum(violations_detected_count) as "Нарушения выявлены"
from v_bi_tasks_daily
where 1 = 1
[[and day >= {{period}}]]
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Средняя длительность выполнения",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select round(avg(avg_duration_minutes), 2) as "Средняя длительность выполнения"
from v_bi_tasks_daily
where 1 = 1
[[and day >= {{period}}]]
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Случаи несанкционированного потребления",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select sum(unauthorized_consumers_count) as "Случаи несанкционированного потребления"
from v_bi_tasks_daily
where 1 = 1
[[and day >= {{period}}]]
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Динамика выполненных задач по дням",
            "display": "line",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  day as "Дата",
  tasks_count as "Количество задач"
from v_bi_tasks_daily
where 1 = 1
[[and day >= {{period}}]]
order by day
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Распределение по типам проверок",
            "display": "bar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  inspection_type_ru as "Тип проверки",
  sum(tasks_count) as "Количество"
from v_bi_inspection_results
where 1 = 1
[[and day >= {{period}}]]
group by inspection_type_ru
order by "Количество" desc
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Результаты проверок",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  inspection_type_ru as "Тип проверки",
  inspection_result_ru as "Результат",
  sum(tasks_count) as "Количество"
from v_bi_inspection_results
where 1 = 1
[[and day >= {{period}}]]
[[and inspection_type_ru = {{inspection_type}}]]
group by inspection_type_ru, inspection_result_ru
order by "Количество" desc
""",
                    ["period", "inspection_type"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period", "inspection_type"]),
        },
        {
            "name": "Рейтинг бригад по числу выполненных задач",
            "display": "bar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  brigade_id as "Бригада",
  sum(tasks_count) as "Количество задач"
from v_bi_brigade_performance
where 1 = 1
[[and day >= {{period}}]]
[[and brigade_id = {{brigade_id}}]]
group by brigade_id
order by "Количество задач" desc
""",
                    ["period", "brigade_id"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period", "brigade_id"]),
        },
        {
            "name": "Распределение абонентов по статусам",
            "display": "pie",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  subscriber_status_ru as "Статус",
  count() as "Количество"
from v_bi_subscriber_object_profile
where 1 = 1
[[and last_task_day >= {{period}}]]
[[and subscriber_status_ru = {{subscriber_status}}]]
group by subscriber_status_ru
order by "Количество" desc
""",
                    ["period", "subscriber_status"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period", "subscriber_status"]),
        },
        {
            "name": "Объекты с автоматом и без автомата",
            "display": "pie",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  automaton_state_ru as "Состояние",
  count() as "Количество"
from v_bi_subscriber_object_profile
where 1 = 1
[[and last_task_day >= {{period}}]]
[[and automaton_state_ru = {{automaton_state}}]]
group by automaton_state_ru
""",
                    ["period", "automaton_state"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period", "automaton_state"]),
        },
        {
            "name": "Наиболее частые адреса проверок",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  object_address as "Адрес",
  sum(total_tasks_count) as "Количество проверок"
from v_bi_subscriber_object_profile
where 1 = 1
[[and last_task_day >= {{period}}]]
group by object_address
order by "Количество проверок" desc
limit 20
""",
                    ["period"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period"]),
        },
        {
            "name": "Статусы абонентов по типам проверок",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  inspection_type_ru as "Тип проверки",
  subscriber_status_ru as "Статус абонента",
  sum(tasks_count) as "Количество"
from v_bi_inspection_results
where 1 = 1
[[and day >= {{period}}]]
[[and inspection_type_ru = {{inspection_type}}]]
[[and subscriber_status_ru = {{subscriber_status}}]]
group by inspection_type_ru, subscriber_status_ru
order by 1, 2
""",
                    ["period", "inspection_type", "subscriber_status"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period", "inspection_type", "subscriber_status"]),
        },
        {
            "name": "Таблица объектов и абонентов",
            "display": "table",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": build_native_query(
                    """
select
  subscriber_account_number as "Лицевой счет",
  subscriber_status_ru as "Статус",
  object_address as "Адрес",
  automaton_state_ru as "Автомат",
  total_tasks_count as "Проверок",
  violations_detected_count as "Нарушений"
from v_bi_subscriber_object_profile
where 1 = 1
[[and last_task_day >= {{period}}]]
[[and subscriber_status_ru = {{subscriber_status}}]]
[[and automaton_state_ru = {{automaton_state}}]]
order by last_task_day desc, total_tasks_count desc
""",
                    ["period", "subscriber_status", "automaton_state"],
                ),
            },
            "parameter_mappings": build_parameter_mappings(["period", "subscriber_status", "automaton_state"]),
        },
    ]


def dashboard_parameters():
    return [
        {"id": "filter-period", "name": "Период", "slug": "period", "type": "date/single"},
        {"id": "filter-inspection-type", "name": "Тип проверки", "slug": "inspection_type", "type": "string/="},
        {"id": "filter-brigade", "name": "Бригада", "slug": "brigade_id", "type": "number/="},
        {"id": "filter-subscriber-status", "name": "Статус абонента", "slug": "subscriber_status", "type": "string/="},
        {"id": "filter-automaton-state", "name": "Наличие автомата", "slug": "automaton_state", "type": "string/="},
    ]


CARD_LAYOUTS = {
    "Обзор операций": [
        ("Всего завершенных задач", 0, 0, 6, 3, ["period"]),
        ("Нарушения выявлены", 0, 6, 6, 3, ["period"]),
        ("Средняя длительность выполнения", 0, 12, 6, 3, ["period"]),
        ("Случаи несанкционированного потребления", 0, 18, 6, 3, ["period"]),
        ("Динамика выполненных задач по дням", 3, 0, 12, 6, ["period"]),
        ("Распределение по типам проверок", 3, 12, 12, 6, ["period"]),
        ("Результаты проверок", 9, 0, 12, 8, ["period", "inspection_type"]),
        ("Рейтинг бригад по числу выполненных задач", 9, 12, 12, 8, ["period", "brigade_id"]),
    ],
    "Абоненты и объекты": [
        ("Распределение абонентов по статусам", 0, 0, 8, 6, ["period", "subscriber_status"]),
        ("Объекты с автоматом и без автомата", 0, 8, 8, 6, ["period", "automaton_state"]),
        ("Наиболее частые адреса проверок", 0, 16, 8, 6, ["period"]),
        ("Статусы абонентов по типам проверок", 6, 0, 12, 8, ["period", "inspection_type", "subscriber_status"]),
        ("Таблица объектов и абонентов", 6, 12, 12, 8, ["period", "subscriber_status", "automaton_state"]),
    ],
}


def build_dashboard_specs(cards_by_name):
    specs = []
    for dashboard_name, card_defs in CARD_LAYOUTS.items():
        cards = []
        for card_name, row, col, size_x, size_y, tag_names in card_defs:
            cards.append(
                {
                    "card_name": card_name,
                    "card_id": cards_by_name[card_name],
                    "row": row,
                    "col": col,
                    "size_x": size_x,
                    "size_y": size_y,
                    "parameter_mappings": build_parameter_mappings(tag_names),
                }
            )
        specs.append(
            {
                "name": dashboard_name,
                "description": (
                    "Ключевые показатели выполнения проверок и эффективности бригад."
                    if dashboard_name == "Обзор операций"
                    else "Срезы по статусам абонентов, объектам и адресам проверок."
                ),
                "parameters": dashboard_parameters(),
                "cards": cards,
            }
        )
    return specs


def upsert_database(client):
    existing = find_by_name(client.list_databases(), env("METABASE_CLICKHOUSE_NAME", "Analytics BI"))
    payload = build_database_payload()
    if existing is None:
        database = client.create_database(payload)
    else:
        database = client.update_database(existing["id"], payload)
    client.sync_database(database["id"])
    return database


def upsert_collection(client):
    collection = find_by_name(client.list_collections(), default_collection_name())
    if collection is None:
        return client.create_collection(default_collection_name())
    return collection


def upsert_cards(client, collection_id: int, database_id: int):
    items = client.list_collection_items(collection_id)
    cards_by_name = {}
    for spec in build_question_specs(database_id):
        payload = {
            "name": spec["name"],
            "display": spec["display"],
            "dataset_query": spec["dataset_query"],
            "collection_id": collection_id,
        }
        existing = find_by_name(items, spec["name"])
        if existing is None:
            card = client.create_card(payload)
        else:
            card = client.update_card(existing["id"], payload)
        cards_by_name[spec["name"]] = card["id"]
    return cards_by_name


def upsert_dashboards(client, collection_id: int, cards_by_name):
    dashboards = client.list_dashboards()
    for dashboard_spec in build_dashboard_specs(cards_by_name):
        dashboard = find_by_name(dashboards, dashboard_spec["name"])
        payload = {
            "name": dashboard_spec["name"],
            "description": dashboard_spec["description"],
            "collection_id": collection_id,
            "parameters": dashboard_spec["parameters"],
        }
        if dashboard is None:
            dashboard = client.create_dashboard(payload)
        else:
            dashboard = client.update_dashboard(dashboard["id"], payload)
        client.replace_dashboard_cards(
            dashboard["id"],
            {
                "cards": [
                    {
                        "card_id": card["card_id"],
                        "row": card["row"],
                        "col": card["col"],
                        "size_x": card["size_x"],
                        "size_y": card["size_y"],
                        "parameter_mappings": card["parameter_mappings"],
                    }
                    for card in dashboard_spec["cards"]
                ]
            },
        )


def run_bootstrap(client) -> None:
    client.wait_for_health()
    if not client.is_setup_complete():
        client.setup()
    client.login()
    database = upsert_database(client)
    collection = upsert_collection(client)
    cards_by_name = upsert_cards(client, collection["id"], database["id"])
    upsert_dashboards(client, collection["id"], cards_by_name)


def main() -> None:
    run_bootstrap(MetabaseClient(env("METABASE_URL", "http://metabase:3000")))


if __name__ == "__main__":
    main()
