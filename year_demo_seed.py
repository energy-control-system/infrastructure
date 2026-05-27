#!/usr/bin/env python3
import argparse
import json
import random
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal


MOSCOW = timezone(timedelta(hours=3))
DEFAULT_BASE_ID = 900_000
DEFAULT_ROWS = 1000
DEFAULT_START_DATE = date(2025, 1, 1)
DEFAULT_COMPOSE_FILE = "docker-compose.dev.yml"
DEFAULT_RANDOM_SEED = 20250505
YEAR_DAYS = 365
ENTITY_ID_OFFSET = 20_000

BRIGADES = (
    (DEFAULT_BASE_ID + 1, (910_101, 910_102)),
    (DEFAULT_BASE_ID + 2, (910_201, 910_202)),
    (DEFAULT_BASE_ID + 3, (910_301, 910_302)),
)

SURNAMES = (
    "Иванов",
    "Петров",
    "Сидоров",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Волков",
    "Михайлов",
    "Федоров",
    "Морозов",
    "Виноградов",
    "Соколов",
)
NAMES = ("Алексей", "Дмитрий", "Сергей", "Павел", "Игорь", "Олег", "Виктор", "Николай")
PATRONYMICS = ("Алексеевич", "Дмитриевич", "Сергеевич", "Павлович", "Игоревич", "Олегович", "Викторович", "Николаевич")
STREETS = (
    "Центральный район, ул. Ленина",
    "Северный район, ул. Мира",
    "Южный район, ул. Победы",
    "Заречный район, ул. Гагарина",
    "Привокзальный район, ул. Кирова",
)
DEVICE_TYPES = ("Однофазный счетчик", "Трехфазный счетчик", "Интеллектуальный счетчик", "Контрольный счетчик")
INSPECTION_KINDS = ("limitation", "resumption", "verification", "unauthorized_connection")

TYPE_IDS = {"limitation": 1, "resumption": 2, "verification": 3, "unauthorized_connection": 4}
RESOLUTION_IDS = {"limitation": 1, "resumption": 3, "verification": 1, "unauthorized_connection": 2}
RESOLUTION_NAMES = {"limitation": "limited", "resumption": "resumed", "verification": "limited", "unauthorized_connection": "stopped"}
REASON_TYPE_IDS = {"limitation": 3, "resumption": 4, "verification": 3, "unauthorized_connection": 3}
REASON_TYPE_NAMES = {"limitation": "inspector_limited", "resumption": "resumed", "verification": "inspector_limited", "unauthorized_connection": "inspector_limited"}
METHODS = {
    "limitation": "Отключение коммутационным аппаратом на фасаде здания.",
    "resumption": "Восстановление схемы электроснабжения в этажном щите.",
    "verification": "Осмотр прибора учета и проверка схемы подключения.",
    "unauthorized_connection": "Фиксация самовольного подключения в обход прибора учета.",
}
DEMO_PASSWORD_HASH = "$2b$10$CwTycUXWue0Thq9StjUM0uJ8TGTSt1n1.Ki/hxL7s.1UTMwuY5M2G"


@dataclass(frozen=True)
class YearSeedCase:
    index: int
    seed_id: int
    entity_base_id: int
    customer_slot: int
    brigade_id: int
    inspector_ids: tuple[int, int]
    visit_at: datetime
    started_at: datetime
    finished_at: datetime
    inspection_kind: str
    account_number: str
    surname: str
    name: str
    patronymic: str
    phone_number: str
    email: str
    inn: str
    birth_date: date
    passport_series: str
    passport_number: str
    address: str
    device_type: str
    device_number: str
    device_place_type: int
    seal_numbers: tuple[str, str]
    contract_number: str
    consumption: Decimal
    reading_value: Decimal

    @property
    def subscriber_id(self) -> int:
        return self.entity_base_id + self.customer_slot

    @property
    def passport_id(self) -> int:
        return self.entity_base_id + self.customer_slot

    @property
    def object_id(self) -> int:
        return self.entity_base_id + self.customer_slot

    @property
    def device_id(self) -> int:
        return self.entity_base_id + self.customer_slot

    @property
    def first_seal_id(self) -> int:
        return (self.entity_base_id + self.customer_slot) * 2

    @property
    def second_seal_id(self) -> int:
        return (self.entity_base_id + self.customer_slot) * 2 + 1

    @property
    def contract_id(self) -> int:
        return self.entity_base_id + self.customer_slot

    @property
    def task_id(self) -> int:
        return self.seed_id

    @property
    def inspection_id(self) -> int:
        return self.seed_id

    @property
    def inspected_device_id(self) -> int:
        return self.seed_id

    @property
    def is_violation(self) -> bool:
        return self.inspection_kind in {"verification", "unauthorized_connection"}


