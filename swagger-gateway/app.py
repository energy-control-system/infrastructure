from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    url: str


SERVICES = (
    ServiceSpec("file-service", "http://file-service/debug/swagger/doc.json"),
    ServiceSpec("task-service", "http://task-service/debug/swagger/doc.json"),
    ServiceSpec("inspection-service", "http://inspection-service/debug/swagger/doc.json"),
    ServiceSpec("analytics-service", "http://analytics-service/debug/swagger/doc.json"),
    ServiceSpec("brigade-service", "http://brigade-service/debug/swagger/doc.json"),
    ServiceSpec("subscriber-service", "http://subscriber-service/debug/swagger/doc.json"),
    ServiceSpec("analyzer-service", "http://analyzer-service/openapi.json"),
)

GATEWAY_DOCS_PATH = "/api/docs"
GATEWAY_OPENAPI_PATH = "/api/docs/openapi.json"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get(GATEWAY_DOCS_PATH, include_in_schema=False)
async def docs():
    return get_swagger_ui_html(
        openapi_url=GATEWAY_OPENAPI_PATH,
        title="Energy Control API - Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get(GATEWAY_OPENAPI_PATH, include_in_schema=False)
async def openapi_json():
    async with httpx.AsyncClient(timeout=5.0) as client:
        specs = []
        for service in SERVICES:
            specs.append((service, await fetch_json(client, service)))

    return merge_specs(specs)


async def fetch_json(client: httpx.AsyncClient, service: ServiceSpec) -> dict[str, Any]:
    try:
        response = await client.get(service.url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as err:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch Swagger spec from {service.name}: {err}",
        ) from err


def merge_specs(specs: list[tuple[ServiceSpec, dict[str, Any]]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Energy Control API",
            "version": "1.0",
            "description": "Aggregated OpenAPI documentation for all backend microservices.",
        },
        "servers": [{"url": "/"}],
        "tags": [],
        "paths": {},
        "components": {"schemas": {}},
    }

    for service, spec in specs:
        converted = convert_to_openapi3(service.name, spec)
        merged["components"]["schemas"].update(converted["components"]["schemas"])
        merged["paths"].update(prefix_paths(service.name, converted.get("paths", {})))

    merged["tags"] = collect_operation_tags(merged["paths"])

    return merged


def convert_to_openapi3(service_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    if "openapi" in spec:
        return namespace_openapi3(service_name, spec)
    if spec.get("swagger") == "2.0":
        return namespace_swagger2(service_name, spec)

    raise HTTPException(
        status_code=502,
        detail=f"Unsupported OpenAPI/Swagger version from {service_name}",
    )


def namespace_openapi3(service_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    schemas = spec.get("components", {}).get("schemas", {})
    schema_map = {name: namespaced_schema_name(service_name, name) for name in schemas}

    return {
        "info": spec.get("info", {}),
        "paths": rewrite_refs(prefix_operation_tags(service_name, spec.get("paths", {})), schema_map),
        "components": {
            "schemas": {
                schema_map[name]: rewrite_refs(schema, schema_map)
                for name, schema in schemas.items()
            }
        },
    }


def namespace_swagger2(service_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    definitions = spec.get("definitions", {})
    schema_map = {name: namespaced_schema_name(service_name, name) for name in definitions}

    return {
        "info": spec.get("info", {}),
        "paths": rewrite_refs(prefix_operation_tags(service_name, spec.get("paths", {})), schema_map),
        "components": {
            "schemas": {
                schema_map[name]: rewrite_refs(schema, schema_map)
                for name, schema in definitions.items()
            }
        },
    }


def prefix_paths(service_name: str, paths: dict[str, Any]) -> dict[str, Any]:
    prefix = f"/api/{service_name}"
    prefixed = {}

    for path, item in paths.items():
        if path == prefix or path.startswith(f"{prefix}/"):
            prefixed[path] = item
            continue
        normalized_path = path if path.startswith("/") else f"/{path}"
        prefixed[f"{prefix}{normalized_path}"] = item

    return prefixed


def prefix_operation_tags(service_name: str, paths: dict[str, Any]) -> dict[str, Any]:
    copied = deep_copy(paths)

    for item in copied.values():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in {
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            }:
                continue
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags") or [service_name]
            operation["tags"] = [f"{service_name}: {tag}" for tag in tags]

    return copied


def collect_operation_tags(paths: dict[str, Any]) -> list[dict[str, str]]:
    tags = []
    seen = set()

    for item in paths.values():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() not in {
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            }:
                continue
            if not isinstance(operation, dict):
                continue
            for tag in operation.get("tags", []):
                if tag in seen:
                    continue
                seen.add(tag)
                tags.append({"name": tag})

    return tags


def rewrite_refs(value: Any, schema_map: dict[str, str]) -> Any:
    if isinstance(value, list):
        return [rewrite_refs(item, schema_map) for item in value]
    if not isinstance(value, dict):
        return value

    rewritten = {}
    for key, item in value.items():
        if key == "$ref" and isinstance(item, str):
            rewritten[key] = rewrite_ref(item, schema_map)
        else:
            rewritten[key] = rewrite_refs(item, schema_map)
    return rewritten


def rewrite_ref(ref: str, schema_map: dict[str, str]) -> str:
    for prefix in ("#/definitions/", "#/components/schemas/"):
        if ref.startswith(prefix):
            name = ref.removeprefix(prefix)
            return f"#/components/schemas/{schema_map.get(name, name)}"
    return ref


def namespaced_schema_name(service_name: str, schema_name: str) -> str:
    return f"{service_name}_{schema_name}".replace(".", "_")


def deep_copy(value: Any) -> Any:
    if isinstance(value, list):
        return [deep_copy(item) for item in value]
    if isinstance(value, dict):
        return {key: deep_copy(item) for key, item in value.items()}
    return value
