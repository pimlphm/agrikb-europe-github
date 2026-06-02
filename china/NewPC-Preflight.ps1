param(
    [switch]$RealModel,
    [int]$Port = 8098
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Read-DotEnv([string]$Path) {
    $values = [ordered]@{}
    if (-not (Test-Path -LiteralPath $Path)) { return $values }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $key, $value = $line.Split("=", 2)
        $values[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
    }
    return $values
}

function Set-ProcessEnv($Values) {
    foreach ($key in $Values.Keys) {
        if ($key -and $Values[$key]) {
            [Environment]::SetEnvironmentVariable($key, [string]$Values[$key], "Process")
        }
    }
    if (-not $env:KIMI_API_KEY -and $env:KNOWLEDGE_RAG_API_KEY) {
        $env:KIMI_API_KEY = $env:KNOWLEDGE_RAG_API_KEY
    }
    $kimiBin = Join-Path $RootDir "runtime\kimi"
    $kimiRgBin = Join-Path $RootDir "runtime\kimi\opencode\bin"
    if (Test-Path -LiteralPath $kimiBin) {
        $env:PATH = "$kimiBin;$kimiRgBin;$env:PATH"
    }
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    $env:AGRIKB_TRUSTED_PC_ROOT = $RootDir
}

function Resolve-PortablePython {
    $embedded = Join-Path $RootDir "runtime\python311\python.exe"
    if (Test-Path -LiteralPath $embedded) { return $embedded }
    $venv = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venv) { return $venv }
    throw "No portable Python was found."
}

$envValues = Read-DotEnv (Join-Path $RootDir ".env")
Set-ProcessEnv $envValues
$python = Resolve-PortablePython
$kimiExe = Join-Path $RootDir "runtime\kimi\kimi.exe"
$kimiModulePython = Join-Path $RootDir "runtime\kimi\python313\python.exe"
$kimiModuleSitePackages = Join-Path $RootDir "runtime\kimi\kimi-cli-tool\Lib\site-packages"
$kimiModuleExists = (Test-Path -LiteralPath $kimiModulePython) -and (Test-Path -LiteralPath (Join-Path $kimiModuleSitePackages "kimi_cli"))
$report = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    root = $RootDir
    python = $python
    python_exists = (Test-Path -LiteralPath $python)
    venv_exists = (Test-Path -LiteralPath (Join-Path $RootDir ".venv\Scripts\python.exe"))
    kimi_cli_exists = ((Test-Path -LiteralPath $kimiExe) -or $kimiModuleExists)
    kimi_cli_module_exists = $kimiModuleExists
    api_key_configured = [bool]$envValues["KNOWLEDGE_RAG_API_KEY"]
    kimi_key_alias_configured = [bool]$envValues["KIMI_API_KEY"]
    frontend_api_key_configured = [bool]$envValues["AGRIKB_FRONTEND_KIMI_API_KEY"]
    backend = $envValues["KNOWLEDGE_RAG_BACKEND"]
    model = $envValues["KNOWLEDGE_RAG_MODEL"]
    frontend_model = $envValues["AGRIKB_FRONTEND_MODEL"]
    fast_mode = $envValues["AGRIKB_FAST_MODE"]
    cache_enabled = $envValues["AGRIKB_KIMI_CACHE"]
    health_ok = $false
    ui_ok = $false
    settings_ok = $false
    settings_backend_test_ok = $false
    settings_frontend_test_ok = $false
    active_provider = ""
    active_model = ""
    real_model_ok = $false
    real_model_seconds = $null
    errors = @()
}

try {
    if ($kimiModuleExists) {
        $oldPythonPath = $env:PYTHONPATH
        $env:PYTHONPATH = "$kimiModuleSitePackages;$oldPythonPath"
        $report.kimi_cli_version = (& $kimiModulePython -m kimi_cli --version 2>&1 | Select-Object -First 1)
        $env:PYTHONPATH = $oldPythonPath
    } elseif ($report.kimi_cli_exists) {
        $report.kimi_cli_version = (& $kimiExe --version 2>&1 | Select-Object -First 1)
    }
} catch {
    if ($null -ne $oldPythonPath) { $env:PYTHONPATH = $oldPythonPath }
    $report.errors += "Kimi CLI version check failed: $($_.Exception.Message)"
}

