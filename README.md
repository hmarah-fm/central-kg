# Central Knowledge Graph

The `central-kg` workspace provides GraphDB storage, a federated EDC catalog,
the Digital Thread ingestion service, and an API for querying the Central
Knowledge Graph and receiving authenticated telemetry.

## Documentation

Follow the guides in this order:

1. **Start the catalog and Digital Thread:** [Quick start](./QUICK_START.md).
   Start the provider and consumer connectors separately by following the
   [ED-Node startup guide](../../ed-node/README.md).
2. **Resolve a failure:** [Troubleshooting](./TROUBLESHOOTING.md) maps common
   symptoms to causes and recovery steps.
3. **Look up component details or develop the platform:** [Full guide](./FULL_GUIDE.md)
   covers architecture, configuration, GraphDB, PostgreSQL, the Central KG API,
   telemetry, and extension workflows.

## Main services

| Service | Purpose | Host endpoint |
|---|---|---|
| GraphDB | Stores RDF data in the `centralKG` repository | `http://localhost:7200` |
| Federated catalog | Discovers and serves provider offerings | `http://localhost:8184` |
| Digital Thread | Negotiates transfers and loads datasets into GraphDB | Background service |
| Central KG API | Exposes knowledge-graph and telemetry endpoints | `http://localhost/docs` |

Use [`deploy.sh`](./deploy.sh) from this directory to manage central-platform
Compose services. For routine operation, use `stop`/`down`; avoid volume
deletion unless a complete data reset is intended.
