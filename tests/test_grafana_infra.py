import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEV_COMPOSE = ROOT / "docker-compose.dev.yml"
DATASOURCE = ROOT / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
DASHBOARD_PROVIDER = ROOT / "grafana" / "provisioning" / "dashboards" / "technical.yml"
DASHBOARD = ROOT / "grafana" / "dashboards" / "technical-metrics.json"


class GrafanaInfraContractTests(unittest.TestCase):
    def test_dev_compose_mounts_grafana_provisioning(self) -> None:
        text = DEV_COMPOSE.read_text(encoding="utf-8")

        self.assertIn("./grafana/provisioning:/etc/grafana/provisioning", text)
        self.assertIn("./grafana/dashboards:/var/lib/grafana/dashboards", text)

    def test_prometheus_datasource_is_provisioned(self) -> None:
        text = DATASOURCE.read_text(encoding="utf-8")

        for token in (
            "apiVersion: 1",
            "name: Prometheus",
            "uid: prometheus",
            "type: prometheus",
            "access: proxy",
            "url: http://prometheus:9090",
            "isDefault: true",
            "httpMethod: POST",
            "timeInterval: 30s",
        ):
            self.assertIn(token, text)

    def test_technical_dashboard_provider_is_provisioned(self) -> None:
        text = DASHBOARD_PROVIDER.read_text(encoding="utf-8")

        for token in (
            "name: technical-metrics",
            "folder: Технические метрики",
            "type: file",
            "allowUiUpdates: false",
            "path: /var/lib/grafana/dashboards",
        ):
            self.assertIn(token, text)

    def test_technical_dashboard_uses_existing_prometheus_metrics(self) -> None:
        dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
        panel_titles = {panel["title"] for panel in dashboard["panels"]}
        queries = "\n".join(
            target["expr"]
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
        )

        self.assertEqual("microservices-technical-metrics", dashboard["uid"])
        self.assertEqual("Технические метрики микросервисов", dashboard["title"])
        self.assertGreaterEqual(len(dashboard["panels"]), 8)
        self.assertGreaterEqual(
            panel_titles,
            {
                "Доступность сервисов",
                "RPS по сервисам",
                "Ошибки 5xx",
                "P95 latency",
                "Активные HTTP-запросы",
                "Goroutines",
                "Память Go heap",
                "CPU process",
            },
        )
        for metric in (
            "up",
            "http_requests_total",
            "http_active_requests",
            "http_request_duration_seconds_bucket",
            "go_goroutines",
            "go_memstats_heap_alloc_bytes",
            "process_cpu_seconds_total",
        ):
            self.assertIn(metric, queries)
        self.assertIn("job=~\"$service\"", queries)


if __name__ == "__main__":
    unittest.main()
