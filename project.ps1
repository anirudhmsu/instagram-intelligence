param(
    [ValidateSet("help", "setup", "check-env", "test", "ingest", "serve", "start", "mcp", "mcp-inspect")]
    [string]$Action = "help",
    [string[]]$Only = @()
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvDir = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
$McpExe = Join-Path $VenvDir "Scripts\mcp.exe"
Set-Location $ProjectRoot

function Assert-Success([string]$Message) {
    if ($LASTEXITCODE -ne 0) { throw "$Message (exit code $LASTEXITCODE)" }
}

function Ensure-Environment {
    if (-not (Test-Path $PythonExe)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv $VenvDir
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv $VenvDir
        } else {
            throw "Python 3 was not found. Install it from python.org and enable Add Python to PATH."
        }
        Assert-Success "Unable to create the virtual environment"
    }
    if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
}

function Install-Dependencies {
    Ensure-Environment
    & $PipExe install -r requirements.txt
    Assert-Success "Dependency installation failed"
}

function Check-Configuration {
    Install-Dependencies
    & $PythonExe -m scripts.check_env
    Assert-Success "Configuration validation failed"
}

function Run-Tests {
    Install-Dependencies
    $PreviousProvider = $env:INSTAGRAM_PROVIDER
    try {
        $env:INSTAGRAM_PROVIDER = "demo"
        & $PythonExe -m pytest -q
        Assert-Success "Tests failed"
    } finally {
        $env:INSTAGRAM_PROVIDER = $PreviousProvider
    }
}

function Run-Ingestion {
    Check-Configuration
    $Arguments = @("-m", "app.ingestion", "--accounts", "accounts.yaml")
    if ($Only.Count -gt 0) { $Arguments += "--only"; $Arguments += $Only }
    & $PythonExe @Arguments
    Assert-Success "Ingestion completed with one or more account errors"
}

switch ($Action) {
    "help" {
        Write-Host ".\project.ps1 setup                    Create venv, install dependencies, ensure .env"
        Write-Host ".\project.ps1 check-env                Validate Instagram configuration"
        Write-Host ".\project.ps1 test                     Run offline tests"
        Write-Host ".\project.ps1 ingest                   Ingest all enabled accounts"
        Write-Host ".\project.ps1 ingest -Only a,b         Ingest selected configured accounts"
        Write-Host ".\project.ps1 serve                    Start FastAPI"
        Write-Host ".\project.ps1 mcp                      Start the MCP stdio server"
        Write-Host ".\project.ps1 mcp-inspect              Open the MCP inspector"
        Write-Host ".\project.ps1 start                    Test, ingest, then start FastAPI"
    }
    "setup" { Install-Dependencies }
    "check-env" { Check-Configuration }
    "test" { Run-Tests }
    "ingest" { Run-Ingestion }
    "serve" {
        Check-Configuration
        & $PythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    }
    "mcp" {
        Install-Dependencies
        & $PythonExe run_mcp.py
    }
    "mcp-inspect" {
        Install-Dependencies
        & $McpExe dev app/mcp_server.py
    }
    "start" {
        Check-Configuration
        Run-Tests
        Run-Ingestion
        & $PythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    }
}

