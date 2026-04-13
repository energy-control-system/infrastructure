from dataclasses import dataclass


@dataclass(frozen=True)
class BrigadeSeed:
    label: str
    inspector_ids: tuple[int, int]


@dataclass(frozen=True)
class SubscriberSeed:
    account_number: str
    surname: str
    name: str
    patronymic: str
    phone_number: str
    email: str
    inn: str
    birth_date: str
    passport_series: str
    passport_number: str
    passport_issued_by: str
    passport_issue_date: str


@dataclass(frozen=True)
class ObjectSeed:
    address: str
    have_automaton: bool
    device_type: str
    device_number: str
    device_place_type: int
    device_place_description: str
    seal_numbers: tuple[str, str]


@dataclass(frozen=True)
class DemoCase:
    brigade_slot: int
    subscriber: SubscriberSeed
    object_data: ObjectSeed
    contract_number: str
    sign_date: str
    task_comment: str
    inspection_kind: str
    outcome: str


@dataclass(frozen=True)
class DemoPlan:
    brigades: tuple[BrigadeSeed, ...]
    cases: tuple[DemoCase, ...]


BRIGADE_LABELS = (
    "Central inspection brigade",
    "North district brigade",
    "South district brigade",
)

BRIGADE_INSPECTOR_IDS = (
    (101, 102),
    (201, 202),
    (301, 302),
)

INSPECTION_KINDS = (
    ("limitation", 8),
    ("resumption", 8),
    ("verification", 8),
    ("unauthorized_connection", 6),
)

MIX = tuple(
    kind
    for kind, count in INSPECTION_KINDS
    for _ in range(count)
)

SURNAMES = (
    "Ivanov",
    "Petrov",
    "Sidorov",
    "Smirnov",
    "Kuznetsov",
    "Popov",
    "Volkov",
    "Mikhailov",
    "Fedorov",
    "Morozov",
    "Vinogradov",
    "Sokolov",
    "Lebedev",
    "Novikov",
    "Orlov",
    "Pavlov",
    "Stepanov",
    "Zaitsev",
    "Borisov",
    "Egorov",
    "Nikiforov",
    "Tikhonov",
    "Karpov",
    "Rybakov",
    "Belov",
    "Denisov",
    "Ershov",
    "Kiselev",
    "Mironov",
    "Semenov",
)

NAMES = (
    "Alexey",
    "Boris",
    "Viktor",
    "Dmitry",
    "Eugene",
    "Fyodor",
    "Gennady",
    "Igor",
    "Kirill",
    "Leonid",
    "Maxim",
    "Nikolay",
    "Oleg",
    "Pavel",
    "Roman",
    "Sergey",
    "Timur",
    "Yuri",
    "Anton",
    "Artem",
    "Vladimir",
    "Andrey",
    "Denis",
    "Mikhail",
    "Yaroslav",
    "Ruslan",
    "Konstantin",
    "Vasiliy",
    "Ilya",
    "Stepan",
)

PATRONYMICS = (
    "Alexeevich",
    "Borisovich",
    "Viktorovich",
    "Dmitrievich",
    "Evgenevich",
    "Fyodorovich",
    "Gennadievich",
    "Igorevich",
    "Kirillovich",
    "Leonidovich",
    "Maximovich",
    "Nikolaevich",
    "Olegovich",
    "Pavlovich",
    "Romanovich",
    "Sergeevich",
    "Timurovich",
    "Yurievich",
    "Antonovich",
    "Artemovich",
    "Vladimirovich",
    "Andreevich",
    "Denisovich",
    "Mikhailovich",
    "Yaroslavovich",
    "Ruslanovich",
    "Konstantinovich",
    "Vasilyevich",
    "Ilyich",
    "Stepanovich",
)

DEVICE_TYPES = (
    "single-phase meter",
    "three-phase meter",
    "smart meter",
    "control meter",
)

ADDRESS_STREETS = (
    "Lenina",
    "Mira",
    "Sovetskaya",
    "Gagarina",
    "Pobedy",
    "Pushkina",
    "Kirova",
    "Molodezhnaya",
    "Zarechnaya",
    "Lugovaya",
)

ISSUED_BY = "Department of Internal Affairs"
TASK_COMMENT_PREFIX = "Demo inspection case"
OUTCOMES = (
    "scheduled",
    "completed",
    "pending follow-up",
)


def build_demo_plan(case_count: int = 30) -> DemoPlan:
    if case_count < 0:
        raise ValueError("case_count must be non-negative")
    if case_count > len(MIX):
        raise ValueError("case_count cannot exceed the available demo mix")

    brigades = tuple(
        BrigadeSeed(label=label, inspector_ids=inspector_ids)
        for label, inspector_ids in zip(BRIGADE_LABELS, BRIGADE_INSPECTOR_IDS)
    )

    cases = tuple(_build_case(index) for index in range(case_count))
    return DemoPlan(brigades=brigades, cases=cases)


def _build_case(index: int) -> DemoCase:
    kind = MIX[index]
    brigade_slot = index % len(BRIGADE_LABELS)

    subscriber = SubscriberSeed(
        account_number=f"ACC-{index + 1:05d}",
        surname=SURNAMES[index],
        name=NAMES[index],
        patronymic=PATRONYMICS[index],
        phone_number=f"+7-900-{index + 10:03d}-{index + 20:02d}-{index + 30:02d}",
        email=f"subscriber{index + 1:02d}@demo.local",
        inn=f"770000{index + 1:04d}",
        birth_date=f"198{index % 10}-0{(index % 9) + 1}-15",
        passport_series=f"{4000 + index:04d}",
        passport_number=f"{700000 + index:06d}",
        passport_issued_by=ISSUED_BY,
        passport_issue_date=f"201{index % 10}-0{(index % 9) + 1}-20",
    )

    object_data = ObjectSeed(
        address=f"{ADDRESS_STREETS[index % len(ADDRESS_STREETS)]} street, {index + 1} house, apt. {index + 10}",
        have_automaton=index % 2 == 0,
        device_type=DEVICE_TYPES[index % len(DEVICE_TYPES)],
        device_number=f"DEV-{index + 1:05d}",
        device_place_type=(index % 4) + 1,
        device_place_description=f"Meter cabinet #{index + 1}",
        seal_numbers=(f"SEL-{index * 2 + 1:05d}", f"SEL-{index * 2 + 2:05d}"),
    )

    return DemoCase(
        brigade_slot=brigade_slot,
        subscriber=subscriber,
        object_data=object_data,
        contract_number=f"CTR-{index + 1:05d}",
        sign_date=f"2024-{(index % 12) + 1:02d}-01",
        task_comment=f"{TASK_COMMENT_PREFIX} #{index + 1}",
        inspection_kind=kind,
        outcome=OUTCOMES[index % len(OUTCOMES)],
    )
