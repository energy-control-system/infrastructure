import os
import unittest

from tests.demo_seed_client import ApiClient
from tests.demo_seed_data import build_demo_plan
from tests.demo_seed_workflow import DemoSeedWorkflow


@unittest.skipUnless(
    os.environ.get("ENERGO_E2E_RUN_FULL_STACK") == "1",
    "set ENERGO_E2E_RUN_FULL_STACK=1 to run the live full-stack demo seed test",
)
class FullStackDemoSeedE2ETests(unittest.TestCase):
    def test_demo_seed_flow_creates_completed_tasks_and_report(self) -> None:
        workflow = DemoSeedWorkflow(ApiClient(os.environ.get("ENERGO_E2E_BASE_URL", "http://localhost")))

        summary = workflow.run_full_demo(build_demo_plan())

        self.assertIn("Completed Cases: 30", summary)
        self.assertIn("Report ID:", summary)


if __name__ == "__main__":
    unittest.main()
