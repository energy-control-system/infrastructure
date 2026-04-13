from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEV_COMPOSE = ROOT / "docker-compose.dev.yml"


class KafkaInfraContractTests(unittest.TestCase):
    @staticmethod
    def _service_section(text: str, service: str) -> str:
        matches = list(re.finditer(r"(?m)^  [a-z0-9-]+:\n", text))
        positions = [match.start() for match in matches]

        marker = re.search(rf"(?m)^  {re.escape(service)}:\n", text)
        if marker is None:
            raise ValueError(f"service {service!r} not found")

        start = marker.start()
        following = [pos for pos in positions if pos > start]
        end = min(following) if following else len(text)

        return text[start:end]

    def test_dev_compose_contains_shared_kafka_topics_init_service(self) -> None:
        text = DEV_COMPOSE.read_text(encoding="utf-8")

        for token in (
            "kafka-topics-init:",
            "container_name: kafka-topics-init",
            "kafka-topics.sh --bootstrap-server kafka:9093 --create --if-not-exists --topic tasks-topic",
            "kafka-topics.sh --bootstrap-server kafka:9093 --create --if-not-exists --topic inspections-topic",
        ):
            self.assertIn(token, text)

    def test_kafka_backed_services_wait_for_topic_init(self) -> None:
        text = DEV_COMPOSE.read_text(encoding="utf-8")

        for service in (
            "task-service",
            "inspection-service",
            "analytics-service",
            "brigade-service",
            "subscriber-service",
        ):
            section = self._service_section(text, service)
            self.assertIn("kafka-topics-init:\n        condition: service_completed_successfully", section)


if __name__ == "__main__":
    unittest.main()
