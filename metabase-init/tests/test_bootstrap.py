import os
import unittest
from unittest.mock import patch

import bootstrap


class RecordingClient:
    def __init__(self) -> None:
        self.calls = []
        self._card_id = 100
        self._dashboard_id = 200

    def wait_for_health(self) -> None:
        self.calls.append(("wait_for_health",))

    def is_setup_complete(self) -> bool:
        self.calls.append(("is_setup_complete",))
        return True

    def setup(self) -> None:
        self.calls.append(("setup",))

    def login(self) -> None:
        self.calls.append(("login",))

    def list_databases(self):
        self.calls.append(("list_databases",))
        return [{"id": 7, "name": "Analytics BI"}]

    def update_database(self, database_id, payload):
        self.calls.append(("update_database", database_id, payload))
        return {"id": database_id, "name": payload["name"]}

    def create_database(self, payload):
        self.calls.append(("create_database", payload))
        return {"id": 99, "name": payload["name"]}

    def sync_database(self, database_id):
        self.calls.append(("sync_database", database_id))

    def list_collections(self):
        self.calls.append(("list_collections",))
        return []

    def create_collection(self, name):
        self.calls.append(("create_collection", name))
        return {"id": 11, "name": name}

    def list_collection_items(self, collection_id):
        self.calls.append(("list_collection_items", collection_id))
        return []

    def create_card(self, payload):
        self.calls.append(("create_card", payload["name"], payload.get("parameter_mappings", [])))
        self._card_id += 1
        return {"id": self._card_id}

    def update_card(self, card_id, payload):
        self.calls.append(("update_card", card_id, payload["name"], payload.get("parameter_mappings", [])))
        return {"id": card_id}

    def list_dashboards(self):
        self.calls.append(("list_dashboards",))
        return []

    def create_dashboard(self, payload):
        self.calls.append(("create_dashboard", payload["name"], payload.get("parameters", [])))
        self._dashboard_id += 1
        return {"id": self._dashboard_id}

    def update_dashboard(self, dashboard_id, payload):
        self.calls.append(("update_dashboard", dashboard_id, payload))
        return {"id": dashboard_id}

    def get_dashboard(self, dashboard_id):
        self.calls.append(("get_dashboard", dashboard_id))
        return {"id": dashboard_id, "dashcards": []}


