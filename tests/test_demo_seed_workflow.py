import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from tests.demo_seed_data import build_demo_plan
from tests.demo_seed_workflow import CaseRunResult, DemoSeedWorkflow


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

    def test_build_finish_payload_for_resumption(self) -> None:
        plan = build_demo_plan()
        workflow = DemoSeedWorkflow(_FakeClient())
        energy_action_at = datetime(2026, 4, 13, 10, 30, tzinfo=MOSCOW)

        payload = workflow.build_finish_payload(
            plan.cases[8],
            device_id=79,
            seal_ids=[601, 602],
            energy_action_at=energy_action_at,
        )

        self.assertEqual(2, payload["Type"])
        self.assertEqual(2, payload["Resolution"])
        self.assertEqual("Восстановление схемы электроснабжения в этажном щите.", payload["Method"])
        self.assertEqual(2, payload["ReasonType"])
        self.assertEqual(79, payload["InspectedDevices"][0]["DeviceID"])
        self.assertFalse(payload["IsRestrictionChecked"])
        self.assertFalse(payload["IsViolationDetected"])

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

    def test_report_period_uses_single_moscow_timestamp(self) -> None:
        workflow = DemoSeedWorkflow(_FakeClient())
        captured_now = datetime(2026, 4, 13, 23, 30, tzinfo=MOSCOW)

        with patch("tests.demo_seed_workflow.datetime") as mock_datetime:
            mock_datetime.now.return_value = captured_now

            period_start, period_end = workflow.report_period()

        self.assertEqual("2026-04-13", period_start)
        self.assertEqual("2026-04-14", period_end)
        mock_datetime.now.assert_called_once_with(MOSCOW)

    def test_run_case_executes_api_flow_in_order(self) -> None:
        client = _PollingFlowClient()
        workflow = DemoSeedWorkflow(client)
        case = build_demo_plan().cases[0]

        result = workflow.run_case(case, brigade_id=7)

        self.assertEqual(61, result.task_id)
        self.assertEqual(71, result.inspection_id)
        self.assertEqual(
            [
                "/api/subscriber-service/subscribers",
                "/api/subscriber-service/objects",
                "/api/subscriber-service/contracts",
                "/api/task-service/tasks",
                "/api/task-service/tasks/assign",
                "/api/task-service/tasks/61/start",
                "/api/inspection-service/inspections/task/61",
                "/api/inspection-service/inspections/task/61",
                "/api/inspection-service/inspections/71/finish",
                "/api/task-service/tasks/61",
                "/api/task-service/tasks/61",
            ],
            [path for _, path, _ in client.calls],
        )
        self.assertEqual(
            {"TaskID": 61, "BrigadeID": 7},
            client.calls[4][2],
        )
        finish_payload = next(payload for _, path, payload in client.calls if path == "/api/inspection-service/inspections/71/finish")
        self.assertEqual(1, finish_payload["Type"])
        self.assertEqual(31, finish_payload["InspectedDevices"][0]["DeviceID"])
        self.assertEqual([41, 42], [item["SealID"] for item in finish_payload["InspectedDevices"][0]["InspectedSeals"]])
        self.assertEqual(2, len([path for _, path, _ in client.calls if path == "/api/inspection-service/inspections/task/61"]))
        self.assertEqual(2, len([path for _, path, _ in client.calls if path == "/api/task-service/tasks/61"]))

    def test_build_summary_contains_created_identifiers(self) -> None:
        workflow = DemoSeedWorkflow(_FlowClient())
        summary = workflow.build_summary(
            brigade_ids=[1, 2, 3],
            results=[],
            report_id=801,
            report_file_id=901,
        )

        self.assertIn("Brigades: 1, 2, 3", summary)
        self.assertIn("Report ID: 801", summary)
        self.assertIn("Report File ID: 901", summary)

    def test_build_summary_truncates_sample_task_ids(self) -> None:
        workflow = DemoSeedWorkflow(_FlowClient())
        results = [
            CaseRunResult(
                brigade_id=1,
                subscriber_id=10 + index,
                object_id=20 + index,
                contract_id=30 + index,
                task_id=100 + index,
                inspection_id=200 + index,
            )
            for index in range(12)
        ]

        summary = workflow.build_summary(
            brigade_ids=[7],
            results=results,
            report_id=801,
            report_file_id=901,
        )

        self.assertIn("Sample Task IDs: 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, ...", summary)

    def test_run_case_raises_when_task_never_reaches_done_status(self) -> None:
        workflow = DemoSeedWorkflow(_PollingFlowClient())
        case = build_demo_plan().cases[0]

        with patch.object(workflow, "wait_for_task_done", return_value={"ID": 61, "Status": 2}):
            with self.assertRaisesRegex(AssertionError, "did not reach done status"):
                workflow.run_case(case, brigade_id=7)

    def test_wait_for_task_done_polls_until_done_status(self) -> None:
        client = _TaskStatusClient([1, 2, 3])
        workflow = DemoSeedWorkflow(client)

        task = workflow.wait_for_task_done(61)

        self.assertEqual(3, task["Status"])
        self.assertEqual(
            [
                "/api/task-service/tasks/61",
                "/api/task-service/tasks/61",
                "/api/task-service/tasks/61",
            ],
            [path for _, path, _ in client.calls],
        )


