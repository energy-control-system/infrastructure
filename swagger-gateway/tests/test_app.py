from fastapi.testclient import TestClient

import app as gateway


def test_openapi_json_merges_specs_with_gateway_prefixes(monkeypatch):
    async def fake_fetch_json(client, service):
        specs = {
            "task-service": {
                "openapi": "3.1.0",
                "info": {"title": "Task Service API", "version": "1.0"},
                "paths": {
                    "/tasks": {
                        "get": {
                            "tags": ["task"],
                            "summary": "List tasks",
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
                "components": {
                    "schemas": {
                        "handler.TaskResponse": {
                            "type": "object",
                            "properties": {"id": {"type": "string"}},
                        }
                    }
                },
            },
            "analyzer-service": {
                "openapi": "3.1.0",
                "info": {"title": "Analyzer Service API", "version": "1.0"},
                "paths": {
                    "/process-image": {
                        "post": {
                            "tags": ["analyzer"],
                            "summary": "Analyze image",
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
                "components": {
                    "schemas": {
                        "ProcessImageResponse": {
                            "type": "object",
                            "properties": {"IsBlurred": {"type": "boolean"}},
                        }
                    }
                },
            },
        }
        return specs[service.name]

    monkeypatch.setattr(gateway, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        gateway,
        "SERVICES",
        (
            gateway.ServiceSpec("task-service", "http://task-service/swagger/doc.json"),
            gateway.ServiceSpec("analyzer-service", "http://analyzer-service/openapi.json"),
        ),
    )

    response = TestClient(gateway.app).get("/api/docs/openapi.json")

    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"] == "3.1.0"
    assert "/api/task-service/tasks" in spec["paths"]
    assert "/api/analyzer-service/process-image" in spec["paths"]
    assert spec["paths"]["/api/task-service/tasks"]["get"]["tags"] == ["task-service: task"]
    assert spec["paths"]["/api/analyzer-service/process-image"]["post"]["tags"] == [
        "analyzer-service: analyzer"
    ]
    assert spec["tags"] == [
        {"name": "task-service: task"},
        {"name": "analyzer-service: analyzer"},
    ]
    assert "task-service_handler_TaskResponse" in spec["components"]["schemas"]
    assert "analyzer-service_ProcessImageResponse" in spec["components"]["schemas"]


def test_openapi_json_rejects_legacy_swagger2_specs(monkeypatch):
    async def fake_fetch_json(client, service):
        return {
            "swagger": "2.0",
            "info": {"title": "Task Service API", "version": "1.0"},
            "paths": {},
            "definitions": {},
        }

    monkeypatch.setattr(gateway, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        gateway,
        "SERVICES",
        (gateway.ServiceSpec("task-service", "http://task-service/swagger/doc.json"),),
    )

    response = TestClient(gateway.app).get("/api/docs/openapi.json")

    assert response.status_code == 502
    assert "Unsupported OpenAPI version from task-service" in response.json()["detail"]


def test_docs_page_points_to_gateway_openapi_json():
    response = TestClient(gateway.app).get("/api/docs")

    assert response.status_code == 200
    assert "/api/docs/openapi.json" in response.text
    assert "SwaggerUIBundle" in response.text
