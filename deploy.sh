#!/usr/bin/env bash

MODE=${1:-}
SERVICE=${2:-}
COMPOSE_EXTRA_ARGS=("${@:3}")
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$SCRIPT_DIR/../../ed-node/.env-connectorcp"

cd "$SCRIPT_DIR" || exit 1

echo "deploy.sh: deploy ${MODE:-<missing action>} ${SERVICE:-<all services>}"
echo ".. action: ${MODE:-<missing>}"
echo ".. service: ${SERVICE:-<all services>}"
echo ".. env-file: $ENV_FILE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: The file $ENV_FILE does not exist."
  exit 1
fi

# Export variables from the .env file
set -o allexport
source "$ENV_FILE"
set +o allexport

echo "deploy.sh: invoke docker compose $1 $2"
echo ".. CONNECTOR_HOST ${CONNECTOR_HOST}"
echo ".. INSTANCE_NAME ${ED_NODE_INSTANCE_NAME}"
echo

if [[ "$MODE" == "up" && "$SERVICE" == "central-platform-federated-catalog" ]] &&
  ! docker image inspect standalone-federated-catalog:latest >/dev/null 2>&1; then
  echo "deploy.sh: local standalone-federated-catalog image not found; building it"
  if ! (
    cd "$PROJECT_ROOT" &&
      ./gradlew -Ppersistence=true :launchers:standalone-federated-catalog:build &&
      docker build \
        --build-arg JAR=build/libs/standalone-federated-catalog.jar \
        --file launchers/standalone-federated-catalog/src/main/docker/Dockerfile \
        --tag standalone-federated-catalog:latest \
        launchers/standalone-federated-catalog
  ); then
    echo "Error: Failed to build standalone-federated-catalog image."
    exit 1
  fi
fi

if [[ "$MODE" == "up" && ( -z "$SERVICE" || "$SERVICE" == "central-platform-digital-thread" ) ]]; then
  echo "deploy.sh: building digital-thread image from workspace source"
  if ! (
    cd "$PROJECT_ROOT" &&
      ./gradlew :launchers:digital-thread:build &&
      docker build \
        --build-arg JAR=build/libs/digital-thread.jar \
        --file launchers/digital-thread/src/main/docker/Dockerfile \
        --tag digital-thread:latest \
        launchers/digital-thread
  ); then
    echo "Error: Failed to build digital-thread image."
    exit 1
  fi
fi

COMPOSE_ARGS=("$MODE")
if [[ -n "$SERVICE" ]]; then
  COMPOSE_ARGS+=("$SERVICE")
fi
COMPOSE_ARGS+=("${COMPOSE_EXTRA_ARGS[@]}")

docker compose --project-name "${ED_NODE_INSTANCE_NAME}" "${COMPOSE_ARGS[@]}"