#!/usr/bin/env bash
# Deploy autopsy-band to Azure Container Apps.
# Prerequisites: az CLI logged in, Docker running (or ACR Tasks used for build).
# Usage: ./deploy.sh [resource-group] [location]
set -euo pipefail

RG="${1:-autopsy-band-rg}"
LOCATION="${2:-eastus}"
ACR_NAME="autopsyband$(openssl rand -hex 3)"
APP_NAME="autopsy-band"
ENV_NAME="autopsy-band-env"

echo "==> Resource group: $RG  |  Location: $LOCATION"

# 1. Resource group
az group create --name "$RG" --location "$LOCATION" --output none
echo "✓ Resource group"

# 2. Container Registry
az acr create \
  --resource-group "$RG" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true \
  --output none
echo "✓ ACR: $ACR_NAME"

# 3. Build + push via ACR Tasks (no local Docker needed)
az acr build \
  --registry "$ACR_NAME" \
  --image "${APP_NAME}:latest" \
  .
echo "✓ Image built and pushed"

# 4. ACR credentials
ACR_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USER=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASS=$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)

# 5. Container Apps environment
az containerapp env create \
  --name "$ENV_NAME" \
  --resource-group "$RG" \
  --location "$LOCATION" \
  --output none
echo "✓ Container Apps environment"

# 6. Load env vars from .env (skip comments and blanks)
ENV_ARGS=()
while IFS= read -r line; do
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
  ENV_ARGS+=("--env-vars" "$line")
done < .env

# 7. Create Container App
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --environment "$ENV_NAME" \
  --image "${ACR_SERVER}/${APP_NAME}:latest" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USER" \
  --registry-password "$ACR_PASS" \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2.0Gi \
  "${ENV_ARGS[@]}" \
  --output none

APP_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "✓ Deployed → https://${APP_URL}"
