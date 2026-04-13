import json
import time
import urllib.error
import urllib.request


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        method: str | None = None,
        path: str | None = None,
        status: int | None = None,
        payload: object | None = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.path = path
        self.status = status
        self.payload = payload


class ApiClient:
    def __init__(self, base_url: str, timeout_seconds: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request_json(self, method: str, path: str, payload: dict | None = None) -> dict | list:
        url = f"{self.base_url}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        request = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode("utf-8")
                payload_data = json.loads(body) if body.strip() else None
                raise ApiError(
                    f"{method.upper()} {path} returned {error.code}",
                    method=method.upper(),
                    path=path,
                    status=error.code,
                    payload=payload_data,
                ) from error
            finally:
                error.close()


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
