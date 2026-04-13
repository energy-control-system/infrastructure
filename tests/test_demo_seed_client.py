import json
import io
import unittest
from urllib.error import HTTPError
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
        request = urlopen.call_args.args[0]

        self.assertEqual({"ID": 17}, payload)
        self.assertEqual("http://localhost/api/task-service/tasks/17", request.full_url)
        self.assertEqual("GET", request.get_method())
        self.assertIsNone(request.data)

    @patch("urllib.request.urlopen")
    def test_request_json_raises_api_error(self, urlopen) -> None:
        urlopen.side_effect = HTTPError(
            "http://localhost/api/task-service/tasks/17",
            500,
            "Internal Server Error",
            None,
            io.BytesIO(json.dumps({"error": "broken"}).encode("utf-8")),
        )

        client = ApiClient("http://localhost")

        with self.assertRaises(ApiError) as cm:
            client.request_json("GET", "/api/task-service/tasks/17")

        self.assertEqual("GET", cm.exception.method)
        self.assertEqual("/api/task-service/tasks/17", cm.exception.path)
        self.assertEqual(500, cm.exception.status)
        self.assertEqual({"error": "broken"}, cm.exception.payload)

    @patch("urllib.request.urlopen")
    def test_request_json_sends_json_body(self, urlopen) -> None:
        urlopen.return_value = _FakeResponse(200, {"ok": True})

        client = ApiClient("http://localhost")

        payload = client.request_json("POST", "/api/task-service/tasks/17", {"name": "seed"})
        request = urlopen.call_args.args[0]

        self.assertEqual({"ok": True}, payload)
        self.assertEqual("POST", request.get_method())
        self.assertEqual("http://localhost/api/task-service/tasks/17", request.full_url)
        self.assertEqual(b'{"name": "seed"}', request.data)
        self.assertEqual("application/json", request.get_header("Content-type"))

    def test_poll_until_retries_until_condition_is_met(self) -> None:
        attempts = iter((None, None, {"ID": 9}))

        result = poll_until(
            lambda: next(attempts),
            lambda value: value is not None,
            timeout_seconds=1.0,
            interval_seconds=0.0,
        )

        self.assertEqual({"ID": 9}, result)


if __name__ == "__main__":
    unittest.main()
