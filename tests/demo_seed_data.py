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
    "Центральная инспекционная бригада",
    "Северная районная бригада",
    "Южная районная бригада",
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
    "Лебедев",
    "Новиков",
    "Орлов",
    "Павлов",
    "Степанов",
    "Зайцев",
    "Борисов",
    "Егоров",
    "Никифоров",
    "Тихонов",
    "Карпов",
    "Рыбаков",
    "Белов",
    "Денисов",
    "Ершов",
    "Киселев",
    "Миронов",
    "Семенов",
)

NAMES = (
    "Алексей",
    "Борис",
    "Виктор",
    "Дмитрий",
    "Евгений",
    "Федор",
    "Геннадий",
    "Игорь",
    "Кирилл",
    "Леонид",
    "Максим",
    "Николай",
    "Олег",
    "Павел",
    "Роман",
    "Сергей",
    "Тимур",
    "Юрий",
    "Антон",
    "Артем",
    "Владимир",
    "Андрей",
    "Денис",
    "Михаил",
    "Ярослав",
    "Руслан",
    "Константин",
    "Василий",
    "Илья",
    "Степан",
)

PATRONYMICS = (
    "Алексеевич",
    "Борисович",
    "Викторович",
    "Дмитриевич",
    "Евгеньевич",
    "Федорович",
    "Геннадьевич",
    "Игоревич",
    "Кириллович",
    "Леонидович",
    "Максимович",
    "Николаевич",
    "Олегович",
    "Павлович",
    "Романович",
    "Сергеевич",
    "Тимурович",
    "Юрьевич",
    "Антонович",
    "Артемович",
    "Владимирович",
    "Андреевич",
    "Денисович",
    "Михайлович",
    "Ярославович",
    "Русланович",
    "Константинович",
    "Васильевич",
    "Ильич",
    "Степанович",
)

DEVICE_TYPES = (
    "Однофазный счетчик",
    "Трехфазный счетчик",
    "Интеллектуальный счетчик",
    "Контрольный счетчик",
)

ADDRESS_STREETS = (
    "ул. Ленина",
    "ул. Мира",
    "ул. Советская",
    "ул. Гагарина",
    "ул. Победы",
    "ул. Пушкина",
    "ул. Кирова",
    "ул. Молодежная",
    "ул. Заречная",
    "ул. Луговая",
)

ISSUED_BY = "ОВД Центрального района г. Тулы"
TASK_COMMENT_PREFIX = "Демонстрационная проверка"
OUTCOMES = (
    "запланирована",
    "выполнена",
    "требует контроля",
)


def build_demo_plan(case_count: int = 30) -> DemoPlan:
    if case_count < 0:
        raise ValueError("case_count must be non-negative")
    if case_count > _supported_case_count():
        raise ValueError("case_count cannot exceed the available demo mix")

    brigades = _build_brigades()

    cases = tuple(_build_case(index) for index in range(case_count))
    return DemoPlan(brigades=brigades, cases=cases)


def _supported_case_count() -> int:
    return min(
        len(MIX),
        len(SURNAMES),
        len(NAMES),
        len(PATRONYMICS),
    )


def _build_brigades() -> tuple[BrigadeSeed, ...]:
    if len(BRIGADE_LABELS) != len(BRIGADE_INSPECTOR_IDS):
        raise ValueError("brigade labels and inspector ids must stay aligned")

    return tuple(
        BrigadeSeed(
            label=BRIGADE_LABELS[index],
            inspector_ids=BRIGADE_INSPECTOR_IDS[index],
        )
        for index in range(len(BRIGADE_LABELS))
    )


def _build_case(index: int) -> DemoCase:
    kind = MIX[index]
    brigade_slot = index % len(BRIGADE_LABELS)

    subscriber = SubscriberSeed(
        account_number=f"ЛС-{index + 1:05d}",
        surname=SURNAMES[index],
        name=NAMES[index],
        patronymic=PATRONYMICS[index],
        phone_number=f"+7900{index + 10:03d}{index + 20:02d}{index + 30:02d}",
        email=f"abonent{index + 1:02d}@demo-energo.local",
        inn=f"770000{index + 1:04d}",
        birth_date=f"198{index % 10}-0{(index % 9) + 1}-15",
        passport_series=f"{4000 + index:04d}",
        passport_number=f"{700000 + index:06d}",
        passport_issued_by=ISSUED_BY,
        passport_issue_date=f"201{index % 10}-{(index % 9) + 1:02d}-20",
    )

    object_data = ObjectSeed(
        address=f"{ADDRESS_STREETS[index % len(ADDRESS_STREETS)]}, д. {index + 1}, кв. {index + 10}",
        have_automaton=index % 2 == 0,
        device_type=DEVICE_TYPES[index % len(DEVICE_TYPES)],
        device_number=f"DEV-{index + 1:05d}",
        device_place_type=(index % 4) + 1,
        device_place_description=f"Щит учета №{index + 1}",
        seal_numbers=(f"SEL-{index * 2 + 1:05d}", f"SEL-{index * 2 + 2:05d}"),
    )

    return DemoCase(
        brigade_slot=brigade_slot,
        subscriber=subscriber,
        object_data=object_data,
        contract_number=f"ДОГ-{index + 1:05d}",
        sign_date=f"2024-{(index % 12) + 1:02d}-01",
        task_comment=f"{TASK_COMMENT_PREFIX} №{index + 1}",
        inspection_kind=kind,
        outcome=OUTCOMES[index % len(OUTCOMES)],
    )
