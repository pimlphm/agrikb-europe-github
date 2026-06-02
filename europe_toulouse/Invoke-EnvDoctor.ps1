param(
    [switch]$InstallMissing,
    [int]$Port = 0,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$RootDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
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

function Write-DotEnv([string]$Path, $Values) {
    $lines = @(
        "# Trusted-PC local runtime configuration.",
        "# Keep this .env private. Do not upload it to GitHub or public storage.",
        "",
        "KNOWLEDGE_RAG_BACKEND=$($Values['KNOWLEDGE_RAG_BACKEND'])",
        "OLLAMA_BASE_URL=$($Values['OLLAMA_BASE_URL'])",
        "OLLAMA_MODEL=$($Values['OLLAMA_MODEL'])",
        "",
        "KNOWLEDGE_RAG_BASE_URL=$($Values['KNOWLEDGE_RAG_BASE_URL'])",
        "KNOWLEDGE_RAG_MODEL=$($Values['KNOWLEDGE_RAG_MODEL'])",
        "KNOWLEDGE_RAG_API_KEY=$($Values['KNOWLEDGE_RAG_API_KEY'])",
        "KIMI_API_KEY=$($Values['KIMI_API_KEY'])",
        "MOONSHOT_API_KEY=$($Values['MOONSHOT_API_KEY'])",
        "AGRIKB_FRONTEND_BASE_URL=$($Values['AGRIKB_FRONTEND_BASE_URL'])",
        "AGRIKB_FRONTEND_MODEL=$($Values['AGRIKB_FRONTEND_MODEL'])",
        "AGRIKB_FRONTEND_KIMI_API_KEY=$($Values['AGRIKB_FRONTEND_KIMI_API_KEY'])",
        "AGRIKB_KIMI_TIMEOUT=$($Values['AGRIKB_KIMI_TIMEOUT'])",
        "AGRIKB_KIMI_MAX_RETRIES=$($Values['AGRIKB_KIMI_MAX_RETRIES'])",
        "AGRIKB_KIMI_CACHE=$($Values['AGRIKB_KIMI_CACHE'])",
        "AGRIKB_FAST_MODE=$($Values['AGRIKB_FAST_MODE'])",
        "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS=$($Values['KNOWLEDGE_RAG_REMOTE_EMBEDDINGS'])",
        "KNOWLEDGE_RAG_EMBEDDING_MODEL=$($Values['KNOWLEDGE_RAG_EMBEDDING_MODEL'])",
        "",
        "KNOWLEDGE_RAG_HOST=$($Values['KNOWLEDGE_RAG_HOST'])",
        "KNOWLEDGE_RAG_PORT=$($Values['KNOWLEDGE_RAG_PORT'])"
    )
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

function Set-DefaultValue($Values, [string]$Key, [string]$Value) {
    if (-not $Values.Contains($Key) -or -not $Values[$Key]) {
        $Values[$Key] = $Value
    }
}

function Apply-ProcessEnv($Values) {
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

function Test-PythonImports([string]$Python) {
    if (-not (Test-Path -LiteralPath $Python)) {
        return [pscustomobject]@{ ok = $false; missing = @("python"); error = "Python not found" }
    }
    $script = @"
import importlib, json
modules = ["fastapi", "uvicorn", "yaml", "requests", "bs4", "rank_bm25"]
missing = []
for name in modules:
    try:
        importlib.import_module(name)
    except Exception:
        missing.append(name)
print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False))
"@
    try {
        $raw = $script | & $Python -
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{ ok = $false; missing = @("runtime-import"); error = "Python import command failed" }
        }
        return ($raw | Select-Object -Last 1 | ConvertFrom-Json)
    } catch {
        return [pscustomobject]@{ ok = $false; missing = @("runtime-import"); error = $_.Exception.Message }
    }
}

