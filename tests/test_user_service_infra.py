from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEV_COMPOSE = ROOT / "docker-compose.dev.yml"
NGINX_DEV = ROOT / "nginx.dev.conf"
BUILD_SCRIPT = ROOT / "build-microservice-images.sh"
SWAGGER_GATEWAY = ROOT / "swagger-gateway" / "app.py"


def test_dev_compose_defines_user_service() -> None:
    text = DEV_COMPOSE.read_text(encoding="utf-8")

    for token in (
        "user-service:",
        "image: user-service:latest",
        "container_name: user-service",
        "context: ../user-service",
        "DATABASE_URL: postgresql://postgres:GvcLkrWP9x8ey2xI9F@postgres:5432/user_service",
    ):
        assert token in text


def test_nginx_routes_user_service_api() -> None:
    text = NGINX_DEV.read_text(encoding="utf-8")

    for token in (
        "upstream user-service",
        "server user-service:3000;",
        "location /api/user-service/",
        "rewrite /api/user-service/(.*) /$1  break;",
        "proxy_pass http://user-service;",
    ):
        assert token in text


def test_swagger_gateway_fetches_user_service_docs() -> None:
    text = SWAGGER_GATEWAY.read_text(encoding="utf-8")

    assert 'ServiceSpec("user-service", "http://user-service:3000/docs-json")' in text


def test_build_script_includes_user_service_image() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert '"user-service"' in text
