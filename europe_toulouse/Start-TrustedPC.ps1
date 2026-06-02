param(
    [switch]$NoBrowser,
    [int]$Port = 0,
    [int]$TtsPort = 8011
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Read-DotEnv([string]$Path) {
    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $values }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $key, $value = $line.Split("=", 2)
        $values[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
    }
    return $values
}

function Resolve-PortablePython {
    if ($env:AGRIKB_RESOLVED_PYTHON -and (Test-Path -LiteralPath $env:AGRIKB_RESOLVED_PYTHON)) {
        return $env:AGRIKB_RESOLVED_PYTHON
    }
    $embedded = Join-Path $RootDir "runtime\python311\python.exe"
    if (Test-Path -LiteralPath $embedded) { return $embedded }
    $venv = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venv) { return $venv }
    throw "Portable Python was not found. Please keep runtime\python311 or .venv in the package."
}

function Test-AgriKBUvicornProcess([int]$ProcessId) {
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        $commandLine = [string]$proc.CommandLine
        return ($commandLine -match "uvicorn" -and $commandLine -match "src\.backend\.app:app")
    } catch {
        return $false
    }
}

function Test-StaleKimiCodingService([string]$HealthUrl, [bool]$ExpectKimiCli) {
    if (-not $ExpectKimiCli) { return $false }
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 4
        return ($health.status -eq "ok" -and [string]$health.active_provider -ne "KimiCliProvider")
    } catch {
        return $false
    }
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:AGRIKB_TRUSTED_PC_ROOT = $RootDir

$doctorPath = Join-Path $RootDir "Invoke-EnvDoctor.ps1"
if (Test-Path -LiteralPath $doctorPath) {
    . $doctorPath -InstallMissing -Port $Port
}

$python = Resolve-PortablePython
$envValues = Read-DotEnv (Join-Path $RootDir ".env")
foreach ($key in $envValues.Keys) {
    if ($key -and $envValues[$key]) {
        [Environment]::SetEnvironmentVariable($key, [string]$envValues[$key], "Process")
    }
}
if (-not $env:KIMI_API_KEY -and $env:KNOWLEDGE_RAG_API_KEY) { $env:KIMI_API_KEY = $env:KNOWLEDGE_RAG_API_KEY }
$kimiBin = Join-Path $RootDir "runtime\kimi"
$kimiRgBin = Join-Path $RootDir "runtime\kimi\opencode\bin"
if (Test-Path -LiteralPath $kimiBin) {
    $env:PATH = "$kimiBin;$kimiRgBin;$env:PATH"
}
$hostName = if ($env:KNOWLEDGE_RAG_HOST) { $env:KNOWLEDGE_RAG_HOST } elseif ($envValues["KNOWLEDGE_RAG_HOST"]) { $envValues["KNOWLEDGE_RAG_HOST"] } else { "0.0.0.0" }
$portValue = if ($Port -gt 0) { [string]$Port } elseif ($env:KNOWLEDGE_RAG_PORT) { $env:KNOWLEDGE_RAG_PORT } elseif ($envValues["KNOWLEDGE_RAG_PORT"]) { $envValues["KNOWLEDGE_RAG_PORT"] } else { "8010" }
$openHost = if ($hostName -in @("0.0.0.0", "::")) { "127.0.0.1" } else { $hostName }
$url = "http://${openHost}:${portValue}/ui/?v=20260525agri93"
$expectsKimiCli = ($env:KIMI_API_KEY -like "sk-kimi-*") -or ($env:KNOWLEDGE_RAG_API_KEY -like "sk-kimi-*") -or ($env:KNOWLEDGE_RAG_BASE_URL -like "*api.kimi.com/coding*") -or ($env:KNOWLEDGE_RAG_MODEL -eq "kimi-for-coding")

Write-Host ""
Write-Host "AgriKB is starting..." -ForegroundColor Green
Write-Host "Project root: $RootDir" -ForegroundColor DarkGray
Write-Host "Python: $python" -ForegroundColor DarkGray
Write-Host "URL: $url" -ForegroundColor Cyan

try {
    $ttsExisting = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::") -and $_.LocalPort -eq $TtsPort } |
        Select-Object -First 1
    if (-not $ttsExisting -and (Test-Path -LiteralPath (Join-Path $RootDir "tools\tts_daemon.py"))) {
        Start-Process -FilePath $python `
            -ArgumentList @("tools\tts_daemon.py", "--host", "127.0.0.1", "--port", "$TtsPort") `
            -WorkingDirectory $RootDir `
            -WindowStyle Hidden | Out-Null
    }
} catch {
    Write-Host "TTS service was not started. Main app is still available: $($_.Exception.Message)" -ForegroundColor Yellow
}

$existing = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -eq [int]$portValue } |
    Select-Object -First 1

if ($existing) {
    $healthUrl = "http://${openHost}:${portValue}/health"
    $isStaleKimiService = Test-StaleKimiCodingService $healthUrl $expectsKimiCli
    if ($isStaleKimiService -and (Test-AgriKBUvicornProcess ([int]$existing.OwningProcess))) {
        Write-Host "Detected an old AgriKB service on port $portValue; restarting it with the bundled Kimi CLI runtime." -ForegroundColor Yellow
        Stop-Process -Id ([int]$existing.OwningProcess) -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Host "The service port is already listening. Opening the page." -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process $url }
        return
    }
}

if (-not $NoBrowser) {
    Start-Process $url
}

& $python -m uvicorn src.backend.app:app --host $hostName --port $portValue
