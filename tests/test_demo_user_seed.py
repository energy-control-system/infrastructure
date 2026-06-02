import unittest
from unittest.mock import patch

from tests.demo_seed_data import build_demo_plan
from tests.demo_user_seed import render_demo_inspector_sql, seed_demo_inspectors


class DemoUserSeedTests(unittest.TestCase):
    def test_render_demo_inspector_sql_creates_user_schema_and_inspectors(self) -> None:
        sql = render_demo_inspector_sql(build_demo_plan())

        self.assertIn("create table if not exists users", sql)
        self.assertIn("delete from users where id in (101, 102, 201, 202, 301, 302)", sql)
        self.assertIn("demo.inspector.101@energo.local", sql)
        self.assertIn("overriding system value", sql)

    def test_seed_demo_inspectors_runs_psql_in_dev_stack(self) -> None:
        plan = build_demo_plan()

        with patch("tests.demo_user_seed.subprocess.run") as run:
            seed_demo_inspectors(
                plan,
                compose_file="docker-compose.dev.yml",
                project_name="energy-control-system",
            )

        command = run.call_args.args[0]
        self.assertEqual(
            [
                "docker",
                "compose",
                "-f",
                "docker-compose.dev.yml",
                "-p",
                "energy-control-system",
                "exec",
                "-T",
                "postgres",
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "postgres",
                "-d",
                "user_service",
            ],
            command,
        )
        self.assertIn("demo.inspector.101@energo.local", run.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
