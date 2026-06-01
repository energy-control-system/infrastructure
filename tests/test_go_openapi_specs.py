import json
from pathlib import Path


GO_SERVICE_DIRS = (
    "analytics-service",
    "brigade-service",
    "file-service",
    "inspection-service",
    "subscriber-service",
    "task-service",
)

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def test_go_services_generate_openapi_31_specs():
    repo_root = Path(__file__).resolve().parents[2]

    for service_dir in GO_SERVICE_DIRS:
        spec_path = repo_root / service_dir / "docs" / "swagger.json"
        spec = json.loads(spec_path.read_text())

        assert spec.get("openapi") == "3.1.0", service_dir
        assert "swagger" not in spec, service_dir


def test_go_service_operations_are_temporarily_public():
    repo_root = Path(__file__).resolve().parents[2]

    for service_dir in GO_SERVICE_DIRS:
        spec_path = repo_root / service_dir / "docs" / "swagger.json"
        spec = json.loads(spec_path.read_text())

        assert "securitySchemes" not in spec.get("components", {}), service_dir

        for path, item in spec["paths"].items():
            for method, operation in item.items():
                if method not in HTTP_METHODS:
                    continue
                assert "security" not in operation, f"{service_dir} {method} {path}"
