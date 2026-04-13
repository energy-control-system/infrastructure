import json
import unittest
from unittest.mock import patch

from tests.demo_seed_client import ApiClient, ApiError, poll_until


class _FakeResponse:
    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class DemoSeedClientTests(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_request_json_returns_decoded_payload(self, urlopen) -> None:
        urlopen.return_value = _FakeResponse(200, {"ID": 17})

        client = ApiClient("http://localhost")

        payload = client.request_json("GET", "/api/task-service/tasks/17")

        self.assertEqual({"ID": 17}, payload)

    @patch("urllib.request.urlopen")
    def test_request_json_raises_api_error(self, urlopen) -> None:
        urlopen.return_value = _FakeResponse(500, {"error": "broken"})

        client = ApiClient("http://localhost")

        with self.assertRaises(ApiError):
            client.request_json("GET", "/api/task-service/tasks/17")

    def test_poll_until_retries_until_condition_is_met(self) -> None:
        attempts = iter((None, None, {"ID": 9}))

        result = poll_until(lambda: next(attempts), lambda value: value is not None, timeout_seconds=1.0)

        self.assertEqual({"ID": 9}, result)


if __name__ == "__main__":
    unittest.main()