function Resolve-PythonCandidate {
    $candidates = @()
    $candidates += (Join-Path $RootDir "runtime\python311\python.exe")
    $candidates += (Join-Path $RootDir ".venv\Scripts\python.exe")
    if ($env:KNOWLEDGE_RAG_PYTHON) { $candidates += $env:KNOWLEDGE_RAG_PYTHON }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += $cmd.Source }

    foreach ($candidate in $candidates | Where-Object { $_ } | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        $check = Test-PythonImports $candidate
        if ($check.ok) {
            return [pscustomobject]@{ python = $candidate; imports = $check; repaired = $false }
        }
    }
    foreach ($candidate in $candidates | Where-Object { $_ } | Select-Object -Unique) {
        if (Test-Path -LiteralPath $candidate) {
            return [pscustomobject]@{ python = $candidate; imports = (Test-PythonImports $candidate); repaired = $false }
        }
    }
    return [pscustomobject]@{ python = ""; imports = [pscustomobject]@{ ok = $false; missing = @("python"); error = "No Python candidate found" }; repaired = $false }
}

function Try-InstallRequirements([string]$Python) {
    $requirements = Join-Path $RootDir "requirements-runtime.txt"
    if (-not (Test-Path -LiteralPath $requirements)) {
        return "requirements-runtime.txt not found"
    }
    try {
        & $Python -m pip --version | Out-Null
        if ($LASTEXITCODE -ne 0) { return "pip is not available" }
        & $Python -m pip install -r $requirements --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) { return "pip install returned a non-zero exit code" }
        return ""
    } catch {
        return $_.Exception.Message
    }
}

function Ensure-KimiRuntime($Report) {
    $kimiDir = Join-Path $RootDir "runtime\kimi"
    $kimiExe = Join-Path $kimiDir "kimi.exe"
    $kimiModulePython = Join-Path $kimiDir "python313\python.exe"
    $kimiModuleSitePackages = Join-Path $kimiDir "kimi-cli-tool\Lib\site-packages"
    $kimiModuleExists = (Test-Path -LiteralPath $kimiModulePython) -and (Test-Path -LiteralPath (Join-Path $kimiModuleSitePackages "kimi_cli"))
    if (-not (Test-Path -LiteralPath $kimiExe)) {
        $cmd = Get-Command kimi -ErrorAction SilentlyContinue
        if ($cmd -and (Test-Path -LiteralPath $cmd.Source)) {
            New-Item -ItemType Directory -Force -Path $kimiDir | Out-Null
            Copy-Item -LiteralPath $cmd.Source -Destination $kimiExe -Force
            $Report.repairs += "Copied Kimi CLI from PATH into runtime/kimi."
        }
    }
    $rgDir = Join-Path $RootDir "runtime\kimi\opencode\bin"
    $rgExe = Join-Path $rgDir "rg.exe"
    if (-not (Test-Path -LiteralPath $rgExe)) {
        $rgCmd = Get-Command rg -ErrorAction SilentlyContinue
        if ($rgCmd -and (Test-Path -LiteralPath $rgCmd.Source)) {
            New-Item -ItemType Directory -Force -Path $rgDir | Out-Null
            Copy-Item -LiteralPath $rgCmd.Source -Destination $rgExe -Force
            $Report.repairs += "Copied rg.exe into runtime/kimi/opencode/bin."
        }
    }
    $Report.kimi_cli_exists = ((Test-Path -LiteralPath $kimiExe) -or $kimiModuleExists)
    $Report.kimi_cli_module_exists = $kimiModuleExists
    $Report.rg_exists = Test-Path -LiteralPath $rgExe
    if ($kimiModuleExists) {
        try {
            $oldPythonPath = $env:PYTHONPATH
            $env:PYTHONPATH = "$kimiModuleSitePackages;$oldPythonPath"
            $Report.kimi_cli_version = (& $kimiModulePython -m kimi_cli --version 2>&1 | Select-Object -First 1)
            $env:PYTHONPATH = $oldPythonPath
        } catch {
            if ($null -ne $oldPythonPath) { $env:PYTHONPATH = $oldPythonPath }
        }
    } elseif ($Report.kimi_cli_exists) {
        try { $Report.kimi_cli_version = (& $kimiExe --version 2>&1 | Select-Object -First 1) } catch {}
    }
}

