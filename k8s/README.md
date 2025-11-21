# Kubernetes Deployment

Deploy the MCP system to your local Kubernetes cluster.

## Prerequisites

- Kubernetes cluster running
- Redis and MySQL already available on your network
- Docker images built for each component

## Build and Push Docker Images

From your build host, run the build script:

```bash
cd /path/to/mcp-server-home
./build-agent/build_mcp_containers.sh
```

This will build all three images and push them to `macmini.localdomain:7235/dk-docker/`

## Configuration

1. Edit `configmap.yaml` to update:
   - Network hostnames (Redis, MySQL)
   - Location coordinates (SUN_LAT, SUN_LNG)
   - Timezone (LOCAL_TIMEZONE)

2. Edit `configmap.yaml` secrets section to update:
   - Home Assistant URL and token
   - Ollama URL
   - Whisper URL
   - MySQL password

## Deploy

```bash
# Create namespace and config
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml

# Deploy services
kubectl apply -f mcp-server.yaml
kubectl apply -f mcp-client.yaml
kubectl apply -f mcp-ui.yaml
```

## Access

The UI will be available via LoadBalancer on port 80.

Check service status:
```bash
kubectl get pods -n mcp-system
kubectl get services -n mcp-system
```

View logs:
```bash
kubectl logs -n mcp-system -l app=mcp-server
kubectl logs -n mcp-system -l app=mcp-client
kubectl logs -n mcp-system -l app=mcp-ui
```

## Remove

```bash
kubectl delete -f k8s/
```
