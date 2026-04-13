import re
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import patch

from tests.demo_seed_data import MIX, build_demo_plan


class DemoSeedDataTests(unittest.TestCase):
    def test_build_demo_plan_supports_reduced_case_count(self) -> None:
        plan = build_demo_plan(case_count=5)

        self.assertEqual(3, len(plan.brigades))
        self.assertEqual(5, len(plan.cases))

    def test_build_demo_plan_rejects_invalid_case_count(self) -> None:
        with self.subTest("negative"):
            with self.assertRaises(ValueError):
                build_demo_plan(case_count=-1)

        with self.subTest("over_max_supported"):
            with self.assertRaises(ValueError):
                build_demo_plan(case_count=len(MIX) + 1)

    def test_build_demo_plan_rejects_case_count_when_datasets_shrink(self) -> None:
        with patch("tests.demo_seed_data.SURNAMES", ("Only",)):
            with self.assertRaises(ValueError):
                build_demo_plan(case_count=2)

    def test_demo_seed_dataclasses_are_frozen(self) -> None:
        plan = build_demo_plan(case_count=1)

        with self.assertRaises(FrozenInstanceError):
            plan.cases = ()

        with self.assertRaises(FrozenInstanceError):
            plan.brigades[0].label = "Changed"

    def test_build_demo_plan_has_expected_shape(self) -> None:
        plan = build_demo_plan()

        self.assertEqual(3, len(plan.brigades))
        self.assertTrue(all(len(brigade.inspector_ids) == 2 for brigade in plan.brigades))
        self.assertEqual(30, len(plan.cases))

    def test_build_demo_plan_has_expected_mix(self) -> None:
        plan = build_demo_plan()

        counts = {}
        for case in plan.cases:
            counts[case.inspection_kind] = counts.get(case.inspection_kind, 0) + 1

        self.assertEqual(
            {
                "limitation": 8,
                "resumption": 8,
                "verification": 8,
                "unauthorized_connection": 6,
            },
            counts,
        )

    def test_build_demo_plan_keeps_natural_fields_unique_where_required(self) -> None:
        plan = build_demo_plan()

        account_numbers = {case.subscriber.account_number for case in plan.cases}
        passport_keys = {
            (case.subscriber.passport_series, case.subscriber.passport_number)
            for case in plan.cases
        }
        addresses = {case.object_data.address for case in plan.cases}
        contract_numbers = {case.contract_number for case in plan.cases}
        device_numbers = {case.object_data.device_number for case in plan.cases}
        seal_numbers = {
            seal_number
            for case in plan.cases
            for seal_number in case.object_data.seal_numbers
        }

        self.assertEqual(30, len(account_numbers))
        self.assertEqual(30, len(passport_keys))
        self.assertEqual(30, len(addresses))
        self.assertEqual(30, len(contract_numbers))
        self.assertEqual(30, len(device_numbers))
        self.assertEqual(60, len(seal_numbers))

    def test_build_demo_plan_matches_subscriber_service_contracts(self) -> None:
        plan = build_demo_plan()
        account_number_pattern = re.compile(r"^[А-ЯЁ][А-ЯЁ0-9-]{2,18}[0-9]$")
        russian_name_pattern = re.compile(r"^[А-ЯЁа-яё -]+$")
        phone_pattern = re.compile(r"^(?:\+7|7|8)\d{10}$")

        for case in plan.cases:
            with self.subTest(account_number=case.subscriber.account_number):
                self.assertRegex(case.subscriber.account_number, account_number_pattern)
                self.assertNotIn("--", case.subscriber.account_number)
                self.assertRegex(case.subscriber.surname, russian_name_pattern)
                self.assertRegex(case.subscriber.name, russian_name_pattern)
                self.assertRegex(case.subscriber.patronymic, russian_name_pattern)
                self.assertRegex(case.subscriber.phone_number, phone_pattern)
                self.assertRegex(case.subscriber.inn, r"^\d{10}(\d{2})?$")
                self.assertRegex(case.subscriber.birth_date, r"^\d{4}-\d{2}-\d{2}$")
                self.assertRegex(case.subscriber.passport_series, r"^\d{4}$")
                self.assertRegex(case.subscriber.passport_number, r"^\d{6}$")
                self.assertRegex(case.subscriber.passport_issue_date, r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
