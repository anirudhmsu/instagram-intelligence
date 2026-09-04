$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Launcher = Join-Path $ProjectRoot "run_mcp.py"
$ClaudeDir = Join-Path $env:APPDATA "Claude"
$ConfigPath = Join-Path $ClaudeDir "claude_desktop_config.json"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment not found. Run '.\project.ps1 setup' first."
}
New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null

if (Test-Path $ConfigPath) {
    try {
        $Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    } catch {
        throw "Existing Claude configuration is invalid JSON. Fix it first: $ConfigPath"
    }
    $Backup = "$ConfigPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $ConfigPath $Backup
    Write-Host "Backup created: $Backup"
} else {
    $Config = [PSCustomObject]@{}
}

if (-not $Config.PSObject.Properties["mcpServers"]) {
    $Config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
}
$Server = [PSCustomObject]@{ command = $PythonExe; args = @($Launcher) }
$Config.mcpServers | Add-Member -NotePropertyName "instagram-health-research" -NotePropertyValue $Server -Force
$Config | ConvertTo-Json -Depth 20 | Set-Content $ConfigPath -Encoding UTF8
Write-Host "Claude Desktop configured: $ConfigPath"
Write-Host "Completely quit and reopen Claude Desktop."

