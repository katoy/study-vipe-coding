#!/bin/bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-asia-northeast1}"
REPOSITORY="${REPOSITORY:-calculator}"
SERVICE="${SERVICE:-study-vipe-coding}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" || "${PROJECT_ID}" == "(none)" ]]; then
  echo "PROJECT_ID is not set and gcloud has no active project." >&2
  echo "Set PROJECT_ID or run: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE}:${IMAGE_TAG}"

echo "Using project: ${PROJECT_ID}"
echo "Using region: ${REGION}"
echo "Using repository: ${REPOSITORY}"
echo "Using service: ${SERVICE}"
echo "Using image: ${IMAGE_URI}"
echo

echo "Enabling required Google Cloud APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

echo
echo "Creating Artifact Registry repository if needed..."
if gcloud artifacts repositories describe "${REPOSITORY}" --location "${REGION}" >/dev/null 2>&1; then
  echo "Repository already exists: ${REPOSITORY}"
else
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Container images for ${SERVICE}"
fi

echo
echo "Building and pushing container image with Cloud Build..."
gcloud builds submit --tag "${IMAGE_URI}" .

echo
echo "Deploying to Cloud Run..."
deploy_args=(
  run
  deploy
  "${SERVICE}"
  --image "${IMAGE_URI}"
  --region "${REGION}"
  --platform managed
  --allow-unauthenticated
)

env_vars=()
if [[ -n "${RATE_LIMIT_PER_MIN:-}" ]]; then
  env_vars+=("RATE_LIMIT_PER_MIN=${RATE_LIMIT_PER_MIN}")
fi

if [[ -n "${ALLOW_ORIGINS:-}" ]]; then
  env_vars+=("ALLOW_ORIGINS=${ALLOW_ORIGINS}")
fi

if [[ "${#env_vars[@]}" -gt 0 ]]; then
  deploy_args+=(--set-env-vars "$(IFS=,; echo "${env_vars[*]}")")
fi

if [[ -n "${MAX_INSTANCES:-}" ]]; then
  deploy_args+=(--max-instances "${MAX_INSTANCES}")
fi

gcloud "${deploy_args[@]}"

echo
echo "Cloud Run service URL:"
gcloud run services describe "${SERVICE}" \
  --region "${REGION}" \
  --format='value(status.url)'
