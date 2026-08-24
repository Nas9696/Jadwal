[CmdletBinding()]
param(
    [switch]$Reset,
    [switch]$Stop,
    [switch]$SampleData,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

# Keep the demo self-contained even when the host has a stale or malformed value.
$env:API_CORS_ORIGINS = "http://localhost:3000"

function Invoke-Compose {
    $composeArguments = $args
    & docker compose @composeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed: docker compose $($ComposeArguments -join ' ')"
    }
}

function Wait-Http {
    param([string]$Uri, [string]$Label, [int]$Seconds = 180)
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 4
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Host "[ready] $Label" -ForegroundColor Green
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)
    throw "$Label did not become ready at $Uri. Run: docker compose logs"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is required. Install/start Docker Desktop, then run this command again."
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is installed but its engine is not running. Start Docker Desktop and retry."
}

if ($Stop) {
    Invoke-Compose down
    Write-Host "Professional Manager demo stopped." -ForegroundColor Yellow
    exit 0
}

if ($Reset) {
    Write-Host "Resetting the local school workspace..." -ForegroundColor Cyan
    Invoke-Compose up -d --build postgres api
    Wait-Http -Uri "http://localhost:8000/api/v1/health" -Label "API"
    if ($SampleData) {
        Invoke-Compose exec -T api python -m app.demo_seed --reset
    } else {
        Invoke-Compose exec -T api python -m app.seed --reset
    }
}

Invoke-Compose up -d --build
Wait-Http -Uri "http://localhost:8000/api/v1/health" -Label "API"
Wait-Http -Uri "http://localhost:3000" -Label "Web"

$appUrl = "http://localhost:3000"
Write-Host ""
Write-Host "Professional Manager is ready: $appUrl" -ForegroundColor Green
Write-Host "Reset: .\scripts\demo.ps1 -Reset"
Write-Host "Sample data: .\scripts\demo.ps1 -Reset -SampleData"
Write-Host "Stop : .\scripts\demo.ps1 -Stop"

if (-not $NoBrowser) {
    Start-Process $appUrl
}
