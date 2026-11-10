import json
from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlsplit


MSC_NAMESPACE = "http://unimaas-project.eu/MSCOntology#"
TELEMETRY_NAMESPACE = "http://unimaas-project.eu/InfraflexTelemetry#"


def _validate_namespace(namespace: str) -> str:
    parsed = urlsplit(namespace)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or any(character.isspace() or character in "<>\"{}|^`\\" for character in namespace)
    ):
        raise ValueError("The telemetry namespace must be an absolute HTTP(S) URL")
    return namespace.rstrip("/")


def _segment(value: object) -> str:
    return quote(str(value), safe="-._~")


def _literal(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def observation_iri(namespace: str, source_id: str, event_id: str) -> str:
    base = _validate_namespace(namespace)
    return f"{base}/observations/{_segment(source_id)}/{_segment(event_id)}"


def serialize_events(
    events: Iterable[Mapping[str, object]], namespace: str
) -> str:
    base = _validate_namespace(namespace)
    triples = [
        f"@prefix ifx: <{TELEMETRY_NAMESPACE}> .",
        f"@prefix sc: <{MSC_NAMESPACE}> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
    ]

    for event in events:
        try:
            value = Decimal(str(event["value"]))
        except (InvalidOperation, KeyError) as error:
            raise ValueError("Each event must contain a numeric value") from error
        if not value.is_finite():
            raise ValueError("Telemetry values must be finite numbers")

        asset_iri = f"{base}/assets/{_segment(event['asset_id'])}"
        event_iri = observation_iri(
            base, str(event["source_id"]), str(event["event_id"])
        )
        value_lexical = format(value, "f")
        triples.extend(
            [
                f"<{asset_iri}> a sc:EquipmentResource ;",
                f"    rdfs:label {_literal(event['asset_id'])} .",
                f"<{event_iri}> a ifx:TelemetryObservation ;",
                f"    ifx:observationId {_literal(event['event_id'])} ;",
                f"    ifx:observedAsset <{asset_iri}> ;",
                f"    ifx:sourceId {_literal(event['source_id'])} ;",
                f"    ifx:metricName {_literal(event['metric_name'])} ;",
                f'    ifx:numericValue "{value_lexical}"^^xsd:decimal ;',
                f"    ifx:unit {_literal(event.get('unit', ''))} ;",
                f"    ifx:observedAt {_literal(event['observed_at'])}^^xsd:dateTime .",
                "",
            ]
        )

    return "\n".join(triples)