import unittest

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
        self.calls.append(("update_dashboard", dashboard_id, payload["name"]))
        return {"id": dashboard_id}

    def replace_dashboard_cards(self, dashboard_id, payload):
        self.calls.append(("replace_dashboard_cards", dashboard_id, payload["cards"]))


class BootstrapSpecTests(unittest.TestCase):
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
            ],
        )
        sql_text = "\n".join(item["dataset_query"]["native"]["query"] for item in specs)
        self.assertIn("v_bi_tasks_daily", sql_text)
        self.assertIn("v_bi_brigade_performance", sql_text)
        self.assertIn("v_bi_inspection_results", sql_text)
        self.assertIn("v_bi_subscriber_object_profile", sql_text)
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
        }
        specs_by_name = {item["name"]: item for item in specs}
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
        }
        specs = bootstrap.build_dashboard_specs(cards_by_name)
        names = [item["name"] for item in specs]
        self.assertEqual(names, ["Обзор операций", "Абоненты и объекты"])
        overview, subscribers = specs
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
            [card["card_id"] for card in overview["cards"] + subscribers["cards"]],
            list(range(1, 14)),
        )
        self.assertTrue(all("row" in card and "col" in card for card in overview["cards"]))
        self.assertTrue(all("size_x" in card and "size_y" in card for card in subscribers["cards"]))
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
        for card in overview["cards"] + subscribers["cards"]:
            self.assertTrue(card["parameter_mappings"])
            self.assertTrue(all(mapping["target"][0] == "variable" for mapping in card["parameter_mappings"]))

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
