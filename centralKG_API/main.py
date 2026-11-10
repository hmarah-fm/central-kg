from datetime import datetime
from math import isfinite
import secrets
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import urllib.parse
import os
import requests
from telemetry_rdf import observation_iri, serialize_events

# Load .env file
dotenv_file = "api.env"
load_dotenv(dotenv_file)

SPARQL_ENDPOINT = os.getenv("DMS_SPARQL_ADDRESS")
SPARQL_USER = os.getenv("DMS_SPARQL_USER")
SPARQL_PASSWORD = os.getenv("DMS_SPARQL_PASSWORD")
TELEMETRY_UPDATE_ENDPOINT = os.getenv("DMS_SPARQL_UPDATE_ADDRESS")
TELEMETRY_NAMESPACE = os.getenv(
    "DMS_TELEMETRY_NAMESPACE", "http://data.local/graph/infraflex"
)

app = FastAPI(
    title="Access API for the central KG",
    description="Access API for the central KG of UniMaaS.",
    version="1.0.0",
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)

@app.get("/")
def read_root():
    return {"message": "Central KG API running"}

def run_sparql(query: str):
    """
    Helper function to send a SPARQL query to the remote endpoint.
    Automatically adds the MSC prefix if not already present in the query.
    Returns JSON results or raises HTTPException on error.
    """
    MSC_PREFIX = "PREFIX sc: <http://unimaas-project.eu/MSCOntology#>"
    # Add prefix only if missing
    if "PREFIX sc:" not in query:
        query = MSC_PREFIX + "\n" + query
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "query": query
    }
    try:
        # Use POST instead of GET
        if SPARQL_USER and SPARQL_PASSWORD:
            response = requests.post(
                SPARQL_ENDPOINT,
                data=data,
                headers=headers,
                auth=(SPARQL_USER, SPARQL_PASSWORD),
                timeout=15
            )
        else:
            response = requests.post(
                SPARQL_ENDPOINT,
                data=data,
                headers=headers,
                timeout=15
            )
        # Raise if HTTP status is not 2xx
        response.raise_for_status()
        # Debug if JSON parsing fails
        try:
            return response.json()
        except ValueError:
            # At this point, we know status is 2xx but body is not JSON
            raise HTTPException(
                status_code=502,
                detail=(
                    "SPARQL endpoint returned non-JSON response. "
                    f"Raw body: {response.text[:500]}"
                )
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"SPARQL endpoint error: {e}")

# 1. Get all classes
@app.get("/classes")
def get_all_classes():
    query = """
    SELECT DISTINCT ?class
    WHERE { ?s a ?class }
    ORDER BY ?class
    """
    results = run_sparql(query)
    classes = [b["class"]["value"] for b in results["results"]["bindings"]]
    return {"classes": classes}


# 2. Get all instances of a class
@app.get("/instances")
def get_instances(class_uri: str):
    class_uri = urllib.parse.unquote(class_uri)
    query = f"""
    SELECT DISTINCT ?instance
    WHERE {{ ?instance a <{class_uri}> }}
    ORDER BY ?instance
    """
    results = run_sparql(query)
    instances = [b["instance"]["value"] for b in results["results"]["bindings"]]
    return {"class": class_uri, "instances": instances}


# 3. Get all properties of a class
@app.get("/properties")
def get_properties_for_class(class_uri: str):
    class_uri = urllib.parse.unquote(class_uri)
    query = f"""
    SELECT DISTINCT ?property
    WHERE {{
        ?instance a <{class_uri}> ;
                  ?property ?value .
    }}
    ORDER BY ?property
    """
    results = run_sparql(query)
    properties = [b["property"]["value"] for b in results["results"]["bindings"]]
    return {"class": class_uri, "properties": properties}


# 4. Get all property values of an instance
@app.get("/instance")
def get_properties_for_instance(instance_uri: str):
    instance_uri = urllib.parse.unquote(instance_uri)
    query = f"""
    SELECT DISTINCT ?property ?value
    WHERE {{
        <{instance_uri}> ?property ?value .
    }}
    ORDER BY ?property
    """
    results = run_sparql(query)

    props = [
        {
            "property": b["property"]["value"],
            "value": b["value"]["value"]
        }
        for b in results["results"]["bindings"]
    ]

    return {"instance": instance_uri, "properties": props}


