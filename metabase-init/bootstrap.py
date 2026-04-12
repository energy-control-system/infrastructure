def default_collection_name() -> str:
    return "Аналитика энергоконтроля"


def build_question_specs(database_id: int):
    return [
        {
            "name": "Всего завершенных задач",
            "display": "scalar",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select count(*) as total_completed_tasks from tasks where status = 'completed'",
                },
            },
        },
        {
            "name": "Динамика выполненных задач по дням",
            "display": "line",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select completed_at::date as day, count(*) as completed_tasks from tasks group by 1 order by 1",
                },
            },
        },
        {
            "name": "Распределение абонентов по статусам",
            "display": "pie",
            "dataset_query": {
                "database": database_id,
                "type": "native",
                "native": {
                    "query": "select status, count(*) as subscribers from subscribers group by 1 order by 2 desc",
                },
            },
        },
    ]


def build_dashboard_specs(cards_by_name):
    return [
        {
            "name": "Обзор операций",
            "cards": [
                {
                    "card_id": cards_by_name["Всего завершенных задач"]["id"],
                    "card_name": "Всего завершенных задач",
                },
                {
                    "card_id": cards_by_name["Динамика выполненных задач по дням"]["id"],
                    "card_name": "Динамика выполненных задач по дням",
                },
            ],
        },
        {
            "name": "Абоненты и объекты",
            "cards": [
                {
                    "card_id": cards_by_name["Распределение абонентов по статусам"]["id"],
                    "card_name": "Распределение абонентов по статусам",
                }
            ],
        },
    ]


def main() -> int:
    print("metabase-init bootstrap no-op placeholder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
