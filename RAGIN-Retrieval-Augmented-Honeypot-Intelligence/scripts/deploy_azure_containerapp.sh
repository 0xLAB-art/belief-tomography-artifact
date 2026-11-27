#!/usr/bin/env bash
# =============================================================================
# RAGIN — Azure Container Apps deployment (real-world, live endpoints)
#
# Deploys: redis (internal), gateway (Rust LLM router), chrollo/don/hisoka
# (Python components) into one Container Apps environment in the existing
# resource group. Cowrie SSH honeypot already runs as ACI (ragin-cowrie-hp).
#
# Usage:
#   RAGIN_LLM_BASE_URL=... RAGIN_LLM_API_KEY=... bash scripts/deploy_azure_containerapp.sh
#
# Required env (falls back to .env):
#   RAGIN_LLM_BASE_URL      OpenAI-compatible base incl. /v1 (e.g. https://api.apmix.ai/v1)
#   RAGIN_LLM_API_KEY       LLM API key
#   RAGIN_API_KEY           Gateway/nginx auth key
#
# Optional:
#   RAGIN_DON_MODEL / RAGIN_HISOKA_MODEL  (default: glm-5.3-flash-free)
#   LOCATION (default: eastus), ACR_NAME (default: auto-generated)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# --- Load .env if present ----------------------------------------------------
if [[ -z "${RAGIN_LLM_API_KEY:-}" || -z "${RAGIN_LLM_BASE_URL:-}" ]] && [[ -f "$PROJECT_DIR/.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$PROJECT_DIR/.env"; set +a
fi
# Legacy Azure staging still accepted (endpoint root -> append /v1).
if [[ -z "${RAGIN_LLM_BASE_URL:-}" && -n "${AZURE_OPENAI_ENDPOINT:-}" ]] \
   && [[ "${AZURE_OPENAI_ENDPOINT:-}" != *apmix* ]]; then
  RAGIN_LLM_BASE_URL="${AZURE_OPENAI_ENDPOINT%/}/openai"
fi
RAGIN_LLM_BASE_URL="${RAGIN_LLM_BASE_URL:?RAGIN_LLM_BASE_URL must be set}"
RAGIN_LLM_API_KEY="${RAGIN_LLM_API_KEY:-${AZURE_OPENAI_KEY:-}}"
: "${RAGIN_LLM_API_KEY:?RAGIN_LLM_API_KEY must be set}"
: "${RAGIN_API_KEY:?RAGIN_API_KEY must be set}"

RG="${RAGIN_AZ_RG:-ragin-honeypot-rg}"
LOCATION="${LOCATION:-eastus}"
ACR_NAME="${ACR_NAME:-raginhp$((RANDOM % 9000 + 1000))}"
APP_ENV="${APP_ENV:-ragin-env}"
DON_MODEL="${RAGIN_DON_MODEL:-glm-5.3-flash-free}"
HISOKA_MODEL="${RAGIN_HISOKA_MODEL:-glm-5.3-flash-free}"
TAG="${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}"

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[deploy] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

command -v az >/dev/null || fail "az CLI not found. Install: https://aka.ms/azure-cli"
az account show >/dev/null 2>&1 || fail "Not logged in to Azure. Run: az login"

# --- 0. Resource group --------------------------------------------------------
az group show -n "$RG" >/dev/null 2>&1 || {
  log "Creating resource group $RG in $LOCATION"
  az group create -n "$RG" -l "$LOCATION" >/dev/null
}

# --- 1. Azure Container Registry (cloud builds — no local docker needed) ------
if ! az acr show -n "$ACR_NAME" -g "$RG" >/dev/null 2>&1; then
  log "Creating ACR '$ACR_NAME' (Basic SKU)"
  az acr create -n "$ACR_NAME" -g "$RG" --sku Basic --admin-enabled true >/dev/null
fi
log "Logging in to ACR"
az acr login -n "$ACR_NAME" >/dev/null
ACR_LOGIN="$(az acr show -n "$ACR_NAME" --query loginServer -o tsv)"

# --- 2. Build images (local docker push; ACR Tasks blocked on this subscription) --
command -v docker >/dev/null || fail "docker not found and ACR Tasks unavailable — install docker or file an Azure support request"
az acr login -n "$ACR_NAME" >/dev/null

log "Building ragin-python:$TAG (local docker)"
docker build -f Dockerfile.python -t "$ACR_LOGIN/ragin-python:$TAG" "$PROJECT_DIR" >/dev/null
log "Pushing ragin-python:$TAG"
docker push "$ACR_LOGIN/ragin-python:$TAG" >/dev/null

# Rust gateway is unneeded on Azure (chrollo/don/hisoka call the LLM direct).
# Build it only when explicitly requested (SKIP_GATEWAY=0).
if [[ "${SKIP_GATEWAY:-1}" == "0" ]]; then
  log "Building gateway:$TAG (local docker)"
  docker build -f Dockerfile.gateway -t "$ACR_LOGIN/gateway:$TAG" "$PROJECT_DIR" >/dev/null
  log "Pushing gateway:$TAG"
  docker push "$ACR_LOGIN/gateway:$TAG" >/dev/null
  GATEWAY_IMAGE="$ACR_LOGIN/gateway:$TAG"
else
  GATEWAY_IMAGE=""
fi
RAGIN_IMAGE="$ACR_LOGIN/ragin-python:$TAG"

# --- 3. Container Apps environment ---------------------------------------------
if ! az containerapp env show -g "$RG" -n "$APP_ENV" >/dev/null 2>&1; then
  log "Creating Container Apps environment '$APP_ENV'"
  az containerapp env create \
    -g "$RG" -n "$APP_ENV" \
    --location "$LOCATION" >/dev/null
fi

REDIS_FQDN="http://redis.internal.$(az containerapp env show -g "$RG" -n "$APP_ENV" --query 'properties.defaultDomain' -o tsv):6379/0"

# --- Registry pull credentials (admin-enabled ACR) --------------------------------
REGISTRY_USER="$(az acr credential show -n "$ACR_NAME" --query username -o tsv)"
REGISTRY_PASS="$(az acr credential show -n "$ACR_NAME" --query 'passwords[0].value' -o tsv)"
REGISTRY_ARGS=(--registry-server "$ACR_LOGIN" --registry-username "$REGISTRY_USER" --registry-password "$REGISTRY_PASS")

# --- Secrets (registered per-app so secretref: resolves at create time) ---------
SECRET_ARGS=(--secrets "ragin-llm-key=$RAGIN_LLM_API_KEY" "ragin-api-key=$RAGIN_API_KEY")

# --- Helper: deploy or update an app --------------------------------------------
deploy_app() {
  local name="$1" image="$2" target_port="$3" external="$4"
  shift 4
  # ACR pull creds only for images we host; docker-hub images need no login.
  local registry_args=()
  if [[ "$image" == "$ACR_LOGIN/"* ]]; then
    registry_args=(--registry-server "$ACR_LOGIN" --registry-username "$REGISTRY_USER" --registry-password "$REGISTRY_PASS")
  fi
  # Ensure this app has a secret store, so secretref: env vars resolve below.
  az containerapp secret set -g "$RG" -n "$name" "${SECRET_ARGS[@]}" >/dev/null 2>&1 || true
  if az containerapp show -g "$RG" -n "$name" >/dev/null 2>&1; then
    if [[ "$image" == "$ACR_LOGIN/"* ]]; then
      az containerapp registry set -g "$RG" -n "$name" \
        --server "$ACR_LOGIN" --username "$REGISTRY_USER" --password "$REGISTRY_PASS" >/dev/null
    fi
    az containerapp update -g "$RG" -n "$name" \
      --image "$image" --set-env-vars "$@" >/dev/null
  else
    local ingress_args=(--ingress external --target-port "$target_port")
    if [[ "$external" == "internal" ]]; then
      ingress_args=(--ingress internal --target-port "$target_port")
    else
      ingress_args+=(--allow-insecure false)
    fi
    az containerapp create -g "$RG" -n "$name" \
      --environment "$APP_ENV" \
      --image "$image" \
      --cpu 1.0 --memory 2.0Gi \
      --min-replicas 1 --max-replicas 2 \
      "${ingress_args[@]}" \
      "${SECRET_ARGS[@]}" \
      "${registry_args[@]}" \
      --env-vars "$@" >/dev/null
  fi
  if [[ "$external" == "external" ]]; then
    az containerapp show -g "$RG" -n "$name" --query 'properties.configuration.ingress.fqdn' -o tsv
  fi
}

# --- 4. redis (internal only) ---------------------------------------------------
log "Deploying redis (internal)"
deploy_app redis "redis:7-alpine" 6379 internal \
  "REDIS_ARGS=appendonly no"

# --- 5. gateway (external) -------------------------------------------------------
if [[ -n "$GATEWAY_IMAGE" ]]; then
  log "Deploying gateway (external)"
  deploy_app gateway "$GATEWAY_IMAGE" 8080 external \
    "TOKENROUTER_API_KEY=placeholder" \
    "RAGIN_API_KEY=secretref:ragin-api-key"
else
  log "Skipping gateway container (SKIP_GATEWAY=1 or no Dockerfile.gateway) — components call the LLM directly"
fi

# --- 6. chrollo / don / hisoka (external, live endpoints) ------------------------
# secretref: values below resolve because deploy_app registers the secrets on
# every app before create/update.
COMMON_ENV=(
  "REDIS_URL=$REDIS_FQDN"
  "API_KEY=secretref:ragin-api-key"
  "RAGIN_LLM_BASE_URL=$RAGIN_LLM_BASE_URL"
  "RAGIN_LLM_API_KEY=secretref:ragin-llm-key"
  "RAGIN_LOG_LEVEL=INFO"
  "RAGIN_BIND_HOST=0.0.0.0"
)

log "Deploying chrollo (external)"
CHROLLO_FQDN=$(deploy_app chrollo "$RAGIN_IMAGE" 8080 external \
  "${COMMON_ENV[@]}" "COMPONENT=chrollo" \
  "RAGIN_GATEWAY_URL=$RAGIN_LLM_BASE_URL" | tail -1)

log "Deploying don (external)"
DON_FQDN=$(deploy_app don "$RAGIN_IMAGE" 8080 external \
  "${COMMON_ENV[@]}" "COMPONENT=don" "RAGIN_DON_MODEL=$DON_MODEL" \
  "RAGIN_GATEWAY_URL=$RAGIN_LLM_BASE_URL" | tail -1)

log "Deploying hisoka (external — the deception endpoint)"
HISOKA_FQDN=$(deploy_app hisoka "$RAGIN_IMAGE" 8080 external \
  "${COMMON_ENV[@]}" "COMPONENT=hisoka" \
  "RAGIN_HISOKA_MODEL=$HISOKA_MODEL" "RAGIN_HISOKA_TIMEOUT=300.0" \
  "RAGIN_HISOKA_GATEWAY_URL=$RAGIN_LLM_BASE_URL" | tail -1)

# --- 6b. jev (external — Jev System One additive classification) --------------
# Jev is additive-only: it never replaces Chrollo/Don/Hisoka, it just answers
# typed questions (noul/choice/score) over attacker state via the free
# opencode zen gateway (/v1/systemone, Bearer public). Env vars come from
# .env (RAGIN_JEVI_BASE_URL / RAGIN_JEVI_API_KEY / RAGIN_JEVI_MODEL); the
# Rust gateway is NOT involved — JevClient POSTs directly to zen.
JEVI_BASE_URL="${RAGIN_JEVI_BASE_URL:-https://opencode.ai/zen/v1}"
JEVI_API_KEY="${RAGIN_JEVI_API_KEY:-public}"
JEVI_MODEL="${RAGIN_JEVI_MODEL:-jev-1.13-free}"
JEVI_ENABLED="${RAGIN_JEVI_ENABLED:-1}"

if [[ "$JEVI_ENABLED" == "1" ]]; then
  log "Deploying jev (external — additive System One classification)"
  JEVI_FQDN=$(deploy_app jev "$RAGIN_IMAGE" 8080 external \
    "REDIS_URL=$REDIS_FQDN" \
    "API_KEY=secretref:ragin-api-key" \
    "COMPONENT=jev" \
    "RAGIN_JEVI_BASE_URL=$JEVI_BASE_URL" \
    "RAGIN_JEVI_API_KEY=$JEVI_API_KEY" \
    "RAGIN_JEVI_MODEL=$JEVI_MODEL" \
    "RAGIN_JEVI_ENABLED=$JEVI_ENABLED" \
    "RAGIN_LOG_LEVEL=INFO" \
    "RAGIN_BIND_HOST=0.0.0.0" | tail -1)
else
  JEVI_FQDN=""
  log "Skipping jev container app (RAGIN_JEVI_ENABLED=0)"
fi

# --- 7. Summary -------------------------------------------------------------------
cat <<EOF

=============================================================================
  RAGIN is LIVE on Azure Container Apps (resource group: $RG)
=============================================================================
  chrollo (session mgmt) : https://$CHROLLO_FQDN
  don     (RAG engine)   : https://$DON_FQDN
  hisoka  (deception)    : https://$HISOKA_FQDN
  jev     (System One)   : ${JEVI_FQDN:-NOT DEPLOYED}  (additive classification)
  redis                  : internal only
  cowrie (SSH honeypot)  : existing ACI attacker-f2ed9d9abd3f:2222,2223

  Health:  curl https://$HISOKA_FQDN/health
  Jev:     curl -X POST https://${JEVI_FQDN}/api/assess -H 'X-API-Key: <key>' -d '{"state":"..."}'
  Logs:    az containerapp logs show -g $RG -n hisoka --follow
  Teardown: az group delete -n $RG --yes   (careful: deletes ACI too)
=============================================================================
EOF
