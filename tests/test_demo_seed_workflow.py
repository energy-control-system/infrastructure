import unittest
from datetime import datetime, timezone, timedelta

from tests.demo_seed_data import build_demo_plan
from tests.demo_seed_workflow import DemoSeedWorkflow


MOSCOW = timezone(timedelta(hours=3))


class _FakeClient:
    def __init__(self) -> None:
        self.calls = []

    def request_json(self, method: str, path: str, payload=None):
        self.calls.append((method, path, payload))
        if path == "/api/brigade-service/brigades":
            return {"ID": 1, "Inspectors": [{"ID": 101}, {"ID": 102}]}
        raise AssertionError(f"unexpected path {path}")


class DemoSeedWorkflowTests(unittest.TestCase):
    def test_create_brigades_posts_inspector_ids(self) -> None:
        plan = build_demo_plan()
        client = _FakeClient()
        workflow = DemoSeedWorkflow(client)

        brigades = workflow.create_brigades(plan.brigades)

        self.assertEqual(3, len(brigades))
        self.assertEqual(
            ("POST", "/api/brigade-service/brigades", {"InspectorIDs": [101, 102]}),
            client.calls[0],
        )

    def test_build_finish_payload_for_limitation(self) -> None:
        plan = build_demo_plan()
        workflow = DemoSeedWorkflow(_FakeClient())
        energy_action_at = datetime(2026, 4, 13, 10, 30, tzinfo=MOSCOW)

        payload = workflow.build_finish_payload(
            plan.cases[0],
            device_id=77,
            seal_ids=[501, 502],
            energy_action_at=energy_action_at,
        )

        self.assertEqual(1, payload["Type"])
        self.assertEqual(1, payload["Resolution"])
        self.assertEqual("Отключение коммутационным аппаратом на фасаде здания.", payload["Method"])
        self.assertEqual(2, payload["MethodBy"])
        self.assertEqual(77, payload["InspectedDevices"][0]["DeviceID"])
        self.assertEqual([501, 502], [item["SealID"] for item in payload["InspectedDevices"][0]["InspectedSeals"]])

    def test_build_finish_payload_for_verification_violation(self) -> None:
        plan = build_demo_plan()
        workflow = DemoSeedWorkflow(_FakeClient())
        energy_action_at = datetime(2026, 4, 13, 10, 30, tzinfo=MOSCOW)

        payload = workflow.build_finish_payload(
            plan.cases[16],
            device_id=88,
            seal_ids=[701, 702],
            energy_action_at=energy_action_at,
        )

        self.assertEqual(3, payload["Type"])
        self.assertTrue(payload["IsRestrictionChecked"])
        self.assertTrue(payload["IsViolationDetected"])
        self.assertTrue(payload["IsExpenseAvailable"])
        self.assertEqual("После введенного ограничения зафиксирован расход электроэнергии.", payload["ViolationDescription"])


if __name__ == "__main__":
    unittest.main()
