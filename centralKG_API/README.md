# Access API for the Central KG

This folder implements the access API for the Central KG, as defined by the [openapi def](../docs/openapi.json).

## Run the api natively

Install a conda distribution:
```sh
# install
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh

# check (in a new terminal)
conda list
```

Install the required libraries for running this API. In a conda environment the installation can be done through the following:

```sh
conda install -c conda-forge fastapi
conda install conda-forge::pydantic
pip install fastapi[all] python-dotenv requests uvicorn
```

It expects a SPARQL endpoint accessible and the endpoint user and password. 
This can be set in the `api.env` file through the environment variables:

```sh
DMS_SPARQL_ADDRESS=localhost:3030/msc/data
DMS_SPARQL_UPDATE_ADDRESS=http://localhost:7200/repositories/centralKG/statements
DMS_SPARQL_USER=admin
DMS_SPARQL_PASSWORD=mypassword
DMS_TELEMETRY_API_KEY=<secret shared with the monitoring adapter>
DMS_TELEMETRY_NAMESPACE=http://data.local/graph/infraflex
```

To run the api, execute:
```sh
scripts/start-api.sh
```

The api will run on the port **8000** by default.

## Run the api on docker

See the [Dockerfile](./Dockerfile)

See the [api.env](./api.env)

Do the following:
```sh
# build the image
scripts/build-image.sh

# run the image
docker compose up
```

Open the url `http://localhost/docs` in a browser.

## API Specification and Documentation

This serves as the mid layer for accesing the central knowledge graph in UniMaaS. The API includes generic methods for accesing the knowledge graph content such as: getting all classes, instances, properties and values and also specific MSC queries related to the stage. Additionally, it contains a method for issuing SPARQL SELECT queries for more customized queries that are necessary for the other components. 

The full API documentation, requstd and expected responses can be verified through the swagger in **http://localhost:8000/docs**

## Infraflex telemetry ingestion

`POST /telemetry/events` accepts batches of 1 to 500 timestamped numeric measurements. The API requires the `X-API-Key` header to match `DMS_TELEMETRY_API_KEY`, then writes observations as Turtle to `DMS_SPARQL_UPDATE_ADDRESS`. Each observation links to an MSC `sc:EquipmentResource`; event and asset identifiers are URL-encoded into stable IRIs. Timestamps must include a timezone.

Configure a strong `DMS_TELEMETRY_API_KEY` in the API environment before enabling ingestion. Do not commit the live value. Example request:

```sh
curl -X POST http://localhost:8000/telemetry/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $DMS_TELEMETRY_API_KEY" \
  -d '{"events":[{"event_id":"evt-001","asset_id":"cell-1-robot-2","source_id":"infraflex-edge","metric_name":"motor_temperature","value":62.4,"unit":"degC","observed_at":"2026-10-21T10:30:00Z"}]}'
```

Load [infraflex-telemetry.ttl](../graphdb/config/infraflex-telemetry.ttl) into the existing GraphDB repository before querying these observations:

```sh
curl -u "$DMS_SPARQL_USER:$DMS_SPARQL_PASSWORD" \
  -H "Content-Type: text/turtle" \
  --data-binary @../graphdb/config/infraflex-telemetry.ttl \
  "http://localhost:7200/repositories/centralKG/statements"
```

This endpoint is the Central KG ingestion boundary, not an EDC replacement. In a governed deployment, WP4 monitoring data should still be published and transferred through the EDC connector; a trusted consumer-side adapter can submit the transferred measurements here. EDC policies and participant identities remain responsible for dataset-level access governance.

Run the serializer tests with `python -m unittest discover -s tests` from this directory.


## Useful documentation

- Uvicorn
  - [Home](https://uvicorn.dev/)


