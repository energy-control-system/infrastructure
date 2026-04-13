import unittest

from tests.demo_seed_data import build_demo_plan


class DemoSeedDataTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
