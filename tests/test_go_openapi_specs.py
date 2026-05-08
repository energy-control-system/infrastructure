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


def test_go_services_generate_openapi_31_specs():
    repo_root = Path(__file__).resolve().parents[2]

    for service_dir in GO_SERVICE_DIRS:
        spec_path = repo_root / service_dir / "docs" / "swagger.json"
        spec = json.loads(spec_path.read_text())

        assert spec.get("openapi") == "3.1.0", service_dir
        assert "swagger" not in spec, service_dir
