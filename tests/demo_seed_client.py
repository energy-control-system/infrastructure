import json
import time
import urllib.request


class ApiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, payload: object | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class ApiClient:
    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request_json(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        request = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read()
            decoded = json.loads(body.decode("utf-8"))
            status = response.status if hasattr(response, "status") else response.getcode()
            if status >= 400:
                raise ApiError(f"request failed with status {status}", status=status, payload=decoded)
            return decoded


def poll_until(fetch, is_ready, timeout_seconds: float, interval_seconds: float = 1.0, on_timeout=None):
    deadline = time.monotonic() + timeout_seconds

    while True:
        value = fetch()
        if is_ready(value):
            return value

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            if on_timeout is not None:
                return on_timeout()
            raise TimeoutError(f"timed out after {timeout_seconds} seconds")

        sleep_for = min(interval_seconds, remaining / 2)
        if sleep_for > 0:
            time.sleep(sleep_for)
