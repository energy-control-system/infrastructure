from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEV_COMPOSE = ROOT / "docker-compose.dev.yml"
PROD_COMPOSE = ROOT / "docker-compose.prod.yml"
DEV_NGINX = ROOT / "nginx.dev.conf"
PROD_NGINX = ROOT / "nginx.prod.conf"


class MetabaseInfraContractTests(unittest.TestCase):
    def test_dev_compose_contains_metabase_stack(self) -> None:
        text = DEV_COMPOSE.read_text(encoding="utf-8")
        for token in (
            "metabase-db-init:",
            "metabase:",
            "metabase-init:",
            "MB_SITE_LOCALE: ru",
            "MB_SITE_URL: http://localhost/metabase/",
            "METABASE_COLLECTION_NAME: Аналитика энергоконтроля",
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
            "./nginx.prod.conf:/etc/nginx/nginx.conf",
        ):
            self.assertIn(token, text)

    def test_dev_nginx_exposes_metabase_route(self) -> None:
        text = DEV_NGINX.read_text(encoding="utf-8")
        self.assertIn("upstream metabase", text)
        self.assertIn("location /metabase", text)
        self.assertIn("proxy_pass http://metabase;", text)

    def test_prod_nginx_file_exists_and_exposes_metabase(self) -> None:
        text = PROD_NGINX.read_text(encoding="utf-8")
        self.assertIn("upstream metabase", text)
        self.assertIn("location /metabase", text)
        self.assertIn("proxy_pass http://metabase;", text)


if __name__ == "__main__":
    unittest.main()
