# Build the React SPA and stage it into backend/static so the FastAPI App Service
# serves frontend + backend from a single origin. Invoked by the azd `prepackage`
# hook (see azure.yaml).
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$static = Join-Path $root "backend/static"

Write-Host "==> Building frontend in $frontend"
Push-Location $frontend
try {
    npm ci
    npm run build
}
finally {
    Pop-Location
}

Write-Host "==> Staging dist into $static"
if (Test-Path $static) { Remove-Item -Recurse -Force $static }
New-Item -ItemType Directory -Force -Path $static | Out-Null
Copy-Item -Recurse -Force (Join-Path $frontend "dist/*") $static

Write-Host "==> Frontend staged into backend/static"