class _FlowClient:
    def __init__(self) -> None:
        self.calls = []

    def request_json(self, method: str, path: str, payload=None):
        self.calls.append((method, path, payload))

        if path == "/api/subscriber-service/subscribers":
            return {"ID": 11}
        if path == "/api/subscriber-service/objects":
            return {"ID": 21, "Devices": [{"ID": 31, "Seals": [{"ID": 41}, {"ID": 42}]}]}
        if path == "/api/subscriber-service/contracts":
            return {"ID": 51}
        if path == "/api/task-service/tasks":
            return {"ID": 61, "Status": 1}
        if path == "/api/task-service/tasks/assign":
            return {"ID": 61, "BrigadeID": 7, "Status": 1}
        if path == "/api/task-service/tasks/61/start":
            return {"ID": 61, "BrigadeID": 7, "Status": 2}
        if path == "/api/inspection-service/inspections/task/61":
            return {"ID": 71, "TaskID": 61, "Status": 1}
        if path == "/api/inspection-service/inspections/71/finish":
            return {"ID": 901, "FileName": "акт.docx"}
        if path == "/api/task-service/tasks/61":
            return {"ID": 61, "Status": 3}

        raise AssertionError(f"unexpected path {path}")


class _PollingFlowClient(_FlowClient):
    def __init__(self) -> None:
        super().__init__()
        self._inspection_calls = 0
        self._task_done_calls = 0

    def request_json(self, method: str, path: str, payload=None):
        self.calls.append((method, path, payload))

        if path == "/api/subscriber-service/subscribers":
            return {"ID": 11}
        if path == "/api/subscriber-service/objects":
            return {"ID": 21, "Devices": [{"ID": 31, "Seals": [{"ID": 41}, {"ID": 42}]}]}
        if path == "/api/subscriber-service/contracts":
            return {"ID": 51}
        if path == "/api/task-service/tasks":
            return {"ID": 61, "Status": 1}
        if path == "/api/task-service/tasks/assign":
            return {"ID": 61, "BrigadeID": 7, "Status": 1}
        if path == "/api/task-service/tasks/61/start":
            return {"ID": 61, "BrigadeID": 7, "Status": 2}
        if path == "/api/inspection-service/inspections/task/61":
            self._inspection_calls += 1
            if self._inspection_calls == 1:
                return None
            return {"ID": 71, "TaskID": 61, "Status": 1}
        if path == "/api/inspection-service/inspections/71/finish":
            return {"ID": 901, "FileName": "акт.docx"}
        if path == "/api/task-service/tasks/61":
            self._task_done_calls += 1
            if self._task_done_calls == 1:
                return None
            return {"ID": 61, "Status": 3}

        raise AssertionError(f"unexpected path {path}")


class _TaskStatusClient(_FlowClient):
    def __init__(self, statuses: list[int]) -> None:
        super().__init__()
        self.statuses = statuses
        self.index = 0

    def request_json(self, method: str, path: str, payload=None):
        self.calls.append((method, path, payload))

        if path == "/api/task-service/tasks/61":
            status = self.statuses[self.index]
            self.index += 1
            return {"ID": 61, "Status": status}

        raise AssertionError(f"unexpected path {path}")


if __name__ == "__main__":
    unittest.main()
