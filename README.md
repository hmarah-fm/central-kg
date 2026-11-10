# MSC-based (Central) Knowledge Graph

This is a repository to be used for the deployment of the central knowledge graph in the DMS. 

It provides the following components and artifacts
- an openapi service to access the triple store 
- an authenticated Infraflex telemetry ingestion endpoint that stores timestamped measurements in the MSC knowledge graph
- a docker compose, defining all the services specific to the central platform (next to the ed-node services):
  - a triple store: graphdb
  - a postgres intance, used by
    - the federated catalog server for its persistence
    - the digital thread agent, to keep track on the datasets loaded
  - the openapi service
  - the federated catalog
  - the digital thread agent

At running this will:
- Run GraphDB on port 7200
- Run the access API on port 8000

## Set up

### Postgres
- settings: 
  - [postgres.env](./env/postgres.env)
- helpers
  - [psql](./postgres/scripts/psql-shell.sh)
  - [create-inserted-table.sh](./postgres/scripts/create-inserted-table.sh)

Make sure
- posges is started
- the inderted-table is created and empty

### KG API

- settings
  - [api.env](./centralKG_API/api.env)
- helpers
  - [start-api.sh](./centralKG_API/scripts/start-api.sh)
  - [build-image.sh](./centralKG_API/scripts/build-image.sh)

### Stand alone federated catalog

- settings
  - [standalone-catalog.env](./env/standalone-catalog.env)
    - The Docker runtime reads the current connectorcp Vault token from the
      read-only `/vault-token/token` volume. It overrides any token in the
      configuration file; do not copy generated tokens into source-controlled files.

## Run

- helpers
  - [deploy.sh](./deploy.sh)
    - used for starting/stopping cp services

The full platform
```sh
# start all services
./deploy.sh up 

# stope all services
./deploy.sh down
```

### Postgres
```sh
# start postgres
./deploy.sh up central-platform-postgres

# check
postgres/scripts/psql-shell.sh

# stop postgres
./deploy.sh down central-platform-postgres

# create the inserted table
postgres/scripts/create-inserted-table.sh
```

### Graphdb

See [README](./graphdb/README.md).

```sh
# start graphdb
./deploy.sh up central-platform-graphdb
```

### Federated Catalog

When starting the federated catalog, `deploy.sh` builds its Gradle artifact with persistence/Vault support and creates the local Docker image if that image is not already available. This requires Docker and the repository's Gradle wrapper dependencies.

```sh
# start the federated catalog
mkdir -p log
./deploy.sh up central-platform-federated-catalog --detach

# inspect catalog logs
docker logs --tail=100 central-platform-federated-catalog

# stop the federated catalog
./deploy.sh stop central-platform-federated-catalog
```

After changing the catalog Dockerfile or entrypoint, rebuild the image from the
repository root and recreate only the catalog container:

```sh
./gradlew -Ppersistence=true :launchers:standalone-federated-catalog:build
docker build \
  --build-arg JAR=build/libs/standalone-federated-catalog.jar \
  --file launchers/standalone-federated-catalog/src/main/docker/Dockerfile \
  --tag standalone-federated-catalog:latest launchers/standalone-federated-catalog
sh launchers/standalone-federated-catalog/src/test/docker/entrypoint-test.sh
central-kg/deploy.sh up central-platform-federated-catalog --detach --no-deps --force-recreate
```

In Postman, use `HOST=localhost`, `FederatedCatalogPortCatalog=8184`, and
`POST /api/catalog/v1alpha/catalog/query` with a `QuerySpec` body. The API queries
the crawler's cache, so `200 []` does not mean crawling succeeded. Check the
catalog logs for failed crawls: Vault HTTP 403 indicates an invalid token, while
DSP HTTP 401 indicates a participant authentication or credential problem.
The mounted token is loaded at startup; recreate the catalog after rotating it.
If the token volume is mounted but missing or empty, startup fails explicitly.
Without that volume, the image retains the normal EDC token configuration.

When providers require DataProcessor credentials for catalog requests, set
`UNIMAAS_ENABLE_EXTRA_VP_CATALOGREQUEST=true` for the standalone catalog as well
as the connectors (Compose already forwards this flag). This authorizes both
Membership and DataProcessor presentation scopes. A mismatched scope causes
`Invalid query: requested Credentials outside of scope` on the provider and an
empty federated cache even when the assets exist.

The central GraphDB service publishes host port `7200`; it cannot start if another process or container already owns that port. The federated catalog does not depend on the central GraphDB service, so start the catalog directly when GraphDB is already provided elsewhere.

## Digital thread

```sh
# start the digital thread
./deploy.sh up central-platform-digital-thread 2>&1 | tee log/central-platform-digital-thread-run10.log

# stop the digital thread
./deploy.sh down central-platform-digital-thread 
```

## API

See [README](./centralKG_API/README.md).

```sh
# start the api
./deploy.sh up central-platform-kg-api 2>&1 | tee log/central-platform-kg-api-run10.log

# stop the api
./deploy.sh down central-platform-kg-api 
```

The API also accepts WP4 Infraflex monitoring batches at `POST /telemetry/events`. Configure `DMS_SPARQL_UPDATE_ADDRESS`, `DMS_TELEMETRY_API_KEY`, and `DMS_TELEMETRY_NAMESPACE` in `centralKG_API/api.env`; see the [API guide](./centralKG_API/README.md#infraflex-telemetry-ingestion) for the request format and GraphDB vocabulary setup. EDC remains the governed transport and catalog mechanism.
