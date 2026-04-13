import urllib.error
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from tests.demo_seed_client import ApiError, poll_until


MOSCOW = timezone(timedelta(hours=3))
STACK_READY_PATHS = (
    "/api/brigade-service/brigades",
    "/api/subscriber-service/subscribers",
    "/api/task-service/tasks",
    "/api/inspection-service/inspections",
    "/api/analytics-service/reports",
)


@dataclass(frozen=True)
class CaseRunResult:
    brigade_id: int
    subscriber_id: int
    object_id: int
    contract_id: int
    task_id: int
    inspection_id: int


class DemoSeedWorkflow:
    def __init__(self, client) -> None:
        self.client = client

    def poll_transient(self, fetch, is_ready, timeout_seconds: float, interval_seconds: float, timeout_message: str):
        last_error = None

        def fetch_or_none():
            nonlocal last_error

            try:
                value = fetch()
            except ApiError as error:
                if error.status is not None and error.status < 500:
                    raise

                last_error = error
                return None
            except urllib.error.URLError as error:
                last_error = error
                return None

            last_error = None
            return value

        def on_timeout():
            if last_error is not None:
                raise TimeoutError(f"{timeout_message}: {last_error}") from last_error
            raise TimeoutError(timeout_message)

        return poll_until(
            fetch=fetch_or_none,
            is_ready=is_ready,
            timeout_seconds=timeout_seconds,
            interval_seconds=interval_seconds,
            on_timeout=on_timeout,
        )

    def assert_stack_ready(self) -> None:
        self.poll_transient(
            fetch=self._probe_stack_ready,
            is_ready=lambda value: value is True,
            timeout_seconds=120.0,
            interval_seconds=2.0,
            timeout_message="stack did not become ready",
        )

    def _probe_stack_ready(self) -> bool:
        for path in STACK_READY_PATHS:
            self.client.request_json("GET", path)

        return True

    def create_brigades(self, brigades):
        created = []
        for brigade in brigades:
            response = self.client.request_json(
                "POST",
                "/api/brigade-service/brigades",
                {"InspectorIDs": list(brigade.inspector_ids)},
            )
            created.append(response)
        return created

    def build_subscriber_payload(self, case) -> dict:
        return {
            "AccountNumber": case.subscriber.account_number,
            "Surname": case.subscriber.surname,
            "Name": case.subscriber.name,
            "Patronymic": case.subscriber.patronymic,
            "PhoneNumber": case.subscriber.phone_number,
            "Email": case.subscriber.email,
            "INN": case.subscriber.inn,
            "BirthDate": case.subscriber.birth_date,
            "Passport": {
                "Series": case.subscriber.passport_series,
                "Number": case.subscriber.passport_number,
                "IssuedBy": case.subscriber.passport_issued_by,
                "IssueDate": case.subscriber.passport_issue_date,
            },
        }

    def build_object_payload(self, case) -> dict:
        return {
            "Address": case.object_data.address,
            "HaveAutomaton": case.object_data.have_automaton,
            "Devices": [
                {
                    "Type": case.object_data.device_type,
                    "Number": case.object_data.device_number,
                    "PlaceType": case.object_data.device_place_type,
                    "PlaceDescription": case.object_data.device_place_description,
                    "Seals": [
                        {"Number": case.object_data.seal_numbers[0], "Place": "крышка клеммной колодки"},
                        {"Number": case.object_data.seal_numbers[1], "Place": "вводной автомат"},
                    ],
                }
            ],
        }

    def build_contract_payload(self, case, subscriber_id: int, object_id: int) -> dict:
        return {
            "Number": case.contract_number,
            "SubscriberID": subscriber_id,
            "ObjectID": object_id,
            "SignDate": case.sign_date,
        }

    def build_task_payload(self, case, object_id: int) -> dict:
        return {
            "BrigadeID": None,
            "ObjectID": object_id,
            "PlanVisitAt": None,
            "Comment": case.task_comment,
        }

    def build_finish_payload(self, case, device_id: int, seal_ids: list[int], energy_action_at: datetime) -> dict:
        type_map = {
            "limitation": 1,
            "resumption": 2,
            "verification": 3,
            "unauthorized_connection": 4,
        }
        resolution_map = {
            "limitation": 1,
            "resumption": 2,
            "verification": 1,
            "unauthorized_connection": 1,
        }
        method_map = {
            "limitation": "Отключение коммутационным аппаратом на фасаде здания.",
            "resumption": "Восстановление схемы электроснабжения в этажном щите.",
            "verification": "Осмотр прибора учета и проверка схемы подключения.",
            "unauthorized_connection": "Осмотр прибора учета и проверка схемы подключения.",
        }
        reason_type_map = {
            "limitation": 3,
            "resumption": 2,
            "verification": 3,
            "unauthorized_connection": 3,
        }

        inspection_kind = case.inspection_kind
        is_verification = inspection_kind == "verification"
        is_unauthorized = inspection_kind == "unauthorized_connection"

        payload = {
            "Type": type_map[inspection_kind],
            "Resolution": resolution_map[inspection_kind],
            "LimitReason": None,
            "Method": method_map[inspection_kind],
            "MethodBy": 2,
            "ReasonType": reason_type_map[inspection_kind],
            "ReasonDescription": None,
            "IsRestrictionChecked": is_verification or is_unauthorized,
            "IsViolationDetected": is_verification or is_unauthorized,
            "IsExpenseAvailable": is_verification or is_unauthorized,
            "ViolationDescription": (
                "После введенного ограничения зафиксирован расход электроэнергии."
                if is_verification
                else None
            ),
            "IsUnauthorizedConsumers": is_unauthorized,
            "UnauthorizedDescription": (
                "Обнаружено самовольное подключение вводного кабеля в обход прибора учета."
                if is_unauthorized
                else None
            ),
            "UnauthorizedExplanation": (
                "Абонент пояснил, что подключение выполнено без согласования."
                if is_unauthorized
                else None
            ),
            "EnergyActionAt": energy_action_at.isoformat(),
            "InspectedDevices": [
                {
                    "DeviceID": device_id,
                    "Value": "1542.40",
                    "Consumption": "18.50",
                    "InspectedSeals": [
                        {"SealID": seal_ids[0], "IsBroken": is_verification or is_unauthorized},
                        {"SealID": seal_ids[1], "IsBroken": False},
                    ],
                }
            ],
        }

        return payload

    def report_period(self) -> tuple[str, str]:
        current = datetime.now(MOSCOW)
        period_start = current.date().isoformat()
        period_end = (current + timedelta(days=1)).date().isoformat()
        return period_start, period_end

    def create_basic_report(self):
        period_start, period_end = self.report_period()
        return self.client.request_json(
            "POST",
            f"/api/analytics-service/reports/basic/{period_start}/{period_end}",
        )

    def list_reports(self):
        return self.client.request_json("GET", "/api/analytics-service/reports")

    def wait_for_basic_report(self):
        return self.poll_transient(
            fetch=self.create_basic_report,
            is_ready=lambda value: isinstance(value, dict) and "ID" in value and value.get("Files"),
            timeout_seconds=60.0,
            interval_seconds=2.0,
            timeout_message="analytics-service did not create a basic report",
        )

    def run_full_demo(self, plan) -> str:
        self.assert_stack_ready()

        created_brigades = self.create_brigades(plan.brigades)
        brigade_ids = [item["ID"] for item in created_brigades]

        results = []
        for case in plan.cases:
            brigade_id = brigade_ids[case.brigade_slot]
            results.append(self.run_case(case, brigade_id=brigade_id))

        report = self.wait_for_basic_report()

        reports = self.list_reports()
        report_ids = [item["ID"] for item in reports]
        if report["ID"] not in report_ids:
            raise AssertionError(f"report {report['ID']} not found in GET /reports")

        report_file_id = report["Files"][0]["ID"]
        return self.build_summary(brigade_ids, results, report["ID"], report_file_id)

    def wait_for_inspection(self, task_id: int):
        return poll_until(
            lambda: self.client.request_json("GET", f"/api/inspection-service/inspections/task/{task_id}"),
            lambda value: value is not None,
            timeout_seconds=30.0,
        )

    def wait_for_task_done(self, task_id: int):
        return poll_until(
            lambda: self.client.request_json("GET", f"/api/task-service/tasks/{task_id}"),
            lambda value: value is not None and value["Status"] == 3,
            timeout_seconds=30.0,
        )

    def run_case(self, case, brigade_id: int) -> CaseRunResult:
        subscriber = self.client.request_json(
            "POST",
            "/api/subscriber-service/subscribers",
            self.build_subscriber_payload(case),
        )
        obj = self.client.request_json(
            "POST",
            "/api/subscriber-service/objects",
            self.build_object_payload(case),
        )
        contract = self.client.request_json(
            "POST",
            "/api/subscriber-service/contracts",
            self.build_contract_payload(case, subscriber["ID"], obj["ID"]),
        )
        task = self.client.request_json(
            "POST",
            "/api/task-service/tasks",
            self.build_task_payload(case, obj["ID"]),
        )
        self.client.request_json(
            "PATCH",
            "/api/task-service/tasks/assign",
            {"TaskID": task["ID"], "BrigadeID": brigade_id},
        )
        started_task = self.client.request_json(
            "PATCH",
            f"/api/task-service/tasks/{task['ID']}/start",
        )

        inspection = self.wait_for_inspection(started_task["ID"])

        device = obj["Devices"][0]
        finish_payload = self.build_finish_payload(
            case,
            device_id=device["ID"],
            seal_ids=[seal["ID"] for seal in device["Seals"]],
            energy_action_at=datetime.now(MOSCOW),
        )
        self.client.request_json(
            "PATCH",
            f"/api/inspection-service/inspections/{inspection['ID']}/finish",
            finish_payload,
        )
        done_task = self.wait_for_task_done(task["ID"])

        if done_task["Status"] != 3:
            raise AssertionError(f"task {task['ID']} did not reach done status: {done_task}")

        return CaseRunResult(
            brigade_id=brigade_id,
            subscriber_id=subscriber["ID"],
            object_id=obj["ID"],
            contract_id=contract["ID"],
            task_id=task["ID"],
            inspection_id=inspection["ID"],
        )

    def build_summary(self, brigade_ids: list[int], results: list[CaseRunResult], report_id: int, report_file_id: int) -> str:
        completed_tasks = ", ".join(str(result.task_id) for result in results[:10])
        if len(results) > 10:
            completed_tasks = f"{completed_tasks}, ..."

        return "\n".join(
            [
                f"Brigades: {', '.join(str(item) for item in brigade_ids)}",
                f"Completed Cases: {len(results)}",
                f"Sample Task IDs: {completed_tasks or 'none'}",
                f"Report ID: {report_id}",
                f"Report File ID: {report_file_id}",
            ]
        )
