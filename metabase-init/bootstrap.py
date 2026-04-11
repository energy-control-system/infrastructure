def default_collection_name() -> str:
    return "Аналитика энергоконтроля"


def find_by_name(items, name):
    for item in items:
        if item.get("name") == name:
            return item
    return None


def build_question_specs(database_id: int):
    return [
        {"name": "Всего завершенных задач", "database_id": database_id},
        {"name": "Динамика выполненных задач по дням", "database_id": database_id},
        {"name": "Распределение абонентов по статусам", "database_id": database_id},
    ]


def build_dashboard_specs(_cards_by_name):
    return [
        {"name": "Обзор операций"},
        {"name": "Абоненты и объекты"},
    ]