function Test-PortState([int]$RequestedPort, $Report) {
    if ($RequestedPort -le 0) { return }
    try {
        $listener = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
            Where-Object { $_.LocalPort -eq $RequestedPort } |
            Select-Object -First 1
        if ($listener) {
            $Report.port_in_use = $true
            $Report.port_owner_pid = $listener.OwningProcess
            $Report.warnings += "Port $RequestedPort is already listening. Startup will reuse it if it is AgriKB, otherwise choose another port manually with -Port."
        }
    } catch {
        $Report.warnings += "Port check skipped: $($_.Exception.Message)"
    }
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    root = $RootDir
    checks = @()
    repairs = @()
    warnings = @()
    errors = @()
    blocking = @()
    selected_python = ""
    python_imports_ok = $false
    python_missing_modules = @()
    env_file_exists = $false
    api_key_configured = $false
    backend_api_key_configured = $false
    frontend_api_key_configured = $false
    key_repairs = @()
    kimi_cli_exists = $false
    rg_exists = $false
    port_in_use = $false
    port_owner_pid = $null
}

$envPath = Join-Path $RootDir ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    $example = Join-Path $RootDir ".env.example"
    if (Test-Path -LiteralPath $example) {
        Copy-Item -LiteralPath $example -Destination $envPath -Force
        $report.repairs += "Created .env from .env.example."
    } else {
        $report.blocking += ".env and .env.example are both missing."
    }
}

$values = Read-DotEnv $envPath
Set-DefaultValue $values "KNOWLEDGE_RAG_BACKEND" "kimi_cli"
Set-DefaultValue $values "OLLAMA_BASE_URL" "http://localhost:11434"
Set-DefaultValue $values "OLLAMA_MODEL" "qwen2.5:7b-instruct"
Set-DefaultValue $values "KNOWLEDGE_RAG_BASE_URL" "https://api.kimi.com/coding/v1"
Set-DefaultValue $values "KNOWLEDGE_RAG_MODEL" "kimi-for-coding"
Set-DefaultValue $values "AGRIKB_FRONTEND_BASE_URL" $values["KNOWLEDGE_RAG_BASE_URL"]
Set-DefaultValue $values "AGRIKB_FRONTEND_MODEL" $values["KNOWLEDGE_RAG_MODEL"]
Set-DefaultValue $values "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS" "false"
Set-DefaultValue $values "KNOWLEDGE_RAG_EMBEDDING_MODEL" ""
Set-DefaultValue $values "KNOWLEDGE_RAG_HOST" "0.0.0.0"
Set-DefaultValue $values "KNOWLEDGE_RAG_PORT" "8010"
Set-DefaultValue $values "AGRIKB_KIMI_TIMEOUT" "180"
Set-DefaultValue $values "AGRIKB_KIMI_MAX_RETRIES" "1"
Set-DefaultValue $values "AGRIKB_KIMI_CACHE" "true"
Set-DefaultValue $values "AGRIKB_FAST_MODE" "true"
$candidateKey = ""
foreach ($keyName in @("KNOWLEDGE_RAG_API_KEY", "KIMI_API_KEY", "MOONSHOT_API_KEY", "AGRIKB_FRONTEND_KIMI_API_KEY")) {
    if ($values.Contains($keyName) -and $values[$keyName]) {
        $candidateKey = $values[$keyName]
        break
    }
}
if ($candidateKey) {
    foreach ($keyName in @("KNOWLEDGE_RAG_API_KEY", "KIMI_API_KEY", "MOONSHOT_API_KEY", "AGRIKB_FRONTEND_KIMI_API_KEY")) {
        if (-not $values.Contains($keyName) -or -not $values[$keyName]) {
            $values[$keyName] = $candidateKey
            $report.key_repairs += "Filled $keyName from an existing configured API key."
        }
    }
    if ($candidateKey.StartsWith("sk-kimi-")) {
        $values["KNOWLEDGE_RAG_BACKEND"] = "kimi_cli"
        $values["KNOWLEDGE_RAG_BASE_URL"] = "https://api.kimi.com/coding/v1"
        $values["KNOWLEDGE_RAG_MODEL"] = "kimi-for-coding"
        $values["AGRIKB_FRONTEND_BASE_URL"] = "https://api.kimi.com/coding/v1"
        $values["AGRIKB_FRONTEND_MODEL"] = "kimi-for-coding"
        $report.key_repairs += "Detected Kimi Coding Plan key and forced bundled Kimi CLI channel."
    }
}
Write-DotEnv $envPath $values
Apply-ProcessEnv $values