try {
    $importScript = @"
from src.backend.utils import load_config
from src.backend.service import create_provider
config = load_config()
provider = create_provider(config)
print(config.get("backend", ""))
print(provider.__class__.__name__)
print(getattr(provider, "model", ""))
print("available=" + str(provider.check_connection()))
"@
    $importLines = @($importScript | & $python -)
    if ($LASTEXITCODE -ne 0) { throw "Backend provider import failed." }
    $report.backend = $importLines[0]
    $report.active_provider = $importLines[1]
    $report.active_model = $importLines[2]
    $report.provider_available = ($importLines[3] -eq "available=True")
} catch {
    $report.errors += "Backend import/provider check failed: $($_.Exception.Message)"
}

if ($RealModel) {
    try {
        $marker = "AGRIKB_REAL_KIMI_OK_20260525"
        $script = @"
import re, time
from src.backend.utils import load_config
from src.backend.service import create_provider
t0 = time.perf_counter()
config = load_config()
provider = create_provider(config)
answer = provider.generate("Return only this exact marker: $marker", system="Follow the user instruction exactly.")
answer = re.sub(r"To resume this session: kimi -r [0-9a-f-]+", "", answer or "").strip()
print(answer)
print("seconds=" + str(round(time.perf_counter() - t0, 2)))
raise SystemExit(0 if "$marker" in answer else 3)
"@
        $modelLines = @($script | & $python -)
        if ($LASTEXITCODE -ne 0) { throw "Real model marker was not returned." }
        $report.real_model_ok = $true
        $secondsLine = $modelLines | Where-Object { $_ -like "seconds=*" } | Select-Object -First 1
        if ($secondsLine) { $report.real_model_seconds = [double]($secondsLine -replace "^seconds=", "") }
    } catch {
        $report.errors += "Real model check failed: $($_.Exception.Message)"
    }
}

$args = @("-m", "uvicorn", "src.backend.app:app", "--host", "127.0.0.1", "--port", "$Port")
$proc = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $RootDir -WindowStyle Hidden -PassThru
try {
    for ($i = 0; $i -lt 40; $i += 1) {
        Start-Sleep -Milliseconds 750
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
            if ($health.status -eq "ok") {
                $report.health_ok = $true
                $report.active_provider = $health.active_provider
                $report.active_model = $health.model
                break
            }
        } catch {}
    }
    if (-not $report.health_ok) { throw "Health check timed out." }
    $ui = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/ui/?v=20260525agri93" -UseBasicParsing -TimeoutSec 10
    $report.ui_ok = ($ui.StatusCode -eq 200)
    $settings = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/settings" -TimeoutSec 10
    $report.settings_ok = [bool]($settings.backend_api_key_present -and $settings.frontend_api_key_present)
    if ($RealModel) {
        $backendBody = @{ target = "backend"; backend = $settings.backend; base_url = $settings.base_url; model = $settings.model } | ConvertTo-Json -Depth 5
        $backendTest = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/settings/test" -Method Post -Body $backendBody -ContentType "application/json" -TimeoutSec 90
        $report.settings_backend_test_ok = [bool]$backendTest.backend_test.ok
        $frontendBody = @{ target = "frontend"; frontend_base_url = $settings.frontend_base_url; frontend_model = $settings.frontend_model } | ConvertTo-Json -Depth 5
        $frontendTest = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/settings/test" -Method Post -Body $frontendBody -ContentType "application/json" -TimeoutSec 90
        $report.settings_frontend_test_ok = [bool]$frontendTest.frontend_test.ok
    }
} catch {
    $report.errors += "Server/UI check failed: $($_.Exception.Message)"
} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}

New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "runtime") | Out-Null
$reportPath = Join-Path $RootDir "runtime\new_pc_preflight_report.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host ""
Write-Host "AgriKB new-PC preflight report: $reportPath" -ForegroundColor Cyan
Write-Host "Python: $($report.python_exists); Kimi CLI: $($report.kimi_cli_exists); backend key: $($report.api_key_configured); frontend key: $($report.frontend_api_key_configured); Provider: $($report.active_provider); UI: $($report.ui_ok)" -ForegroundColor Green
if ($RealModel) {
    Write-Host "Real model: $($report.real_model_ok); seconds: $($report.real_model_seconds)" -ForegroundColor Green
    Write-Host "Settings API tests: backend=$($report.settings_backend_test_ok); frontend=$($report.settings_frontend_test_ok)" -ForegroundColor Green
}
if ($report.errors.Count -gt 0) {
    Write-Host "Preflight found issues:" -ForegroundColor Yellow
    $report.errors | ForEach-Object { Write-Host " - $_" -ForegroundColor Yellow }
    throw "New-PC preflight failed. See runtime\new_pc_preflight_report.json."
}
