# Run the federated catalog and Digital Thread

This is the day-to-day start path for the federated catalog and Digital Thread.
It assumes the central services have been initialized. It does not start the
connectors: start connector1, connector2, and connectorcp using the
[ED-Node startup guide](../../ed-node/README.md) first. For a fresh installation
or component configuration details, use the [full guide](./FULL_GUIDE.md).

Run the commands below from `ids-mvd-dms/central-kg`.

## 1. Check prerequisites

The Digital Thread requires healthy connector services, registered provider
assets and contract definitions, the GraphDB repository `centralKG`, and the
PostgreSQL `inserted_assets` table. Create the repository and table once during
initial setup; do not recreate or clear them on normal starts. See the
[full guide](./FULL_GUIDE.md) for first-time
storage initialization.

Each provider's advertised public EDR endpoint must be reachable from the
Digital Thread container.

**Current configuration note:** connector1's `.env-connector1` currently sets
`NGINX_PUBLIC_HOST=localhost`. Its EDR advertises
`http://localhost:9876/api/public`, which the Digital Thread container cannot
reach. To ingest from connector1, configure its public host to a hostname or IP
reachable from the Digital Thread container, then follow the
[ED-Node startup guide](../../ed-node/README.md) to apply the connector
configuration.

## 2. Start the federated catalog

The catalog requires connectorcp and its Identity Hub to be running. The
Compose configuration also checks these dependencies. The deploy wrapper builds
the local catalog image when it is not already available.

```bash
mkdir -p log
./deploy.sh up central-platform-federated-catalog --detach
docker logs --tail=100 central-platform-federated-catalog
```

Check that catalog crawling completes and both provider assets are discoverable:
`request-rdf-service-file` and `request-rdf-service-sparql`.
If the catalog is empty, see the
[troubleshooting guide](./TROUBLESHOOTING.md).

## 3. Start the Digital Thread

The deploy wrapper builds the Digital Thread image from the current workspace
source. It starts central GraphDB and PostgreSQL as Compose dependencies when
they are not already running.

```bash
./deploy.sh up central-platform-digital-thread --detach
docker logs --tail=150 central-platform-digital-thread
```

If `env/digital_thread.env` changes while the container is running, recreate
only the Digital Thread so it receives the updated environment:

```bash
./deploy.sh up central-platform-digital-thread --detach --no-deps --force-recreate
```

## 4. Verify discovery and ingestion

Check the catalog and Digital Thread logs:

```bash
docker logs --tail=200 central-platform-federated-catalog
docker logs --tail=200 central-platform-digital-thread
```

The catalog should discover both assets. A successful Digital Thread cycle
shows `Ingestion in CentralKG Complete` for each transferred asset and then
`Job completed`. The published file asset is Turtle, so
[`env/digital_thread.env`](./env/digital_thread.env) must use
`DMS_FILE_SERIALIZATION=TTL`.

If a transfer or ingestion fails, use the
[troubleshooting guide](./TROUBLESHOOTING.md). It includes the current
connector1 `localhost` EDR limitation.

## 5. Stop these services

Stop only the catalog and Digital Thread; this does not remove database volumes:

```bash
./deploy.sh stop central-platform-federated-catalog
./deploy.sh stop central-platform-digital-thread
```

For connector startup and shutdown, follow the
[ED-Node startup guide](../../ed-node/README.md). Avoid `down-v` or `fromzero`
unless a complete connector data reset is intentional.
