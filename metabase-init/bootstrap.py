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
                    "query": "select count(*) as total_completed_tasks from v_bi_tasks_daily",
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
                    "query": "select day, completed_tasks from v_bi_tasks_daily order by day",
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
                    "query": "select status, subscribers from v_bi_subscriber_object_profile order by subscribers desc",
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
                    "card_id": cards_by_name["Всего завершенных задач"],
                    "card_name": "Всего завершенных задач",
                },
                {
                    "card_id": cards_by_name["Динамика выполненных задач по дням"],
                    "card_name": "Динамика выполненных задач по дням",
                },
            ],
        },
        {
            "name": "Абоненты и объекты",
            "cards": [
                {
                    "card_id": cards_by_name["Распределение абонентов по статусам"],
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