def build_year_cases(
    rows: int = DEFAULT_ROWS,
    start_date: date = DEFAULT_START_DATE,
    base_id: int = DEFAULT_BASE_ID,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> list[YearSeedCase]:
    if rows <= 0:
        raise ValueError("rows must be positive")

    rng = random.Random(random_seed)
    entity_base_id = base_id + ENTITY_ID_OFFSET
    customer_count = min(max(80, rows // 8), 160)
    customer_slots = _customer_slots(rows, customer_count, rng)
    daily_workload = _daily_workload(rows, rng)
    cases = []
    index = 0
    for day_index, checks_count in enumerate(daily_workload):
        current_date = start_date + timedelta(days=day_index)
        for check_index in range(checks_count):
            customer_slot = customer_slots[index]
            visit_at = datetime.combine(
                current_date,
                time(rng.randint(7, 18), rng.randint(0, 59)),
                tzinfo=MOSCOW,
            )
            duration_minutes = rng.randint(25, 135)
            started_at = visit_at - timedelta(minutes=rng.randint(5, 35))
            finished_at = visit_at + timedelta(minutes=duration_minutes)
            brigade_id, inspector_ids = rng.choice(BRIGADES)
            kind = rng.choices(INSPECTION_KINDS, weights=(28, 21, 34, 17), k=1)[0]
            consumption = _consumption_for(customer_slot, visit_at.date(), rng)

            cases.append(
                YearSeedCase(
                    index=index,
                    seed_id=base_id + index,
                    entity_base_id=entity_base_id,
                    customer_slot=customer_slot,
                    brigade_id=brigade_id,
                    inspector_ids=inspector_ids,
                    visit_at=visit_at,
                    started_at=started_at,
                    finished_at=finished_at,
                    inspection_kind=kind,
                    account_number=f"ГД-{customer_slot + 1:06d}",
                    surname=SURNAMES[customer_slot % len(SURNAMES)],
                    name=NAMES[(customer_slot * 3) % len(NAMES)],
                    patronymic=PATRONYMICS[(customer_slot * 5) % len(PATRONYMICS)],
                    phone_number=f"+79{entity_base_id + customer_slot:09d}"[-12:],
                    email=f"year.demo.{customer_slot + 1:04d}@energo.local",
                    inn=f"7700{customer_slot + 1:08d}",
                    birth_date=date(1968 + customer_slot % 35, (customer_slot % 12) + 1, min((customer_slot % 27) + 1, 28)),
                    passport_series=f"{5200 + customer_slot % 700:04d}",
                    passport_number=f"{entity_base_id + customer_slot:06d}"[-6:],
                    address=f"{STREETS[customer_slot % len(STREETS)]}, д. {1 + customer_slot % 90}, кв. {1 + customer_slot}",
                    device_type=DEVICE_TYPES[customer_slot % len(DEVICE_TYPES)],
                    device_number=f"ГД-DEV-{customer_slot + 1:06d}",
                    device_place_type=(customer_slot % 3) + 1,
                    seal_numbers=(f"ГД-SEL-{customer_slot * 2 + 1:06d}", f"ГД-SEL-{customer_slot * 2 + 2:06d}"),
                    contract_number=f"ГД-ДОГ-{customer_slot + 1:06d}",
                    consumption=consumption,
                    reading_value=Decimal("1800.00") + Decimal(customer_slot * 33 + index * 5) + consumption,
                )
            )
            index += 1

    return cases


def _daily_workload(rows: int, rng: random.Random) -> list[int]:
    if rows < YEAR_DAYS:
        return [1] * rows

    workload = [1] * YEAR_DAYS
    remaining = rows - YEAR_DAYS
    weights = [rng.randint(1, 8) + (3 if day % 7 in (1, 2, 3) else 0) for day in range(YEAR_DAYS)]
    while remaining > 0:
        day_index = rng.choices(range(YEAR_DAYS), weights=weights, k=1)[0]
        extra = min(remaining, rng.randint(1, 4))
        workload[day_index] += extra
        remaining -= extra

    return workload


def _customer_slots(rows: int, customer_count: int, rng: random.Random) -> list[int]:
    slots = list(range(customer_count))
    while len(slots) < rows:
        batch = list(range(customer_count))
        rng.shuffle(batch)
        slots.extend(batch)
    rng.shuffle(slots)
    return slots[:rows]


def _consumption_for(customer_slot: int, visit_date: date, rng: random.Random) -> Decimal:
    baseline = Decimal(80 + (customer_slot % 37) * 4 + rng.randint(-18, 28))
    seasonal = Decimal(1) + Decimal((visit_date.month in (1, 2, 7, 8)) * rng.uniform(0.10, 0.28)).quantize(Decimal("0.01"))
    consumption = baseline * seasonal

    if customer_slot % 29 == 0:
        consumption = Decimal(650 + rng.randint(0, 180))
    elif customer_slot % 17 == 0 and visit_date.month in (8, 9):
        consumption *= Decimal(rng.uniform(3.1, 4.4)).quantize(Decimal("0.01"))
    elif customer_slot % 19 == 0 and visit_date.month in (10, 11):
        consumption *= Decimal(rng.uniform(0.12, 0.28)).quantize(Decimal("0.01"))
    elif rng.random() < 0.035:
        consumption *= Decimal(rng.uniform(1.8, 3.3)).quantize(Decimal("0.01"))
    elif rng.random() < 0.025:
        consumption *= Decimal(rng.uniform(0.25, 0.55)).quantize(Decimal("0.01"))

    return consumption.quantize(Decimal("0.01"))


def render_brigade_sql() -> str:
    values = ",\n".join(f"({brigade_id}, 1, now(), now())" for brigade_id, _ in BRIGADES)
    members = ",\n".join(
        f"({brigade_id}, {inspector_id}, now())"
        for brigade_id, inspector_ids in BRIGADES
        for inspector_id in inspector_ids
    )
    return f"""
delete from brigade_members where brigade_id between {DEFAULT_BASE_ID} and {DEFAULT_BASE_ID + 99999};
delete from brigades where id between {DEFAULT_BASE_ID} and {DEFAULT_BASE_ID + 99999};
insert into brigades (id, status, created_at, updated_at) overriding system value values
{values};
insert into brigade_members (brigade_id, inspector_id, assigned_at) values
{members};
"""


def render_user_sql() -> str:
    inspector_ids = tuple(inspector_id for _, inspector_ids in BRIGADES for inspector_id in inspector_ids)
    user_ids = ", ".join(str(inspector_id) for inspector_id in inspector_ids)
    users = ",\n".join(
        "("
        f"{inspector_id}, 1, {sql_str('Инспектор')}, {sql_str(str(slot + 1))}, {sql_str('Демо')}, "
        f"{sql_str(demo_inspector_phone(inspector_id))}, {sql_str(f'year.demo.inspector.{inspector_id}@energo.local')}, "
        f"{sql_str(DEMO_PASSWORD_HASH)}, now(), now()"
        ")"
        for slot, inspector_id in enumerate(inspector_ids)
    )
    return f"""
create table if not exists users (
    id serial primary key,
    role_id integer not null,
    surname text not null,
    name text not null,
    patronymic text,
    phone_number text not null unique,
    email text not null unique,
    password_hash text not null,
    refresh_token text,
    refresh_token_expired_after timestamp with time zone,
    created_at timestamp with time zone default now() not null,
    updated_at timestamp with time zone default now() not null,
    constraint phone_number_format check (phone_number ~ '^(\\+7|8)\\d{{10}}$'),
    constraint email_format check (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{{2,}}$')
);
delete from users where id in ({user_ids});
insert into users (id, role_id, surname, name, patronymic, phone_number, email, password_hash, created_at, updated_at) overriding system value values
{users};
"""


def render_subscriber_sql(cases: list[YearSeedCase]) -> str:
    unique_cases = _unique_customer_cases(cases)
    subscribers = ",\n".join(
        "("
        f"{case.subscriber_id}, {sql_str(case.account_number)}, {sql_str(case.surname)}, {sql_str(case.name)}, {sql_str(case.patronymic)}, "
        f"{sql_str(case.phone_number)}, {sql_str(case.email)}, {sql_str(case.inn)}, {sql_str(case.birth_date.isoformat())}, "
        f"{subscriber_status(case)}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)}"
        ")"
        for case in unique_cases
    )
    passports = ",\n".join(
        "("
        f"{case.passport_id}, {case.subscriber_id}, {sql_str(case.passport_series)}, {sql_str(case.passport_number)}, "
        f"{sql_str('ОВД Центрального района')}, {sql_str(date(2015 + case.index % 8, (case.index % 12) + 1, 15).isoformat())}"
        ")"
        for case in unique_cases
    )
    objects = ",\n".join(
        f"({case.object_id}, {sql_str(case.address)}, {sql_bool(case.index % 2 == 0)}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)})"
        for case in unique_cases
    )
    devices = ",\n".join(
        "("
        f"{case.device_id}, {case.object_id}, {sql_str(case.device_type)}, {sql_str(case.device_number)}, "
        f"{case.device_place_type}, {sql_str('Щит учета на лестничной площадке')}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)}"
        ")"
        for case in unique_cases
    )
    seals = ",\n".join(
        f"({case.first_seal_id}, {case.device_id}, {sql_str(case.seal_numbers[0])}, {sql_str('крышка клеммной колодки')}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)}),\n"
        f"({case.second_seal_id}, {case.device_id}, {sql_str(case.seal_numbers[1])}, {sql_str('вводной автомат')}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)})"
        for case in unique_cases
    )
    contracts = ",\n".join(
        "("
        f"{case.contract_id}, {sql_str(case.contract_number)}, {case.subscriber_id}, {case.object_id}, "
        f"{sql_str((case.visit_at.date() - timedelta(days=120 + case.index % 180)).isoformat())}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)}"
        ")"
        for case in unique_cases
    )
    cleanup_start, cleanup_end = cleanup_bounds(cases)
    return f"""
delete from contracts where id between {cleanup_start} and {cleanup_end};
delete from seals where device_id between {cleanup_start} and {cleanup_end};
delete from devices where id between {cleanup_start} and {cleanup_end};
delete from objects where id between {cleanup_start} and {cleanup_end};
delete from passports where subscriber_id between {cleanup_start} and {cleanup_end};
delete from subscribers where id between {cleanup_start} and {cleanup_end};
insert into subscribers (id, account_number, surname, name, patronymic, phone_number, email, inn, birth_date, status, created_at, updated_at) overriding system value values
{subscribers};
insert into passports (id, subscriber_id, series, number, issued_by, issue_date) overriding system value values
{passports};
insert into objects (id, address, have_automaton, created_at, updated_at) overriding system value values
{objects};
insert into devices (id, object_id, type, number, place_type, place_description, created_at, updated_at) overriding system value values
{devices};
insert into seals (id, device_id, number, place, created_at, updated_at) overriding system value values
{seals};
insert into contracts (id, number, subscriber_id, object_id, sign_date, created_at, updated_at) overriding system value values
{contracts};
"""


def render_task_sql(cases: list[YearSeedCase]) -> str:
    tasks = ",\n".join(
        "("
        f"{case.task_id}, {case.brigade_id}, {case.object_id}, {sql_ts(case.visit_at)}, 3, "
        f"{sql_str('Годовой демо-сценарий: ' + case.inspection_kind)}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)}, "
        f"{sql_ts(case.started_at)}, {sql_ts(case.finished_at)}"
        ")"
        for case in cases
    )
    return f"""
delete from tasks where id between {cases[0].seed_id} and {cases[-1].seed_id};
insert into tasks (id, brigade_id, object_id, plan_visit_at, status, comment, started_at, finished_at, created_at, updated_at) overriding system value values
{tasks};
"""


def render_inspection_sql(cases: list[YearSeedCase]) -> str:
    inspections = ",\n".join(
        "("
        f"{case.inspection_id}, {case.task_id}, 2, {TYPE_IDS[case.inspection_kind]}, {RESOLUTION_IDS[case.inspection_kind]}, null, "
        f"{sql_str(METHODS[case.inspection_kind])}, 2, {REASON_TYPE_IDS[case.inspection_kind]}, null, "
        f"{sql_bool(case.is_violation)}, {sql_bool(case.is_violation)}, {sql_bool(case.is_violation)}, "
        f"{sql_nullable_str('Зафиксирован расход после ограничения.' if case.inspection_kind == 'verification' else None)}, "
        f"{sql_bool(case.inspection_kind == 'unauthorized_connection')}, "
        f"{sql_nullable_str('Самовольное подключение кабеля в обход прибора учета.' if case.inspection_kind == 'unauthorized_connection' else None)}, "
        f"{sql_nullable_str('Подключение выполнено без согласования.' if case.inspection_kind == 'unauthorized_connection' else None)}, "
        f"{sql_ts(case.finished_at)}, {sql_ts(case.visit_at)}, {sql_ts(case.started_at)}, {sql_ts(case.finished_at)}"
        ")"
        for case in cases
    )
    devices = ",\n".join(
        f"({case.inspected_device_id}, {case.device_id}, {case.inspection_id}, {case.reading_value:.2f}, {case.consumption:.2f}, {sql_ts(case.finished_at)})"
        for case in cases
    )
    seals = ",\n".join(
        f"({case.first_seal_id}, {case.inspection_id}, {sql_bool(case.is_violation)}, {sql_ts(case.finished_at)}),\n"
        f"({case.second_seal_id}, {case.inspection_id}, false, {sql_ts(case.finished_at)})"
        for case in cases
    )
    return f"""
delete from inspected_seals where inspection_id between {cases[0].seed_id} and {cases[-1].seed_id};
delete from inspected_devices where inspection_id between {cases[0].seed_id} and {cases[-1].seed_id};
delete from attachments where inspection_id between {cases[0].seed_id} and {cases[-1].seed_id};
delete from inspections where id between {cases[0].seed_id} and {cases[-1].seed_id};
insert into inspections (
    id, task_id, status, type, resolution, limit_reason, method, method_by, reason_type, reason_description,
    is_restriction_checked, is_violation_detected, is_expense_available, violation_description,
    is_unauthorized_consumers, unauthorized_description, unauthorized_explanation,
    inspect_at, energy_action_at, created_at, updated_at
) overriding system value values
{inspections};
insert into inspected_devices (id, device_id, inspection_id, value, consumption, created_at) overriding system value values
{devices};
insert into inspected_seals (seal_id, inspection_id, is_broken, created_at) values
{seals};
"""


def render_clickhouse_json_lines(cases: list[YearSeedCase]) -> str:
    return "\n".join(json.dumps(clickhouse_row(case), ensure_ascii=False) for case in cases) + "\n"


def estimate_anomaly_reasons(cases: list[YearSeedCase]) -> set[str]:
    monthly = defaultdict(Decimal)
    for case in cases:
        key = (
            case.visit_at.replace(day=1).date(),
            case.subscriber_id,
            case.object_id,
            case.address.split(",", 1)[0],
        )
        monthly[key] += case.consumption

    subscriber_values = defaultdict(list)
    district_month_values = defaultdict(list)
    for (month, subscriber_id, object_id, district_name), consumption in monthly.items():
        subscriber_values[(subscriber_id, object_id)].append((month, consumption))
        district_month_values[(district_name, month)].append(consumption)

    reasons = set()
    for (month, subscriber_id, object_id, district_name), consumption in monthly.items():
        own_history = [value for value_month, value in subscriber_values[(subscriber_id, object_id)] if value_month < month]
        own_avg = sum(own_history, Decimal("0")) / Decimal(len(own_history)) if own_history else Decimal("0")
        district_values = district_month_values[(district_name, month)]
        district_avg = (
            (sum(district_values, Decimal("0")) - consumption) / Decimal(len(district_values) - 1)
            if len(district_values) > 1
            else Decimal("0")
        )
        subscriber_deviation = (consumption - own_avg) / own_avg if own_avg > 0 else Decimal("0")
        district_deviation = (consumption - district_avg) / district_avg if district_avg > 0 else Decimal("0")

        if len(own_history) >= 3 and subscriber_deviation >= Decimal("0.5"):
            reasons.add("Скачок относительно истории абонента")
        elif len(own_history) >= 3 and subscriber_deviation <= Decimal("-0.5"):
            reasons.add("Провал относительно истории абонента")
        elif district_deviation >= Decimal("1.5"):
            reasons.add("Выше среднего по району")
        elif district_deviation <= Decimal("-0.6"):
            reasons.add("Ниже среднего по району")

    return reasons


def clickhouse_row(case: YearSeedCase) -> dict:
    return {
        "task_id": case.task_id,
        "comment": f"Годовой демо-сценарий: {case.inspection_kind}",
        "plan_visit_at": ch_dt(case.visit_at),
        "started_at": ch_dt(case.started_at),
        "finished_at": ch_dt(case.finished_at),
        "inspection_id": case.inspection_id,
        "inspection_type": case.inspection_kind,
        "inspection_resolution": RESOLUTION_NAMES[case.inspection_kind],
        "inspection_limit_reason": None,
        "inspection_method": METHODS[case.inspection_kind],
        "inspection_method_by": "inspector",
        "inspection_reason_type": REASON_TYPE_NAMES[case.inspection_kind],
        "inspection_reason_description": None,
        "inspection_is_restriction_checked": case.is_violation,
        "inspection_is_violation_detected": case.is_violation,
        "inspection_is_expense_available": case.is_violation,
        "inspection_violation_description": "Зафиксирован расход после ограничения." if case.inspection_kind == "verification" else None,
        "inspection_is_unauthorized_consumers": case.inspection_kind == "unauthorized_connection",
        "inspection_unauthorized_description": "Самовольное подключение кабеля в обход прибора учета." if case.inspection_kind == "unauthorized_connection" else None,
        "inspection_unauthorized_explanation": "Подключение выполнено без согласования." if case.inspection_kind == "unauthorized_connection" else None,
        "inspection_inspect_at": ch_dt(case.finished_at),
        "inspection_energy_action_at": ch_dt(case.visit_at),
        "inspected_devices": [
            {
                "id": case.inspected_device_id,
                "device_id": case.device_id,
                "value": f"{case.reading_value:.2f}",
                "consumption_kwh": f"{case.consumption:.2f}",
                "created_at": ch_dt(case.finished_at),
            }
        ],
        "brigade_id": case.brigade_id,
        "brigade_inspectors": [
            {
                "id": inspector_id,
                "surname": "Инспектор",
                "name": str(slot + 1),
                "patronymic": "Демо",
                "phone_number": f"+7910{inspector_id:07d}"[-12:],
                "email": f"inspector.{inspector_id}@energo.local",
                "assigned_at": ch_dt(case.started_at),
            }
            for slot, inspector_id in enumerate(case.inspector_ids)
        ],
        "object_id": case.object_id,
        "object_address": case.address,
        "object_have_automaton": case.index % 2 == 0,
        "subscriber_id": case.subscriber_id,
        "subscriber_account_number": case.account_number,
        "subscriber_surname": case.surname,
        "subscriber_name": case.name,
        "subscriber_patronymic": case.patronymic,
        "subscriber_phone_number": case.phone_number,
        "subscriber_email": case.email,
        "subscriber_inn": case.inn,
        "subscriber_birth_date": case.birth_date.isoformat(),
        "subscriber_status": "violator" if case.is_violation else "active",
    }


def run_seed(
    rows: int,
    start_date: date,
    compose_file: str = DEFAULT_COMPOSE_FILE,
    base_id: int = DEFAULT_BASE_ID,
    project_name: str | None = None,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> None:
    cases = build_year_cases(rows=rows, start_date=start_date, base_id=base_id, random_seed=random_seed)
    run_psql(compose_file, "user_service", render_user_sql(), project_name=project_name)
    run_psql(compose_file, "subscriber_service", render_subscriber_sql(cases), project_name=project_name)
    run_psql(compose_file, "brigade_service", render_brigade_sql(), project_name=project_name)
    run_psql(compose_file, "task_service", render_task_sql(cases), project_name=project_name)
    run_psql(compose_file, "inspection_service", render_inspection_sql(cases), project_name=project_name)
    run_clickhouse(compose_file, cases, project_name=project_name)


def run_psql(compose_file: str, database: str, sql: str, project_name: str | None = None) -> None:
    subprocess.run(
        compose_command(compose_file, project_name) + ["exec", "-T", "postgres", "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database],
        input=sql,
        text=True,
        check=True,
    )


def run_clickhouse(compose_file: str, cases: list[YearSeedCase], project_name: str | None = None) -> None:
    delete_query = (
        "ALTER TABLE analytics_service.finished_tasks "
        f"DELETE WHERE task_id >= {cases[0].task_id} AND task_id <= {cases[-1].task_id} SETTINGS mutations_sync = 1"
    )
    insert_query = "INSERT INTO analytics_service.finished_tasks FORMAT JSONEachRow"
    subprocess.run(
        compose_command(compose_file, project_name)
        + clickhouse_client_command(delete_query),
        check=True,
    )
    subprocess.run(
        compose_command(compose_file, project_name)
        + clickhouse_client_command(insert_query),
        input=render_clickhouse_json_lines(cases),
        text=True,
        check=True,
    )


def clickhouse_client_command(query: str) -> list[str]:
    return [
        "exec",
        "-T",
        "clickhouse",
        "clickhouse-client",
        "--host",
        "localhost",
        "--port",
        "9123",
        "-u",
        "root",
        "--password",
        "s4c1A2bgbqK2FJuR20R7",
        "--query",
        query,
    ]


def compose_command(compose_file: str, project_name: str | None = None) -> list[str]:
    command = ["docker", "compose", "-f", compose_file]
    if project_name:
        command.extend(["-p", project_name])
    return command


def sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_nullable_str(value: str | None) -> str:
    return "null" if value is None else sql_str(value)


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def sql_ts(value: datetime) -> str:
    return sql_str(value.isoformat())


def ch_dt(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def demo_inspector_phone(inspector_id: int) -> str:
    return f"+7910{inspector_id:07d}"[-12:]


def subscriber_status(case: YearSeedCase) -> int:
    return 2 if case.is_violation else 1


def cleanup_bounds(cases: list[YearSeedCase]) -> tuple[int, int]:
    start = cases[0].seed_id
    return start, start + 99_999


def _unique_customer_cases(cases: list[YearSeedCase]) -> list[YearSeedCase]:
    unique = {}
    for case in cases:
        unique.setdefault(case.customer_slot, case)
    return [unique[slot] for slot in sorted(unique)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed one year of realistic demo data into the dev databases.")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="Number of completed inspections to create.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_START_DATE, help="First work day in YYYY-MM-DD format.")
    parser.add_argument("--compose-file", default=DEFAULT_COMPOSE_FILE, help="Docker Compose file path.")
    parser.add_argument("--base-id", type=int, default=DEFAULT_BASE_ID, help="Numeric ID prefix used for deterministic seed rows.")
    parser.add_argument("--project-name", help="Docker Compose project name, for example energy-control-system.")
    parser.add_argument("--random-seed", type=int, default=DEFAULT_RANDOM_SEED, help="Seed for reproducible pseudo-random data.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_seed(
        rows=args.rows,
        start_date=args.start_date,
        compose_file=args.compose_file,
        base_id=args.base_id,
        project_name=args.project_name,
        random_seed=args.random_seed,
    )
    end_date = args.start_date + timedelta(days=min(args.rows, YEAR_DAYS) - 1)
    print(f"Seeded {args.rows} completed inspections from {args.start_date} to {end_date}.")


if __name__ == "__main__":
    main()
