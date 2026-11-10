import unittest

from telemetry_rdf import observation_iri, serialize_events


class TelemetryRdfTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "event_id": "evt/001",
            "asset_id": "robot cell 1",
            "source_id": "infraflex-edge",
            "metric_name": 'temperature "bearing"',
            "value": 24.75,
            "unit": "degC",
            "observed_at": "2026-10-21T10:30:00+02:00",
        }

    def test_serializes_observation_linked_to_msc_equipment(self):
        turtle = serialize_events([self.event], "https://kg.example/data/infraflex/")

        self.assertIn("a sc:EquipmentResource", turtle)
        self.assertIn("a ifx:TelemetryObservation", turtle)
        self.assertIn("ifx:numericValue \"24.75\"^^xsd:decimal", turtle)
        self.assertIn("ifx:observedAt \"2026-10-21T10:30:00+02:00\"^^xsd:dateTime", turtle)
        self.assertIn('temperature \\\"bearing\\\"', turtle)
        self.assertIn("robot%20cell%201", turtle)
        self.assertIn("evt%2F001", turtle)

    def test_observation_iri_is_stable_and_source_scoped(self):
        first = observation_iri("https://kg.example/data", "edge-a", "event-7")
        second = observation_iri("https://kg.example/data", "edge-b", "event-7")

        self.assertEqual(
            first,
            "https://kg.example/data/observations/edge-a/event-7",
        )
        self.assertNotEqual(first, second)

    def test_rejects_non_http_namespace(self):
        with self.assertRaises(ValueError):
            serialize_events([self.event], "file:///tmp/graph")

    def test_rejects_namespace_with_query_or_fragment(self):
        with self.assertRaises(ValueError):
            serialize_events([self.event], "https://kg.example/data?graph=telemetry")

    def test_rejects_non_finite_values(self):
        event = {**self.event, "value": float("nan")}

        with self.assertRaises(ValueError):
            serialize_events([event], "https://kg.example/data")


if __name__ == "__main__":
    unittest.main()