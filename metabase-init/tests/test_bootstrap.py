import io
import unittest
from contextlib import redirect_stdout

import bootstrap


class BootstrapSpecTests(unittest.TestCase):
    def test_question_specs_are_in_russian(self) -> None:
        specs = bootstrap.build_question_specs(database_id=42)
        names = [item["name"] for item in specs]
        self.assertIn("Всего завершенных задач", names)
        self.assertIn("Динамика выполненных задач по дням", names)
        self.assertIn("Распределение абонентов по статусам", names)
        for spec in specs:
            self.assertTrue(spec["display"])
            self.assertEqual(spec["dataset_query"]["database"], 42)
            self.assertEqual(spec["dataset_query"]["type"], "native")
            self.assertTrue(spec["dataset_query"]["native"]["query"].strip())

    def test_dashboard_specs_are_in_russian(self) -> None:
        cards_by_name = {
            "Всего завершенных задач": 501,
            "Динамика выполненных задач по дням": 902,
            "Распределение абонентов по статусам": 1337,
        }
        specs = bootstrap.build_dashboard_specs(cards_by_name)
        names = [item["name"] for item in specs]
        self.assertEqual(names, ["Обзор операций", "Абоненты и объекты"])
        overview, subscribers = specs
        self.assertTrue(overview["cards"])
        self.assertTrue(subscribers["cards"])
        self.assertEqual(
            [card["card_id"] for card in overview["cards"]],
            [501, 902],
        )
        self.assertEqual(
            [card["card_name"] for card in overview["cards"]],
            ["Всего завершенных задач", "Динамика выполненных задач по дням"],
        )
        self.assertEqual(
            [card["card_id"] for card in subscribers["cards"]],
            [1337],
        )
        self.assertEqual(
            [card["card_name"] for card in subscribers["cards"]],
            ["Распределение абонентов по статусам"],
        )

    def test_collection_name_is_fixed(self) -> None:
        self.assertEqual(bootstrap.default_collection_name(), "Аналитика энергоконтроля")

    def test_main_is_an_explicit_no_op_entrypoint(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = bootstrap.main()
        self.assertEqual(exit_code, 0)
        self.assertIn("no-op", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
