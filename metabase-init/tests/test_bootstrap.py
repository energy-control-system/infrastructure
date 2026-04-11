import unittest

import bootstrap


class BootstrapSpecTests(unittest.TestCase):
    def test_question_specs_are_in_russian(self) -> None:
        specs = bootstrap.build_question_specs(database_id=42)
        names = [item["name"] for item in specs]
        self.assertIn("Всего завершенных задач", names)
        self.assertIn("Динамика выполненных задач по дням", names)
        self.assertIn("Распределение абонентов по статусам", names)

    def test_dashboard_specs_are_in_russian(self) -> None:
        specs = bootstrap.build_dashboard_specs({})
        names = [item["name"] for item in specs]
        self.assertEqual(names, ["Обзор операций", "Абоненты и объекты"])

    def test_collection_name_is_fixed(self) -> None:
        self.assertEqual(bootstrap.default_collection_name(), "Аналитика энергоконтроля")

    def test_find_by_name_returns_existing_item(self) -> None:
        existing = [{"id": 7, "name": "Обзор операций"}]
        item = bootstrap.find_by_name(existing, "Обзор операций")
        self.assertEqual(item["id"], 7)


if __name__ == "__main__":
    unittest.main()
