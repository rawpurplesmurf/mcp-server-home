#!/bin/bash
set -euo pipefail

# Configuration
REGISTRY="macmini.localdomain:7235"
REGISTRY_USER="admin"
REGISTRY_NAMESPACE="dk-docker"
REGISTRY_PASSWORD="${REGISTRY_PASSWORD:-aeolian}"

# Image names
IMAGES=("mcp-server" "mcp-client" "mcp-ui")
DOCKERFILES=("Dockerfile.server" "Dockerfile.client" "Dockerfile.ui")

echo "========== [1/4] Logging in to the container registry =========="
if ! echo "$REGISTRY_PASSWORD" | podman login \
    --username "$REGISTRY_USER" \
    --password-stdin \
    --tls-verify=false \
    "$REGISTRY"; then
    echo "[ERROR] Podman login failed."
    exit 1
fi

# Build, tag, and push each image
for i in "${!IMAGES[@]}"; do
    IMAGE="${IMAGES[$i]}"
    DOCKERFILE="${DOCKERFILES[$i]}"
    
    echo ""
    echo "========== Building $IMAGE =========="
    echo "[2/4] Building the container image from $DOCKERFILE"
    if ! podman build -f "$DOCKERFILE" -t "$IMAGE:latest" .; then
        echo "[ERROR] Podman build failed for $IMAGE."
        exit 1
    fi

    echo "[3/4] Tagging the image for the remote registry"
    if ! podman tag "$IMAGE:latest" "$REGISTRY/$REGISTRY_NAMESPACE/$IMAGE:latest"; then
        echo "[ERROR] Podman tag failed for $IMAGE."
        exit 1
    fi

    echo "[4/4] Pushing the image to the remote registry"
    if ! podman push --tls-verify=false "$REGISTRY/$REGISTRY_NAMESPACE/$IMAGE:latest"; then
        echo "[ERROR] Podman push failed for $IMAGE."
        exit 1
    fi
    
    echo "✓ $IMAGE completed successfully"
done

echo ""
echo "========== ALL CONTAINERS BUILD AND PUSH SUCCESS =========="
echo "Built and pushed:"
for IMAGE in "${IMAGES[@]}"; do
    echo "  - $REGISTRY/$REGISTRY_NAMESPACE/$IMAGE:latest"
done