# 5. Get all instances of a class that have a given property
@app.get("/instances/by-property")
def get_instances_with_property(class_uri: str, property_uri: str):
    class_uri = urllib.parse.unquote(class_uri)
    property_uri = urllib.parse.unquote(property_uri)

    query = f"""
    SELECT DISTINCT ?instance
    WHERE {{
        ?instance a <{class_uri}> ;
                  <{property_uri}> ?value .
    }}
    ORDER BY ?instance
    """
    results = run_sparql(query)
    instances = [b["instance"]["value"] for b in results["results"]["bindings"]]
    return {
        "class": class_uri,
        "property": property_uri,
        "instances": instances
    }


# 6. Get all instances of a class with property = value
@app.get("/instances/by-property-value")
def get_instances_with_property_value(class_uri: str, property_uri: str, value: str):
    class_uri = urllib.parse.unquote(class_uri)
    property_uri = urllib.parse.unquote(property_uri)
    value = urllib.parse.unquote(value)

    # Detect if value is URI or literal
    if value.startswith("http://") or value.startswith("https://"):
        value_filter = f"<{value}>"
    else:
        value_filter = f"\"{value}\""

    query = f"""
    SELECT DISTINCT ?instance
    WHERE {{
        ?instance a <{class_uri}> ;
                  <{property_uri}> ?v .
        FILTER(?v = {value_filter})
    }}
    ORDER BY ?instance
    """
    results = run_sparql(query)
    instances = [b["instance"]["value"] for b in results["results"]["bindings"]]

    return {
        "class": class_uri,
        "property": property_uri,
        "value": value,
        "instances": instances
    }


# 7. Run raw SPARQL query
class SPARQLQuery(BaseModel):
    query: str

@app.post("/sparql")
def run_raw_sparql(body: SPARQLQuery):
    results = run_sparql(body.query)
    return results


class InfraflexTelemetryEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    asset_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=128)
    metric_name: str = Field(min_length=1, max_length=128)
    value: float
    unit: str = Field(default="", max_length=32)
    observed_at: datetime


class InfraflexTelemetryBatch(BaseModel):
    events: List[InfraflexTelemetryEvent]


@app.post("/telemetry/events", status_code=202)
def ingest_infraflex_telemetry(
    body: InfraflexTelemetryBatch,
    x_api_key: Optional[str] = Header(default=None),
):
    expected_key = os.getenv("DMS_TELEMETRY_API_KEY")
    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Telemetry ingestion is not configured",
        )
    if not x_api_key or not secrets.compare_digest(
        x_api_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not TELEMETRY_UPDATE_ENDPOINT:
        raise HTTPException(
            status_code=503,
            detail="GraphDB telemetry update endpoint is not configured",
        )
    if not 1 <= len(body.events) <= 500:
        raise HTTPException(
            status_code=422,
            detail="A batch must contain between 1 and 500 events",
        )

    records = []
    seen_event_ids = set()
    for event in body.events:
        if not all(
            value.strip()
            for value in (
                event.event_id,
                event.asset_id,
                event.source_id,
                event.metric_name,
            )
        ):
            raise HTTPException(
                status_code=422,
                detail="Event identifiers and metric name cannot be blank",
            )
        if not isfinite(event.value):
            raise HTTPException(
                status_code=422,
                detail="Telemetry values must be finite numbers",
            )
        if event.observed_at.utcoffset() is None:
            raise HTTPException(
                status_code=422,
                detail="observed_at must include a timezone",
            )
        event_identity = (event.source_id, event.event_id)
        if event_identity in seen_event_ids:
            raise HTTPException(
                status_code=422,
                detail="A batch cannot contain duplicate source_id/event_id pairs",
            )
        seen_event_ids.add(event_identity)

        records.append(
            {
                "event_id": event.event_id,
                "asset_id": event.asset_id,
                "source_id": event.source_id,
                "metric_name": event.metric_name,
                "value": event.value,
                "unit": event.unit,
                "observed_at": event.observed_at.isoformat(),
            }
        )

    try:
        turtle = serialize_events(records, TELEMETRY_NAMESPACE)
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail="Telemetry namespace configuration is invalid",
        ) from error
    try:
        response = requests.post(
            TELEMETRY_UPDATE_ENDPOINT,
            data=turtle.encode("utf-8"),
            headers={"Content-Type": "text/turtle"},
            auth=(SPARQL_USER, SPARQL_PASSWORD)
            if SPARQL_USER and SPARQL_PASSWORD
            else None,
            timeout=15,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="GraphDB rejected the telemetry update",
        ) from error

    return {
        "accepted": len(records),
        "observations": [
            observation_iri(TELEMETRY_NAMESPACE, item["source_id"], item["event_id"])
            for item in records
        ],
    }

