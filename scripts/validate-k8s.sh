#!/bin/bash

# Kubernetes Configuration Validation Script for MCP System
# This script validates all Kubernetes manifests and checks cluster readiness

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="$(dirname "$SCRIPT_DIR")/k8s"

echo "=========================================="
echo "MCP Kubernetes Configuration Validator"
echo "=========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} kubectl is not installed or not in PATH"
    exit 1
fi

echo -e "${GREEN}[✓]${NC} kubectl is available"
echo ""

# Check cluster connectivity
echo "Checking cluster connectivity..."
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}[ERROR]${NC} Cannot connect to Kubernetes cluster"
    exit 1
fi
echo -e "${GREEN}[✓]${NC} Connected to Kubernetes cluster"
echo ""

# Validate YAML syntax for all manifests
echo "Validating YAML syntax..."
MANIFESTS=(
    "$K8S_DIR/namespace.yaml"
    "$K8S_DIR/configmap.yaml"
    "$K8S_DIR/mcp-server.yaml"
    "$K8S_DIR/mcp-client.yaml"
    "$K8S_DIR/mcp-ui.yaml"
)

for manifest in "${MANIFESTS[@]}"; do
    if [ ! -f "$manifest" ]; then
        echo -e "${RED}[ERROR]${NC} Manifest not found: $manifest"
        exit 1
    fi
    
    manifest_name=$(basename "$manifest")
    if kubectl apply --dry-run=client -f "$manifest" &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} $manifest_name - syntax valid"
    else
        echo -e "${RED}[✗]${NC} $manifest_name - syntax error"
        kubectl apply --dry-run=client -f "$manifest"
        exit 1
    fi
done
echo ""

# Validate server-side (checks against API server schemas)
echo "Validating against Kubernetes API server..."
for manifest in "${MANIFESTS[@]}"; do
    manifest_name=$(basename "$manifest")
    if kubectl apply --dry-run=server -f "$manifest" &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} $manifest_name - server validation passed"
    else
        echo -e "${YELLOW}[WARN]${NC} $manifest_name - server validation warning"
        kubectl apply --dry-run=server -f "$manifest" 2>&1 | grep -v "Warning"
    fi
done
echo ""

# Check if namespace exists
echo "Checking namespace..."
if kubectl get namespace mcp-system &> /dev/null; then
    echo -e "${GREEN}[✓]${NC} Namespace 'mcp-system' exists"
else
    echo -e "${YELLOW}[WARN]${NC} Namespace 'mcp-system' does not exist (will be created on apply)"
fi
echo ""

# Check if secrets exist (if namespace exists)
if kubectl get namespace mcp-system &> /dev/null; then
    echo "Checking for required secrets..."
    if kubectl get secret mcp-secrets -n mcp-system &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} Secret 'mcp-secrets' exists"
        
        # Check required secret keys
        REQUIRED_KEYS=("HA_URL" "HA_TOKEN" "OLLAMA_URL" "MYSQL_PASSWORD" "WHISPER_URL")
        for key in "${REQUIRED_KEYS[@]}"; do
            if kubectl get secret mcp-secrets -n mcp-system -o jsonpath="{.data.$key}" &> /dev/null; then
                echo -e "${GREEN}  [✓]${NC} Secret key '$key' present"
            else
                echo -e "${YELLOW}  [WARN]${NC} Secret key '$key' missing"
            fi
        done
    else
        echo -e "${RED}[✗]${NC} Secret 'mcp-secrets' does not exist"
        echo "    Create it with: kubectl create secret generic mcp-secrets -n mcp-system \\"
        echo "      --from-literal=HA_URL=http://your-ha-url \\"
        echo "      --from-literal=HA_TOKEN=your-token \\"
        echo "      --from-literal=OLLAMA_URL=http://ollama:11434 \\"
        echo "      --from-literal=MYSQL_PASSWORD=your-password \\"
        echo "      --from-literal=WHISPER_URL=http://whisper:8000"
    fi
    echo ""
fi

# Check if ConfigMap exists (if namespace exists)
if kubectl get namespace mcp-system &> /dev/null; then
    echo "Checking for ConfigMap..."
    if kubectl get configmap mcp-config -n mcp-system &> /dev/null; then
        echo -e "${GREEN}[✓]${NC} ConfigMap 'mcp-config' exists"
    else
        echo -e "${YELLOW}[WARN]${NC} ConfigMap 'mcp-config' does not exist (will be created on apply)"
    fi
    echo ""
fi

# Check if Ingress controller is available
echo "Checking Ingress controller..."
if kubectl get ingressclass public &> /dev/null; then
    echo -e "${GREEN}[✓]${NC} IngressClass 'public' exists"
elif kubectl get ingressclass &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} IngressClass 'public' not found, but other ingress classes exist:"
    kubectl get ingressclass -o name
else
    echo -e "${RED}[✗]${NC} No Ingress controller found"
    echo "    Install an ingress controller (e.g., microk8s enable ingress)"
fi
echo ""

# Check LoadBalancer support
echo "Checking LoadBalancer support..."
if kubectl get svc -A | grep LoadBalancer | grep -v pending &> /dev/null; then
    echo -e "${GREEN}[✓]${NC} LoadBalancer services are working in cluster"
elif kubectl get svc -A | grep LoadBalancer &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} LoadBalancer services exist but may be pending"
    echo "    Ensure MetalLB or similar is configured (e.g., microk8s enable metallb)"
else
    echo -e "${YELLOW}[WARN]${NC} No LoadBalancer services found in cluster"
    echo "    LoadBalancer support may not be configured"
fi
echo ""

# Check external-dns
echo "Checking external-dns..."
if kubectl get pods -A | grep external-dns | grep Running &> /dev/null; then
    echo -e "${GREEN}[✓]${NC} external-dns is running"
else
    echo -e "${YELLOW}[WARN]${NC} external-dns not found or not running"
    echo "    DNS records may not be automatically created"
fi
echo ""

# Summary
echo "=========================================="
echo "Validation Summary"
echo "=========================================="
echo -e "${GREEN}[✓]${NC} All manifest files are valid"
echo ""
echo "To deploy the MCP system:"
echo "  1. Create secrets if not exists (see above)"
echo "  2. Run: kubectl apply -f $K8S_DIR/namespace.yaml"
echo "  3. Run: kubectl apply -f $K8S_DIR/configmap.yaml"
echo "  4. Run: kubectl apply -f $K8S_DIR/mcp-server.yaml"
echo "  5. Run: kubectl apply -f $K8S_DIR/mcp-client.yaml"
echo "  6. Run: kubectl apply -f $K8S_DIR/mcp-ui.yaml"
echo ""
echo "Or apply all at once:"
echo "  kubectl apply -f $K8S_DIR/"
echo ""
