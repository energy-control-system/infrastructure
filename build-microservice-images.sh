#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DRY_RUN="${DRY_RUN:-false}"

SERVICES=(
  "file-service"
  "analyzer-service"
  "task-service"
  "inspection-service"
  "analytics-service"
  "brigade-service"
  "subscriber-service"
  "user-service"
)

if ! command -v docker >/dev/null 2>&1; then
  echo "docker command is required but was not found in PATH" >&2
  exit 1
fi

for service in "${SERVICES[@]}"; do
  context="${REPO_ROOT}/${service}"
  dockerfile="${context}/Dockerfile"
  tag="${service}:latest"

  if [[ ! -f "${dockerfile}" ]]; then
    echo "Dockerfile not found for ${service}: ${dockerfile}" >&2
    exit 1
  fi

  echo "Building ${tag} from ${context}"

  if [[ "${DRY_RUN}" == "true" ]]; then
    printf 'docker build -t "%s" -f "%s"' "${tag}" "${dockerfile}"
    if (($# > 0)); then
      printf ' "%s"' "$@"
    fi
    printf ' "%s"\n' "${context}"
    continue
  fi

  docker build -t "${tag}" -f "${dockerfile}" "$@" "${context}"
done

echo "All microservice images were built successfully."
