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

PROTECTED_OPERATIONS = {
    "analytics-service": (
        ("/reports/basic/{periodStart}/{periodEnd}", "post"),
        ("/reports", "get"),
    ),
    "brigade-service": (
        ("/brigades", "post"),
        ("/brigades/{id}/archive", "patch"),
        ("/brigades", "get"),
    ),
    "file-service": (
        ("/files/{id}", "get"),
    ),
    "inspection-service": (
        ("/inspections", "get"),
        ("/inspections/{id}", "get"),
        ("/inspections/brigades/{brigadeID}", "get"),
        ("/inspections/{id}/photo", "post"),
        ("/inspections/{id}/finish", "patch"),
    ),
    "subscriber-service": (
        ("/subscribers", "post"),
        ("/subscribers/{id}/extended", "get"),
        ("/subscribers/{id}", "get"),
        ("/subscribers/{id}", "patch"),
        ("/subscribers/{id}", "delete"),
        ("/subscribers", "get"),
        ("/objects", "post"),
        ("/objects/{id}", "get"),
        ("/objects/{id}", "patch"),
        ("/objects/{id}", "delete"),
        ("/objects", "get"),
        ("/contracts", "post"),
        ("/contracts", "get"),
        ("/contracts/{id}", "patch"),
        ("/contracts/{id}", "delete"),
        ("/registry/parse", "post"),
    ),
    "task-service": (
        ("/tasks", "post"),
        ("/tasks/{id}/extended", "get"),
        ("/tasks/{id}", "patch"),
        ("/tasks/{id}", "delete"),
        ("/tasks/brigade/{brigadeID}/extended", "get"),
        ("/tasks", "get"),
        ("/tasks/{id}/start", "patch"),
        ("/tasks/assign", "post"),
    ),
}

PUBLIC_OPERATIONS = {
    "brigade-service": (
        ("/brigades/{id}", "get"),
    ),
    "file-service": (
        ("/files", "post"),
        ("/files", "get"),
    ),
    "inspection-service": (
        ("/inspections/task/{taskID}", "get"),
    ),
    "subscriber-service": (
        ("/objects/devices/{deviceID}", "get"),
        ("/objects/seals/{sealID}", "get"),
        ("/contracts/objects/last", "get"),
        ("/contracts/objects/{objectID}/last", "get"),
    ),
    "task-service": (
        ("/tasks/{id}", "get"),
        ("/tasks/brigade/{brigadeID}", "get"),
    ),
}


def test_go_services_generate_openapi_31_specs():
    repo_root = Path(__file__).resolve().parents[2]

    for service_dir in GO_SERVICE_DIRS:
        spec_path = repo_root / service_dir / "docs" / "swagger.json"
        spec = json.loads(spec_path.read_text())

        assert spec.get("openapi") == "3.1.0", service_dir
        assert "swagger" not in spec, service_dir


def test_go_services_mark_jwt_protected_operations():
    repo_root = Path(__file__).resolve().parents[2]

    for service_dir in GO_SERVICE_DIRS:
        spec_path = repo_root / service_dir / "docs" / "swagger.json"
        spec = json.loads(spec_path.read_text())

        assert spec["components"]["securitySchemes"]["bearer"] == {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT authorization header. Use Bearer <token>.",
        }, service_dir

        for path, method in PROTECTED_OPERATIONS[service_dir]:
            operation = spec["paths"][path][method]
            assert operation.get("security") == [{"bearer": []}], f"{service_dir} {method} {path}"

        for path, method in PUBLIC_OPERATIONS.get(service_dir, ()):
            operation = spec["paths"][path][method]
            assert "security" not in operation, f"{service_dir} {method} {path}"