class SetupRecordingClient(bootstrap.MetabaseClient):
    def __init__(self) -> None:
        super().__init__("http://metabase.example")
        self.calls = []

    def request(self, method: str, path: str, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET" and path == "/api/session/properties":
            return {"setup-token": "token"}
        if method == "POST" and path == "/api/setup":
            return {"ok": True}
        raise AssertionError(f"unexpected request: {method} {path}")


class SetupStateClient(bootstrap.MetabaseClient):
    def __init__(self, props) -> None:
        super().__init__("http://metabase.example")
        self.props = props

    def request(self, method: str, path: str, payload=None):
        if method == "GET" and path == "/api/session/properties":
            return self.props
        raise AssertionError(f"unexpected request: {method} {path}")


class CreateCardPayloadClient(RecordingClient):
    def create_card(self, payload):
        self.calls.append(("create_card", payload))
        self._card_id += 1
        return {"id": self._card_id}


class DashboardScopeClient(RecordingClient):
    def list_dashboards(self):
        self.calls.append(("list_dashboards",))
        return [{"id": 900, "name": "Обзор операций"}]


class PaginatedScopeClient(RecordingClient):
    def list_databases(self):
        self.calls.append(("list_databases",))
        return {"data": [{"id": 7, "name": "Analytics BI"}]}

    def list_collections(self):
        self.calls.append(("list_collections",))
        return {"data": [{"id": 11, "name": "Аналитика энергоконтроля"}]}

    def list_collection_items(self, collection_id):
        self.calls.append(("list_collection_items", collection_id))
        return {
            "data": [
                {"id": 501, "name": "Всего завершенных задач", "model": "dashboard"},
                {"id": 777, "name": "Всего завершенных задач", "model": "card"},
            ]
        }

    def list_dashboards(self):
        self.calls.append(("list_dashboards",))
        return {"data": []}


class UpdateCardPayloadClient(PaginatedScopeClient):
    def update_card(self, card_id, payload):
        self.calls.append(("update_card", card_id, payload))
        return {"id": card_id}


class ExistingDashboardClient(RecordingClient):
    def list_collections(self):
        self.calls.append(("list_collections",))
        return {"data": [{"id": 11, "name": "Аналитика энергоконтроля"}]}

    def list_collection_items(self, collection_id):
        self.calls.append(("list_collection_items", collection_id))
        return {
            "data": [
                {"id": 301, "name": "Обзор операций", "model": "dashboard"},
                {"id": 401, "name": "Всего завершенных задач", "model": "card"},
                {"id": 402, "name": "Нарушения выявлены", "model": "card"},
                {"id": 403, "name": "Средняя длительность выполнения", "model": "card"},
                {"id": 404, "name": "Случаи несанкционированного потребления", "model": "card"},
                {"id": 405, "name": "Динамика выполненных задач по дням", "model": "card"},
                {"id": 406, "name": "Распределение по типам проверок", "model": "card"},
                {"id": 407, "name": "Результаты проверок", "model": "card"},
                {"id": 408, "name": "Рейтинг бригад по числу выполненных задач", "model": "card"},
                {"id": 409, "name": "Распределение абонентов по статусам", "model": "card"},
                {"id": 410, "name": "Объекты с автоматом и без автомата", "model": "card"},
                {"id": 411, "name": "Наиболее частые адреса проверок", "model": "card"},
                {"id": 412, "name": "Статусы абонентов по типам проверок", "model": "card"},
                {"id": 413, "name": "Таблица объектов и абонентов", "model": "card"},
            ]
        }

    def get_dashboard(self, dashboard_id):
        self.calls.append(("get_dashboard", dashboard_id))
        if dashboard_id == 301:
            return {
                "id": 301,
                "dashcards": [
                    {"id": 901, "card_id": 401, "row": 99, "col": 99, "size_x": 1, "size_y": 1},
                    {"id": 999, "card_id": 9999, "row": 1, "col": 1, "size_x": 1, "size_y": 1},
                ],
            }
        return {"id": dashboard_id, "dashcards": []}




class BootstrapSpecTests(unittest.TestCase):
    def test_find_collection_lookup_supports_model_key(self) -> None:
        items = [
            {"id": 10, "name": "Обзор операций", "model": "dashboard"},
            {"id": 11, "name": "Всего завершенных задач", "model": "card"},
        ]

        self.assertEqual(bootstrap.find_collection_dashboard(items, "Обзор операций")["id"], 10)
        self.assertEqual(bootstrap.find_collection_card(items, "Всего завершенных задач")["id"], 11)

    def test_is_setup_complete_prefers_has_user_setup_flag(self) -> None:
        client = SetupStateClient({"has-user-setup": True, "setup-token": "token"})

        self.assertTrue(client.is_setup_complete())

    def test_setup_uses_valid_default_admin_email(self) -> None:
        client = SetupRecordingClient()

        with patch.dict(os.environ, {}, clear=True):
            client.setup()

        setup_call = next(item for item in client.calls if item[0] == "POST" and item[1] == "/api/setup")
        self.assertEqual(setup_call[2]["user"]["email"], "admin@example.com")

    def test_build_database_payload_defaults_to_clickhouse_http_port(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            payload = bootstrap.build_database_payload()

        self.assertEqual(payload["details"]["port"], 8123)

    def test_question_specs_reference_bi_views_and_filters(self) -> None:
        specs = bootstrap.build_question_specs(database_id=42)
        names = [item["name"] for item in specs]
        self.assertEqual(
            names,
            [
                "Всего завершенных задач",
                "Нарушения выявлены",
                "Средняя длительность выполнения",
                "Случаи несанкционированного потребления",
                "Динамика выполненных задач по дням",
                "Распределение по типам проверок",
                "Результаты проверок",
                "Рейтинг бригад по числу выполненных задач",
                "Распределение абонентов по статусам",
                "Объекты с автоматом и без автомата",
                "Наиболее частые адреса проверок",
                "Статусы абонентов по типам проверок",
                "Таблица объектов и абонентов",
                "Всего аномалий потребления",
                "Абоненты с аномалиями потребления",
                "Динамика аномалий потребления по месяцам",
                "Причины аномалий потребления",
                "Последние аномалии потребления",
                "Помесячное потребление абонентов",
                "Отклонение от среднего по району",
            ],
        )
        sql_text = "\n".join(item["dataset_query"]["native"]["query"] for item in specs)
        self.assertIn("v_bi_tasks_daily", sql_text)
        self.assertIn("v_bi_brigade_performance", sql_text)
        self.assertIn("v_bi_inspection_results", sql_text)
        self.assertIn("v_bi_subscriber_object_profile", sql_text)
        specs_by_name = {item["name"]: item for item in specs}
        self.assertIn(
            "sum(avg_duration_minutes * tasks_count) / nullIf(sum(tasks_count), 0)",
            specs_by_name["Средняя длительность выполнения"]["dataset_query"]["native"]["query"],
        )
        self.assertIn(
            "countDistinct(subscriber_id)",
            specs_by_name["Распределение абонентов по статусам"]["dataset_query"]["native"]["query"],
        )
        expected_tags = {
            "Всего завершенных задач": {"period"},
            "Нарушения выявлены": {"period"},
            "Средняя длительность выполнения": {"period"},
            "Случаи несанкционированного потребления": {"period"},
            "Динамика выполненных задач по дням": {"period"},
            "Распределение по типам проверок": {"period"},
            "Результаты проверок": {"period", "inspection_type"},
            "Рейтинг бригад по числу выполненных задач": {"period", "brigade_id"},
            "Распределение абонентов по статусам": {"period", "subscriber_status"},
            "Объекты с автоматом и без автомата": {"period", "automaton_state"},
            "Наиболее частые адреса проверок": {"period"},
            "Статусы абонентов по типам проверок": {"period", "inspection_type", "subscriber_status"},
            "Таблица объектов и абонентов": {"period", "subscriber_status", "automaton_state"},
            "Всего аномалий потребления": {"period", "subscriber_id", "anomaly_reason", "district_name"},
            "Абоненты с аномалиями потребления": {"period", "subscriber_id", "anomaly_reason", "district_name"},
            "Динамика аномалий потребления по месяцам": {"period", "subscriber_id", "anomaly_reason", "district_name"},
            "Причины аномалий потребления": {"period", "subscriber_id", "district_name"},
            "Последние аномалии потребления": {"period", "subscriber_id", "anomaly_reason", "district_name"},
            "Помесячное потребление абонентов": {"period", "subscriber_id", "district_name"},
            "Отклонение от среднего по району": {"period", "subscriber_id", "anomaly_reason", "district_name"},
        }
        for name, tag_names in expected_tags.items():
            spec = specs_by_name[name]
            template_tags = spec["dataset_query"]["native"]["template-tags"]
            self.assertEqual(set(template_tags), tag_names)
            for tag_name in tag_names:
                self.assertIn(f"{{{{{tag_name}}}}}", spec["dataset_query"]["native"]["query"])
            self.assertTrue(spec["parameter_mappings"])
            self.assertEqual(
                {mapping["target"][1][1] for mapping in spec["parameter_mappings"]},
                tag_names,
            )
        self.assertIn(
            "sum(tasks_count) as \"Количество\"",
            specs_by_name["Статусы абонентов по типам проверок"]["dataset_query"]["native"]["query"],
        )
        self.assertIn(
            "v_bi_consumption_anomalies",
            specs_by_name["Последние аномалии потребления"]["dataset_query"]["native"]["query"],
        )
        self.assertIn(
            "v_bi_consumption_monthly",
            specs_by_name["Помесячное потребление абонентов"]["dataset_query"]["native"]["query"],
        )
        self.assertIn(
            "monthly_consumption_kwh",
            specs_by_name["Отклонение от среднего по району"]["dataset_query"]["native"]["query"],
        )
        for spec in specs:
            self.assertTrue(spec["display"])
            self.assertEqual(spec["dataset_query"]["database"], 42)
            self.assertEqual(spec["dataset_query"]["type"], "native")
            self.assertTrue(spec["dataset_query"]["native"]["query"].strip())

    def test_dashboard_specs_cover_both_dashboards_and_layout_cards(self) -> None:
        cards_by_name = {
            "Всего завершенных задач": 1,
            "Нарушения выявлены": 2,
            "Средняя длительность выполнения": 3,
            "Случаи несанкционированного потребления": 4,
            "Динамика выполненных задач по дням": 5,
            "Распределение по типам проверок": 6,
            "Результаты проверок": 7,
            "Рейтинг бригад по числу выполненных задач": 8,
            "Распределение абонентов по статусам": 9,
            "Объекты с автоматом и без автомата": 10,
            "Наиболее частые адреса проверок": 11,
            "Статусы абонентов по типам проверок": 12,
            "Таблица объектов и абонентов": 13,
            "Всего аномалий потребления": 14,
            "Абоненты с аномалиями потребления": 15,
            "Динамика аномалий потребления по месяцам": 16,
            "Причины аномалий потребления": 17,
            "Последние аномалии потребления": 18,
            "Помесячное потребление абонентов": 19,
            "Отклонение от среднего по району": 20,
        }
        specs = bootstrap.build_dashboard_specs(cards_by_name)
        names = [item["name"] for item in specs]
        self.assertEqual(names, ["Обзор операций", "Абоненты и объекты", "Аномалии потребления"])
        overview, subscribers, anomalies = specs
        self.assertEqual(
            [card["card_name"] for card in overview["cards"]],
            [
                "Всего завершенных задач",
                "Нарушения выявлены",
                "Средняя длительность выполнения",
                "Случаи несанкционированного потребления",
                "Динамика выполненных задач по дням",
                "Распределение по типам проверок",
                "Результаты проверок",
                "Рейтинг бригад по числу выполненных задач",
            ],
        )
        self.assertEqual(
            [card["card_name"] for card in subscribers["cards"]],
            [
                "Распределение абонентов по статусам",
                "Объекты с автоматом и без автомата",
                "Наиболее частые адреса проверок",
                "Статусы абонентов по типам проверок",
                "Таблица объектов и абонентов",
            ],
        )
        self.assertEqual(
            [card["card_name"] for card in anomalies["cards"]],
            [
                "Всего аномалий потребления",
                "Абоненты с аномалиями потребления",
                "Динамика аномалий потребления по месяцам",
                "Причины аномалий потребления",
                "Последние аномалии потребления",
                "Помесячное потребление абонентов",
                "Отклонение от среднего по району",
            ],
        )
        self.assertEqual(
            [card["card_id"] for card in overview["cards"] + subscribers["cards"] + anomalies["cards"]],
            list(range(1, 21)),
        )
        self.assertTrue(all("row" in card and "col" in card for card in overview["cards"]))
        self.assertTrue(all("size_x" in card and "size_y" in card for card in subscribers["cards"]))
        self.assertTrue(all("size_x" in card and "size_y" in card for card in anomalies["cards"]))
        self.assertEqual(
            [param["name"] for param in overview["parameters"]],
            ["Период", "Тип проверки", "Бригада"],
        )
        self.assertEqual(overview["parameters"][0]["type"], "date/single")
        self.assertEqual(
            [param["name"] for param in subscribers["parameters"]],
            ["Период", "Тип проверки", "Статус абонента", "Наличие автомата"],
        )
        self.assertEqual(subscribers["parameters"][0]["type"], "date/single")
        self.assertEqual(
            [param["name"] for param in anomalies["parameters"]],
            ["Период", "Абонент", "Район", "Причина аномалии"],
        )
        self.assertEqual(anomalies["parameters"][0]["type"], "date/single")
        for dashboard_spec in specs:
            covered = {
                mapping["parameter_id"]
                for card in dashboard_spec["cards"]
                for mapping in card["parameter_mappings"]
            }
            self.assertTrue(
                covered.issuperset({param["id"] for param in dashboard_spec["parameters"]}),
                msg=f"uncovered dashboard filters in {dashboard_spec['name']}",
            )
        for card in overview["cards"] + subscribers["cards"] + anomalies["cards"]:
            self.assertTrue(card["parameter_mappings"])
            self.assertTrue(all(mapping["target"][0] == "variable" for mapping in card["parameter_mappings"]))

    def test_run_bootstrap_ignores_global_dashboards_outside_collection(self) -> None:
        client = DashboardScopeClient()

        bootstrap.run_bootstrap(client)

        create_dashboard_calls = [item for item in client.calls if item[0] == "create_dashboard"]
        self.assertEqual(len(create_dashboard_calls), 3)
        self.assertNotIn(("update_dashboard", 900), [(item[0], item[1]) for item in client.calls if item[0] == "update_dashboard"])

    def test_run_bootstrap_handles_paginated_lists_and_card_only_lookup(self) -> None:
        client = UpdateCardPayloadClient()

        bootstrap.run_bootstrap(client)

        update_card_calls = [item for item in client.calls if item[0] == "update_card"]
        self.assertTrue(update_card_calls)
        self.assertEqual(update_card_calls[0][1], 777)
        self.assertNotIn(501, [item[1] for item in update_card_calls])
        self.assertTrue(
            all(call[2]["visualization_settings"] == {} for call in update_card_calls),
            msg="update payloads must include empty visualization_settings",
        )

    def test_run_bootstrap_sets_empty_visualization_settings_on_new_cards(self) -> None:
        client = CreateCardPayloadClient()

        bootstrap.run_bootstrap(client)

        create_card_calls = [item for item in client.calls if item[0] == "create_card"]
        self.assertTrue(create_card_calls)
        self.assertTrue(
            all(call[1]["visualization_settings"] == {} for call in create_card_calls),
            msg="create payloads must include empty visualization_settings",
        )

    def test_build_dashcards_payload_reuses_existing_ids_and_creates_negative_ids_for_new_cards(self) -> None:
        existing_dashcards = [
            {"id": 901, "card_id": 1, "row": 99, "col": 99, "size_x": 1, "size_y": 1},
            {"id": 999, "card_id": 9999, "row": 1, "col": 1, "size_x": 1, "size_y": 1},
        ]
        desired_cards = [
            {
                "card_name": "Всего завершенных задач",
                "card_id": 1,
                "row": 0,
                "col": 0,
                "size_x": 6,
                "size_y": 3,
                "parameter_mappings": bootstrap.build_parameter_mappings(["period"]),
            },
            {
                "card_name": "Нарушения выявлены",
                "card_id": 2,
                "row": 0,
                "col": 6,
                "size_x": 6,
                "size_y": 3,
                "parameter_mappings": bootstrap.build_parameter_mappings(["period"]),
            },
        ]

        payload = bootstrap.build_dashcards_payload(existing_dashcards, desired_cards)

        self.assertEqual(
            payload,
            [
                {
                    "id": 901,
                    "card_id": 1,
                    "row": 0,
                    "col": 0,
                    "size_x": 6,
                    "size_y": 3,
                    "parameter_mappings": bootstrap.build_parameter_mappings(["period"]),
                },
                {
                    "id": -1,
                    "card_id": 2,
                    "row": 0,
                    "col": 6,
                    "size_x": 6,
                    "size_y": 3,
                    "parameter_mappings": bootstrap.build_parameter_mappings(["period"]),
                },
            ],
        )

    def test_run_bootstrap_updates_dashboards_via_put_with_dashcards(self) -> None:
        client = ExistingDashboardClient()

        bootstrap.run_bootstrap(client)

        update_dashboard_calls = [item for item in client.calls if item[0] == "update_dashboard"]
        self.assertEqual(len(update_dashboard_calls), 3)
        overview_update = next(call for call in update_dashboard_calls if call[1] == 301)
        dashcards = overview_update[2]["dashcards"]
        self.assertEqual(dashcards[0]["id"], 901)
        self.assertEqual(dashcards[0]["card_id"], 401)
        self.assertEqual(dashcards[0]["row"], 0)
        self.assertEqual(dashcards[1]["id"], -1)
        self.assertEqual(dashcards[-1]["id"], -7)
        self.assertTrue(
            all("card_id" not in mapping for dashcard in dashcards for mapping in dashcard["parameter_mappings"]),
            msg="dashboard parameter mappings must not be pre-bound to card ids for dashboard PUT payloads",
        )

    def test_run_bootstrap_updates_existing_database_and_syncs_it(self) -> None:
        client = RecordingClient()

        bootstrap.run_bootstrap(client)

        calls = [item[0] for item in client.calls]
        self.assertIn("update_database", calls)
        self.assertIn("sync_database", calls)
        self.assertNotIn("create_database", calls)
        update_calls = [item for item in client.calls if item[0] == "update_database"]
        self.assertEqual(len(update_calls), 1)
        self.assertEqual(update_calls[0][1], 7)
        self.assertIn(("sync_database", 7), client.calls)

    def test_collection_name_is_fixed(self) -> None:
        self.assertEqual(bootstrap.default_collection_name(), "Аналитика энергоконтроля")


if __name__ == "__main__":
    unittest.main()
