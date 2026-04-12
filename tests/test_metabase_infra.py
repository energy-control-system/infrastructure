from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEV_COMPOSE = ROOT / "docker-compose.dev.yml"
PROD_COMPOSE = ROOT / "docker-compose.prod.yml"
DEV_NGINX = ROOT / "nginx.dev.conf"
PROD_NGINX = ROOT / "nginx.prod.conf"
METABASE_INIT_DIR = ROOT / "metabase-init"
METABASE_INIT_DOCKERFILE = METABASE_INIT_DIR / "Dockerfile"
METABASE_INIT_BOOTSTRAP = METABASE_INIT_DIR / "bootstrap.py"


class MetabaseInfraContractTests(unittest.TestCase):
    def test_dev_compose_contains_metabase_stack(self) -> None:
        text = DEV_COMPOSE.read_text(encoding="utf-8")
        for token in (
            "metabase-db-init:",
            "metabase:",
            "metabase-init:",
            "MB_SITE_LOCALE: ru",
            "MB_SITE_URL: http://localhost/metabase/",
            "METABASE_URL: http://metabase:3000",
            "METABASE_ADMIN_EMAIL: admin@localhost",
            "METABASE_CLICKHOUSE_DB: analytics_service",
            "depends_on:",
        ):
            self.assertIn(token, text)

    def test_prod_compose_contains_metabase_stack_and_nginx(self) -> None:
        text = PROD_COMPOSE.read_text(encoding="utf-8")
        for token in (
            "nginx:",
            "metabase-db-init:",
            "metabase:",
            "metabase-init:",
            "MB_SITE_LOCALE: ru",
            "MB_SITE_URL: http://tns.quassbot.ru/metabase/",
            "METABASE_URL: ${METABASE_URL:?METABASE_URL is required}",
            "METABASE_ADMIN_EMAIL: ${METABASE_ADMIN_EMAIL:?METABASE_ADMIN_EMAIL is required}",
            "METABASE_CLICKHOUSE_PASSWORD: ${METABASE_CLICKHOUSE_PASSWORD:?METABASE_CLICKHOUSE_PASSWORD is required}",
            "./nginx.prod.conf:/etc/nginx/nginx.conf",
        ):
            self.assertIn(token, text)

    def test_dev_nginx_exposes_metabase_route(self) -> None:
        text = DEV_NGINX.read_text(encoding="utf-8")
        self.assertIn("upstream metabase", text)
        self.assertIn("location = /metabase", text)
        self.assertIn("return 301 /metabase/;", text)
        self.assertIn("location /metabase/", text)
        self.assertIn("proxy_pass http://metabase/;", text)

    def test_prod_nginx_file_exists_and_exposes_metabase(self) -> None:
        text = PROD_NGINX.read_text(encoding="utf-8")
        self.assertIn("upstream metabase", text)
        self.assertIn("location = /metabase", text)
        self.assertIn("return 301 /metabase/;", text)
        self.assertIn("location /metabase/", text)
        self.assertIn("proxy_pass http://metabase/;", text)

    def test_metabase_init_build_context_exists(self) -> None:
        self.assertTrue(METABASE_INIT_DIR.is_dir())
        self.assertTrue(METABASE_INIT_DOCKERFILE.is_file())
        self.assertTrue(METABASE_INIT_BOOTSTRAP.is_file())


if __name__ == "__main__":
    unittest.main()
