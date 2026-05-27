import json
import unittest
from datetime import date
from unittest.mock import patch

from year_demo_seed import (
    DEFAULT_BASE_ID,
    DEFAULT_ROWS,
    build_year_cases,
    estimate_anomaly_reasons,
    render_brigade_sql,
    render_clickhouse_json_lines,
    render_inspection_sql,
    render_subscriber_sql,
    render_task_sql,
    render_user_sql,
    run_seed,
)


class YearDemoSeedTests(unittest.TestCase):
    def test_default_plan_contains_one_thousand_checks(self) -> None:
        self.assertEqual(1000, DEFAULT_ROWS)
        self.assertEqual(1000, len(build_year_cases()))

    def test_build_year_cases_spreads_workload_across_year(self) -> None:
        cases = build_year_cases(rows=1200, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)

        self.assertEqual(1200, len(cases))
        self.assertEqual(date(2025, 1, 1), cases[0].visit_at.date())
        self.assertEqual(date(2025, 12, 31), cases[-1].visit_at.date())
        self.assertEqual(12, len({case.visit_at.month for case in cases}))
        self.assertEqual(4, len({case.inspection_kind for case in cases}))
        self.assertLess(len({case.account_number for case in cases}), 1200)
        self.assertLess(len({case.device_number for case in cases}), 1200)

    def test_build_year_cases_has_variable_daily_workload(self) -> None:
        cases = build_year_cases(rows=1200, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)
        daily_counts = {}
        for case in cases:
            day = case.visit_at.date()
            daily_counts[day] = daily_counts.get(day, 0) + 1

        self.assertEqual(365, len(daily_counts))
        self.assertGreaterEqual(min(daily_counts.values()), 1)
        self.assertGreater(max(daily_counts.values()), min(daily_counts.values()))
        self.assertGreaterEqual(max(daily_counts.values()), 4)

    def test_build_year_cases_reuses_subscribers_for_history(self) -> None:
        cases = build_year_cases(rows=1000, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)

        self.assertLess(len({case.subscriber_id for case in cases}), len(cases))
        self.assertLess(len({case.object_id for case in cases}), len(cases))
        self.assertGreaterEqual(
            max(sum(1 for case in cases if case.subscriber_id == subscriber_id) for subscriber_id in {case.subscriber_id for case in cases}),
            6,
        )

    def test_build_year_cases_uses_only_male_full_names(self) -> None:
        cases = build_year_cases(rows=1000, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)

        self.assertFalse({case.name for case in cases} & {"Марина", "Елена"})
        self.assertTrue(all(case.surname.endswith("ов") or case.surname.endswith("ев") or case.surname.endswith("ин") for case in cases))
        self.assertTrue(all(case.patronymic.endswith(("ич", "ыч")) for case in cases))

    def test_build_year_cases_produces_multiple_anomaly_reasons(self) -> None:
        cases = build_year_cases(rows=1000, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)

        self.assertGreaterEqual(
            estimate_anomaly_reasons(cases),
            {
                "Скачок относительно истории абонента",
                "Провал относительно истории абонента",
                "Выше среднего по району",
                "Ниже среднего по району",
            },
        )

    def test_render_postgres_sql_targets_service_tables(self) -> None:
        cases = build_year_cases(rows=2, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)

        subscriber_sql = render_subscriber_sql(cases)
        brigade_sql = render_brigade_sql()
        task_sql = render_task_sql(cases)
        inspection_sql = render_inspection_sql(cases)
        user_sql = render_user_sql()

        self.assertIn("insert into subscribers", subscriber_sql)
        self.assertIn("insert into contracts", subscriber_sql)
        self.assertIn("insert into brigades", brigade_sql)
        self.assertIn("insert into tasks", task_sql)
        self.assertIn("insert into inspections", inspection_sql)
        self.assertIn("insert into inspected_devices", inspection_sql)
        self.assertIn("insert into users", user_sql)
        self.assertIn("role_id", user_sql)
        self.assertIn("2025-01-01T", task_sql)

    def test_render_user_sql_seeds_demo_inspectors_for_brigades(self) -> None:
        user_sql = render_user_sql()

        self.assertIn("delete from users where id in", user_sql)
        self.assertIn("910101", user_sql)
        self.assertIn("910102", user_sql)
        self.assertIn("year.demo.inspector.910101@energo.local", user_sql)
        self.assertIn("Инспектор", user_sql)

    def test_render_clickhouse_json_lines_matches_finished_tasks_schema(self) -> None:
        cases = build_year_cases(rows=1, start_date=date(2025, 1, 1), base_id=DEFAULT_BASE_ID)

        rows = [json.loads(line) for line in render_clickhouse_json_lines(cases).splitlines()]

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual(DEFAULT_BASE_ID, row["task_id"])
        self.assertIn(row["subscriber_status"], {"active", "violator"})
        self.assertEqual(2, len(row["brigade_inspectors"]))
        self.assertEqual(1, len(row["inspected_devices"]))
        self.assertRegex(row["finished_at"], r"^2025-01-01 \d{2}:\d{2}:00$")

    def test_run_seed_executes_expected_database_commands(self) -> None:
        with patch("year_demo_seed.subprocess.run") as run:
            run_seed(
                rows=2,
                start_date=date(2025, 1, 1),
                compose_file="docker-compose.dev.yml",
                project_name="energy-control-system",
                random_seed=123,
            )

        commands = [call.args[0] for call in run.call_args_list]
        joined = "\n".join(" ".join(command) for command in commands)
        self.assertIn("-p energy-control-system", joined)
        self.assertIn("subscriber_service", joined)
        self.assertIn("brigade_service", joined)
        self.assertIn("task_service", joined)
        self.assertIn("inspection_service", joined)
        self.assertIn("user_service", joined)
        self.assertIn("analytics_service.finished_tasks", joined)
        self.assertIn("--port 9123", joined)
        self.assertEqual(7, len(commands))


if __name__ == "__main__":
    unittest.main()