#MSC Queries

# 8. MSC: Get stage information for a product
@app.get("/msc/get_stage")
def get_msc_stage(product_uri: str):
    """
    Returns the MSC stage information for a given product.
    """
    product_uri = urllib.parse.unquote(product_uri)

    query = f"""
    PREFIX sc: <http://unimaas-project.eu/MSCOntology#>
    SELECT DISTINCT
        ?processConfig
        ?process
        ?site
        ?resourceConf
        ?resource
        ?supplier
        ?inputProduct
        ?outputProduct
    WHERE {{
        VALUES ?requestedProduct <{product_uri}>
        ?processConfig a sc:ProcessConfiguration ;
                       sc:hasOutput ?requestedProduct .

        OPTIONAL {{
            ?processConfig sc:requiresProcess ?process .
            OPTIONAL {{ ?process sc:isPerformedAt ?site . }}
        }}

        OPTIONAL {{
            ?processConfig sc:usesResourceConf ?resourceConf .
            ?resourceConf sc:refersToResource ?resource .
            OPTIONAL {{ ?resource sc:isProvidedBy ?supplier . }}
        }}

        OPTIONAL {{
            ?processConfig sc:usesResource ?resource .
            OPTIONAL {{ ?resource sc:isProvidedBy ?supplier . }}
        }}

        OPTIONAL {{
            ?processConfig sc:hasInput ?inputProduct .
        }}
    }}
    """

    results = run_sparql(query)

    # Convert bindings into a list of dicts
    rows = []
    for b in results["results"]["bindings"]:
        row = {var: b[var]["value"] for var in b}
        rows.append(row)

    return {
        "product": product_uri,
        "stage_info": rows
    }

# 9. MSC: Get all stages for a product
@app.get("/msc/get_all_stages")
def get_msc_all_stages(product_uri: str):
    """
    Returns all MSC stages (full chain) for a given product.
    """
    product_uri = urllib.parse.unquote(product_uri)

    query = f"""
    PREFIX sc: <http://unimaas-project.eu/MSCOntology#>
    SELECT DISTINCT
        ?processConfig
        ?process
        ?site
        ?resourceConf
        ?resource
        ?supplier
        ?inputProduct
        ?outputProduct
    WHERE {{
        VALUES ?requestedProduct <{product_uri}>

        {{
            SELECT DISTINCT ?processConfig
            WHERE {{
                ?rootPC a sc:ProcessConfiguration ;
                        sc:hasOutput ?requestedProduct .

                {{
                    ?processConfig
                        (sc:hasNextStep|^sc:hasNextStep)*
                        ?rootPC .
                }}
            }}
        }}

        OPTIONAL {{
            ?processConfig sc:requiresProcess ?process .
            OPTIONAL {{ ?process sc:isPerformedAt ?site . }}
        }}

        OPTIONAL {{
            ?processConfig sc:usesResourceConf ?resourceConf .
            ?resourceConf sc:refersToResource ?resource .
            OPTIONAL {{ ?resource sc:isProvidedBy ?supplier . }}
        }}

        OPTIONAL {{
            ?processConfig sc:hasInput ?inputProduct .
        }}

        OPTIONAL {{
            ?processConfig sc:hasOutput ?outputProduct .
        }}
    }}
    """

    results = run_sparql(query)

    rows = []
    for b in results["results"]["bindings"]:
        row = {var: b[var]["value"] for var in b}
        rows.append(row)

    return {
        "product": product_uri,
        "all_stages": rows
    }