# Troubleshooting

Use the symptom and logs to identify the failing stage before restarting
services. Normal `up`, `stop`, and `down` commands preserve database volumes;
avoid `down-v` and `fromzero` unless a complete reset is intentional.

For the normal startup sequence, see the [quick start](./QUICK_START.md). For
configuration and component details, see the [full guide](./FULL_GUIDE.md).

## Federated catalog and EDC transfers

| Symptom | Root cause | Resolution |
|---|---|---|
| Federated catalog returns an empty list although provider assets exist | Catalog could not crawl providers because its Vault token was stale/missing, or provider catalog requests required the DataProcessor credential scope in addition to Membership. | The catalog loads the current token from its mounted Vault token volume. Ensure `UNIMAAS_ENABLE_EXTRA_VP_CATALOGREQUEST=true` is enabled for the catalog and connectors, then recreate the catalog: `./deploy.sh up central-platform-federated-catalog --detach --no-deps --force-recreate`. Check catalog/provider logs for Vault `403` or `Invalid query: requested Credentials outside of scope`. |
| Provider reports `Failed to Dispatch TransferRequestMessage` with HTTP 404 to `central-platform-federated-catalog:8182/api/dsp` | The standalone catalog shares connectorcp's participant DID, but its DSP callback was pointed at the catalog's own protocol port instead of the connectorcp DSP proxy. | Set the callback in [`env/standalone-catalog.env`](./env/standalone-catalog.env) to `http://edc-proxy-connectorcp:80/api/dsp`, then recreate the catalog with `./deploy.sh up central-platform-federated-catalog --detach --no-deps --force-recreate`. |
| Provider asset or contract-definition GET returns not found after redeployment | `redeploy_all.sh` uses `down-v`, deleting provider PostgreSQL volumes that held assets, policies, and contract definitions. A full reset can also remove Vault and IdentityHub state. | Restore assets, policies, and contract definitions with Postman requests `411`/`412`/`414` and `511`/`512`/`514` in the [ED-Node collection](../postman/UniMaaS-ED-NODE.postman_collection.json). Restore/reinitialize the affected IdentityHub/Vault participant credentials and signing key. For routine work, use `./deploy.sh connector1` and `./deploy.sh connector2`, not `down-v` or `fromzero`. |
| Negotiation remains `REQUESTED`, times out, or fails with a policy mismatch | A previous Digital Thread implementation constructed a policy that differed from the provider's published offer. A timeout alone does not identify whether the policy, callback, or participant authentication failed. | The current Digital Thread forwards the catalog's published offer and context. Rebuild/recreate with `./deploy.sh up central-platform-digital-thread --detach --no-deps --force-recreate`. If a `401` remains, inspect provider, connectorcp, and IdentityHub logs for the current callback/authentication cause rather than increasing the timeout. |
| Digital Thread logs `ConnectException` when fetching an EDR URL such as `http://localhost:9876/api/public` | `localhost` in an EDR is resolved by the consumer. Inside the Digital Thread container, it points to that container, not connector1 on the host. | Set provider `NGINX_PUBLIC_HOST` to a hostname/IP reachable from the Digital Thread container. For this local deployment, `michel-laptop` is mapped to the Docker host gateway. Apply the connector config from `ed-node` using `./deploy.sh connector1` (and connector2 if needed). The current connector1 config intentionally uses `localhost`, so its transfer is expected to fail from Digital Thread until changed. |
| Proxy responds with HTTP 502 after a connector container is recreated | NGINX resolved and cached the old connector container IP when it started. | Restart the provider proxy after connector recreation. The current `ed-node/deploy.sh` build-up workflow restarts `edc-proxy` after applying the connector configuration. Confirm the upstream error is gone in `docker logs edc-proxy-connector1` or `docker logs edc-proxy-connector2`. |
| Public API request succeeds, then Digital Thread logs `Failed to parse RDF body` / Jena `Content is not allowed in prolog` | Provider's `request-rdf-service-file` is Turtle, but the Digital Thread was configured to parse the response as RDF/XML. | Set `DMS_FILE_SERIALIZATION=TTL` in [`env/digital_thread.env`](./env/digital_thread.env), then recreate the service so the environment takes effect: `./deploy.sh up central-platform-digital-thread --detach --no-deps --force-recreate`. |
| GraphDB does not start and reports host port `7200` is already in use | Another GraphDB process/container is bound to the same host port. | Identify the existing owner and stop only the intended conflicting instance. Do not run standalone `graphdb` and `central-platform-graphdb` simultaneously against the same data directory. |
| Digital Thread starts but no dataset is ingested | Service startup is not proof of successful catalog discovery, negotiation, transfer, or GraphDB insertion. Common prerequisites include the `centralKG` repository and PostgreSQL `inserted_assets` table. | Follow the [quick start](./QUICK_START.md) and verify each stage in order: catalog discovery, negotiation, transfer, then GraphDB ingestion. Initialize the repository and ledger table once; see the component setup section in the [full guide](./FULL_GUIDE.md). |

## Central KG API and telemetry

| Symptom | Root cause | Resolution |
|---|---|---|
| API documentation returns 404 or the API is unreachable | The root Compose deployment maps host port `80` to container port `8000`. | Use `http://localhost/docs` for the Compose deployment. Port `8000` applies only when running the API natively or with a different port mapping. Check `docker ps` and the API container logs. |
| Telemetry endpoint returns HTTP 503 | `DMS_TELEMETRY_API_KEY` or `DMS_SPARQL_UPDATE_ADDRESS` is missing, or the telemetry namespace is invalid. | Set these values in `centralKG_API/api.env`, use an absolute HTTP(S) namespace URL without a query or fragment, then recreate `central-platform-kg-api`. |
| Telemetry endpoint returns HTTP 401 | The `X-API-Key` header does not match the key configured in the API container. | Check `DMS_TELEMETRY_API_KEY` and the request header. Recreate the API container after changing its environment. |
| Telemetry endpoint returns HTTP 502 | The API could not write to GraphDB. | Check GraphDB health, credentials, and the update URL. From the API container, GraphDB should resolve as `central-platform-graphdb:7200`. |

## Deployment safety

For production or network exposure beyond a trusted test environment, the
telemetry API key is only a shared-secret gate, not full IAM. Use TLS, restrict
network access, rotate development credentials, keep secrets out of version
control, and protect raw SPARQL and GraphDB/PostgreSQL management interfaces.

## Quick diagnostics

```bash
docker ps --filter name=central-platform
docker logs --tail=200 central-platform-federated-catalog
docker logs --tail=200 central-platform-digital-thread
docker logs --tail=100 edc-connector-connector1
docker logs --tail=100 edc-connector-connector2
docker logs --tail=100 edc-proxy-connector1
docker logs --tail=100 edc-proxy-connector2
docker logs --tail=100 central-platform-kg-api
```

Keep tokens, passwords, private keys, and credential response bodies out of
shared logs and documentation.
