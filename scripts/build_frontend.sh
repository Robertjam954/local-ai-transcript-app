#!/usr/bin/env sh
# Build the React SPA and stage it into backend/static so the FastAPI App Service
# serves frontend + backend from a single origin. Invoked by the azd `prepackage`
# hook (see azure.yaml). Run from the repo root.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
FRONTEND="$ROOT/frontend"
STATIC="$ROOT/backend/static"

echo "==> Building frontend in $FRONTEND"
cd "$FRONTEND"
npm ci
npm run build

echo "==> Staging dist into $STATIC"
rm -rf "$STATIC"
mkdir -p "$STATIC"
cp -R "$FRONTEND/dist/." "$STATIC/"

echo "==> Frontend staged into backend/static"