$report.env_file_exists = Test-Path -LiteralPath $envPath
$report.api_key_configured = [bool]$values["KNOWLEDGE_RAG_API_KEY"]
$report.backend_api_key_configured = [bool]$values["KNOWLEDGE_RAG_API_KEY"]
$report.frontend_api_key_configured = [bool]$values["AGRIKB_FRONTEND_KIMI_API_KEY"]
if (-not $report.api_key_configured) {
    $report.blocking += "KNOWLEDGE_RAG_API_KEY is empty. Run 配置API密钥.bat or edit .env."
}

if (-not $report.frontend_api_key_configured) {
    $report.warnings += "AGRIKB_FRONTEND_KIMI_API_KEY is empty. The GUI can still use the backend key, but the frontend/backup key test will fail until configured."
}

Ensure-KimiRuntime $report
if (-not $report.kimi_cli_exists) {
    $report.blocking += "Kimi CLI is missing. runtime/kimi/kimi.exe was not found and no kimi command was available in PATH."
}

$pythonResult = Resolve-PythonCandidate
$selectedPython = $pythonResult.python
if ($selectedPython -and -not $pythonResult.imports.ok -and $InstallMissing) {
    $installError = Try-InstallRequirements $selectedPython
    if ($installError) {
        $report.warnings += "Python dependency auto-install failed: $installError"
    } else {
        $report.repairs += "Installed missing Python packages from requirements-runtime.txt."
    }
    $pythonResult = [pscustomobject]@{ python = $selectedPython; imports = (Test-PythonImports $selectedPython); repaired = $true }
}
$report.selected_python = $pythonResult.python
$report.python_imports_ok = [bool]$pythonResult.imports.ok
$report.python_missing_modules = @($pythonResult.imports.missing)
if (-not $report.selected_python) {
    $report.blocking += "No usable Python was found."
} elseif (-not $report.python_imports_ok) {
    $report.blocking += "Python runtime is missing packages: $($report.python_missing_modules -join ', ')."
}

$requestedPort = if ($Port -gt 0) { $Port } elseif ($values["KNOWLEDGE_RAG_PORT"]) { [int]$values["KNOWLEDGE_RAG_PORT"] } else { 8010 }
Test-PortState $requestedPort $report

$env:AGRIKB_RESOLVED_PYTHON = $report.selected_python
$global:AGRIKB_ENV_DOCTOR_RESULT = [pscustomobject]$report
New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "runtime") | Out-Null
$reportPath = Join-Path $RootDir "runtime\env_doctor_report.json"
$global:AGRIKB_ENV_DOCTOR_RESULT | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
$env:AGRIKB_ENV_DOCTOR_REPORT = $reportPath

if (-not $Quiet) {
    Write-Host ""
    Write-Host "AgriKB environment doctor" -ForegroundColor Cyan
    Write-Host "Python: $($report.selected_python)" -ForegroundColor Gray
    Write-Host "Kimi CLI: $($report.kimi_cli_exists); backend key: $($report.backend_api_key_configured); frontend key: $($report.frontend_api_key_configured); imports: $($report.python_imports_ok)" -ForegroundColor Green
    if ($report.key_repairs.Count -gt 0) {
        Write-Host "API key repairs:" -ForegroundColor Green
        $report.key_repairs | ForEach-Object { Write-Host " - $_" -ForegroundColor Green }
    }
    if ($report.repairs.Count -gt 0) {
        Write-Host "Auto repairs:" -ForegroundColor Green
        $report.repairs | ForEach-Object { Write-Host " - $_" -ForegroundColor Green }
    }
    if ($report.warnings.Count -gt 0) {
        Write-Host "Warnings:" -ForegroundColor Yellow
        $report.warnings | ForEach-Object { Write-Host " - $_" -ForegroundColor Yellow }
    }
}

if ($report.blocking.Count -gt 0) {
    if (-not $Quiet) {
        Write-Host "Blocking issues:" -ForegroundColor Red
        $report.blocking | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
        Write-Host "Report: $reportPath" -ForegroundColor Yellow
    }
    throw "AgriKB startup environment check failed. See runtime\env_doctor_report.json."
}
