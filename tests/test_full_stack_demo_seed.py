import os
import unittest

from tests.demo_seed_client import ApiClient
from tests.demo_seed_data import build_demo_plan
from tests.demo_seed_workflow import DemoSeedWorkflow
from tests.demo_user_seed import seed_demo_inspectors


@unittest.skipUnless(
    os.environ.get("ENERGO_E2E_RUN_FULL_STACK") == "1",
    "set ENERGO_E2E_RUN_FULL_STACK=1 to run the live full-stack demo seed test",
)
class FullStackDemoSeedE2ETests(unittest.TestCase):
    def test_demo_seed_flow_creates_completed_tasks_and_report(self) -> None:
        plan = build_demo_plan()
        seed_demo_inspectors(
            plan,
            compose_file=os.environ.get("ENERGO_E2E_COMPOSE_FILE", "docker-compose.dev.yml"),
            project_name=os.environ.get("ENERGO_E2E_PROJECT_NAME", "energy-control-system"),
        )
        workflow = DemoSeedWorkflow(ApiClient(os.environ.get("ENERGO_E2E_BASE_URL", "http://localhost")))

        summary = workflow.run_full_demo(plan)

        self.assertIn("Completed Cases: 30", summary)
        self.assertIn("Report ID:", summary)


if __name__ == "__main__":
    unittest.main()
