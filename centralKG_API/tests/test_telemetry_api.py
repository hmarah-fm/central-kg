import os
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

import main


class TelemetryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.env = patch.dict(os.environ, {"DMS_TELEMETRY_API_KEY": "test-key"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.endpoint = patch.object(
            main, "TELEMETRY_UPDATE_ENDPOINT", "http://graphdb/repositories/centralKG/statements"
        )
        self.endpoint.start()
        self.addCleanup(self.endpoint.stop)
        self.payload = {
            "events": [
                {
                    "event_id": "evt-001",
                    "asset_id": "cell-1-robot-2",
                    "source_id": "infraflex-edge",
                    "metric_name": "motor_temperature",
                    "value": 62.4,
                    "unit": "degC",
                    "observed_at": "2026-10-21T10:30:00Z",
                }
            ]
        }

    def test_writes_valid_batch_to_graphdb(self):
        graphdb_response = Mock()
        with patch("main.requests.post", return_value=graphdb_response) as post:
            response = self.client.post(
                "/telemetry/events",
                json=self.payload,
                headers={"X-API-Key": "test-key"},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["accepted"], 1)
        self.assertEqual(post.call_args.args[0], main.TELEMETRY_UPDATE_ENDPOINT)
        self.assertEqual(post.call_args.kwargs["headers"]["Content-Type"], "text/turtle")
        self.assertIn(
            b"ifx:TelemetryObservation",
            post.call_args.kwargs["data"],
        )
        graphdb_response.raise_for_status.assert_called_once_with()

    def test_rejects_invalid_key_without_writing(self):
        with patch("main.requests.post") as post:
            response = self.client.post(
                "/telemetry/events",
                json=self.payload,
                headers={"X-API-Key": "wrong-key"},
            )

        self.assertEqual(response.status_code, 401)
        post.assert_not_called()

    def test_rejects_timestamp_without_timezone(self):
        payload = {
            "events": [
                {
                    **self.payload["events"][0],
                    "observed_at": "2026-10-21T10:30:00",
                }
            ]
        }

        with patch("main.requests.post") as post:
            response = self.client.post(
                "/telemetry/events",
                json=payload,
                headers={"X-API-Key": "test-key"},
            )

        self.assertEqual(response.status_code, 422)
        post.assert_not_called()

    def test_rejects_duplicate_event_identity_in_batch(self):
        payload = {"events": [*self.payload["events"], self.payload["events"][0]]}

        with patch("main.requests.post") as post:
            response = self.client.post(
                "/telemetry/events",
                json=payload,
                headers={"X-API-Key": "test-key"},
            )

        self.assertEqual(response.status_code, 422)
        post.assert_not_called()

    def test_reports_graphdb_failure(self):
        with patch(
            "main.requests.post",
            side_effect=main.requests.exceptions.ConnectionError,
        ):
            response = self.client.post(
                "/telemetry/events",
                json=self.payload,
                headers={"X-API-Key": "test-key"},
            )

        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()