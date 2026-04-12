import unittest

import bootstrap


class BootstrapSpecTests(unittest.TestCase):
    def test_question_specs_reference_bi_views(self) -> None:
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
            ["Период", "Тип проверки", "Бригада", "Статус абонента", "Наличие автомата"],
        )

    def test_collection_name_is_fixed(self) -> None:
        self.assertEqual(bootstrap.default_collection_name(), "Аналитика энергоконтроля")


if __name__ == "__main__":
    unittest.main()
