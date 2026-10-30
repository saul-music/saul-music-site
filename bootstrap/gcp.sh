#!/usr/bin/env bash
# Bootstrap del despliegue del sitio en GCP (CI/CD de este repo). Idempotente.
#
# Crea lo que Terraform todavía no crea: repo de imágenes, dos service accounts (deployer para el
# CI y runtime para Cloud Run, sin acceso a datos) y un proveedor de Workload Identity Federation
# restringido a ESTE repo y a main, dentro del pool existente del proyecto. No toca políticas de
# organización: la excepción que permite servicios públicos ya existe en este proyecto.
#
# Uso:   bootstrap/gcp.sh              # ejecuta
#        DRY_RUN=1 bootstrap/gcp.sh    # solo muestra qué haría (las lecturas sí corren)
#
# No imprime secretos. Al final muestra el proveedor WIF, que va a la variable de GitHub
# GCP_WIF_PROVIDER (no es un secreto).

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-saulapp-music}"
REGION="${REGION:-southamerica-west1}"            # explícita, nunca por defecto
GITHUB_REPO="${GITHUB_REPO:-saulapp-legal/saul-music-site}"
AR_REPO="${AR_REPO:-musicsite}"
DEPLOYER="${DEPLOYER:-musicsite-deployer}"
RUNTIME="${RUNTIME:-musicsite-runtime}"
POOL="${POOL:-github}"
PROVIDER="${PROVIDER:-github-musicsite}"
export CLOUDSDK_CONFIG="${CLOUDSDK_CONFIG:-$HOME/.config/gcloud-saul}"
DRY_RUN="${DRY_RUN:-0}"
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

APIS=(run.googleapis.com artifactregistry.googleapis.com iam.googleapis.com
  iamcredentials.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com)

DEPLOYER_SA="$DEPLOYER@$PROJECT_ID.iam.gserviceaccount.com"
RUNTIME_SA="$RUNTIME@$PROJECT_ID.iam.gserviceaccount.com"

log() { printf '→ %s\n' "$*"; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then printf '  [dry-run] %s\n' "$*"; else "$@" >/dev/null; fi
}

log "proyecto=$PROJECT_ID región=$REGION repo=$GITHUB_REPO dry_run=$DRY_RUN"

state="$(gcloud projects describe "$PROJECT_ID" --format='value(lifecycleState)')"
[[ "$state" == "ACTIVE" ]] || { echo "el proyecto $PROJECT_ID no está ACTIVE" >&2; exit 1; }
NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

# 1. APIs (habilitar una ya habilitada no hace nada).
log "habilitando APIs: ${APIS[*]}"
run gcloud services enable "${APIS[@]}" --project "$PROJECT_ID"

# 2. Repo de imágenes, con tags inmutables (nunca se sobrescribe una imagen publicada).
if gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  log "repo de imágenes $AR_REPO ya existe"
else
  log "creando repo de imágenes $AR_REPO en $REGION"
  run gcloud artifacts repositories create "$AR_REPO" --project "$PROJECT_ID" \
    --location "$REGION" --repository-format docker --immutable-tags \
    --description "Imágenes del sitio de SAÚL música"
fi

# 3. Service accounts: una por componente, con mínimo privilegio.
for sa in "$DEPLOYER" "$RUNTIME"; do
  if gcloud iam service-accounts describe "$sa@$PROJECT_ID.iam.gserviceaccount.com" --project "$PROJECT_ID" >/dev/null 2>&1; then
    log "service account $sa ya existe"
  else
    log "creando service account $sa"
    run gcloud iam service-accounts create "$sa" --project "$PROJECT_ID" --display-name "$sa"
  fi
done

# 4. Permisos. El runtime no tiene ningún rol: el sitio no lee ni escribe datos. El deployer sube
# imágenes a su repo, despliega y actúa como el runtime. run.admin (no developer) porque el
# despliegue público fija la política IAM del servicio.
log "permisos"
run gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --project "$PROJECT_ID" \
  --location "$REGION" --member "serviceAccount:$DEPLOYER_SA" --role roles/artifactregistry.writer
run gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:$DEPLOYER_SA" --role roles/run.admin --condition=None
run gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" --project "$PROJECT_ID" \
  --member "serviceAccount:$DEPLOYER_SA" --role roles/iam.serviceAccountUser

# 5. WIF: solo este repo y solo la rama main pueden actuar como el deployer. El pool es compartido
# con otros repos del proyecto; cada repo tiene su propio proveedor y su propia condición.
if gcloud iam workload-identity-pools describe "$POOL" --location global --project "$PROJECT_ID" >/dev/null 2>&1; then
  log "pool $POOL ya existe"
else
  log "creando pool $POOL"
  run gcloud iam workload-identity-pools create "$POOL" --location global --project "$PROJECT_ID" \
    --display-name "GitHub"
fi
if gcloud iam workload-identity-pools providers describe "$PROVIDER" --workload-identity-pool "$POOL" \
  --location global --project "$PROJECT_ID" >/dev/null 2>&1; then
  log "proveedor $PROVIDER ya existe"
else
  log "creando proveedor $PROVIDER (repo $GITHUB_REPO, rama main)"
  run gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
    --workload-identity-pool "$POOL" --location global --project "$PROJECT_ID" \
    --issuer-uri "https://token.actions.githubusercontent.com" \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition "assertion.repository=='$GITHUB_REPO' && assertion.ref=='refs/heads/main'"
fi
run gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" --project "$PROJECT_ID" \
  --role roles/iam.workloadIdentityUser \
  --member "principalSet://iam.googleapis.com/projects/$NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository/$GITHUB_REPO"

# 6. Verificación: solo metadatos.
log "verificación"
gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" \
  --format='value(name,mode)' 2>/dev/null | sed 's/^/  repo: /' || true
gcloud iam service-accounts list --project "$PROJECT_ID" --format='value(email)' 2>/dev/null \
  | grep -E "^($DEPLOYER|$RUNTIME)@" | sed 's/^/  sa: /' || true
echo "  variable de GitHub GCP_WIF_PROVIDER = projects/$NUMBER/locations/global/workloadIdentityPools/$POOL/providers/$PROVIDER"
