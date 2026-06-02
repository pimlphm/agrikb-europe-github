param(
    [switch]$NoInstall,
    [switch]$ForceApiBackend
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Find-Python {
    $candidates = @()
    if ($env:KNOWLEDGE_RAG_PYTHON) { $candidates += $env:KNOWLEDGE_RAG_PYTHON }
    $candidates += @(
        (Join-Path $RootDir "runtime\python311\python.exe"),
        (Join-Path $RootDir ".venv\Scripts\python.exe")
    )
    $candidates += @(
        "C:\ProgramData\anaconda3\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }

    foreach ($candidate in $candidates | Where-Object { $_ } | Select-Object -Unique) {
        try {
            $version = & $candidate -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
            & $candidate -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
            if ($LASTEXITCODE -eq 0) {
                return [pscustomobject]@{ Path = $candidate; Version = $version }
            }
        } catch {
            continue
        }
    }
    return $null
}

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

function Set-DotEnvValue($Values, [string]$Key, [string]$Value) {
    if ($null -ne $Value -and $Value -ne "") {
        $Values[$Key] = $Value
    }
}

function Get-PlainText([securestring]$SecureValue) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Get-ValueOrDefault($Values, [string]$Key, [string]$DefaultValue) {
    if ($Values.Contains($Key) -and $null -ne $Values[$Key] -and $Values[$Key] -ne "") {
        return $Values[$Key]
    }
    return $DefaultValue
}

function Write-DotEnv([string]$Path, $Values) {
    $lines = @(
        "# Trusted-PC local runtime configuration.",
        "# Keep this .env private. Do not upload it to GitHub, screenshots, or public storage.",
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

function Test-OllamaService([string]$BaseUrl) {
    $result = [ordered]@{ available = $false; models = @(); error = "" }
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/tags" -Method Get -TimeoutSec 5
        $result.available = $true
        if ($response.models) {
            $result.models = @($response.models | ForEach-Object { $_.name } | Where-Object { $_ })
        }
    } catch {
        $result.error = $_.Exception.Message
    }
    return [pscustomobject]$result
}

function Get-ApiModels([string]$BaseUrl, [string]$ApiKey) {
    if (-not $ApiKey) { return @() }
    try {
        $headers = @{ Authorization = "Bearer $ApiKey" }
        $response = Invoke-RestMethod -Uri "$BaseUrl/models" -Method Get -Headers $headers -TimeoutSec 10
        if ($response.data) {
            return @($response.data | ForEach-Object { $_.id } | Where-Object { $_ })
        }
    } catch {
        return @()
    }
    return @()
}

function Select-ApiModel($Models, [string]$CurrentModel) {
    if ($CurrentModel -and (($Models.Count -eq 0) -or ($Models -contains $CurrentModel))) {
        return $CurrentModel
    }
    $preferred = @(
        "kimi-for-coding",
        "kimi-k2.5",
        "kimi-k2.6",
        "moonshot-v1-8k",
        "moonshot-v1-32k",
        "moonshot-v1-128k",
        "kimi-latest",
        "kimi-k2-0711-preview"
    )
    foreach ($model in $preferred) {
        if ($Models -contains $model) { return $model }
    }
    if ($Models.Count -gt 0) { return $Models[0] }
    return "kimi-for-coding"
}

function Test-ApiBackend([string]$BaseUrl, [string]$ApiKey, [string]$Model) {
    if (-not $ApiKey -or -not $Model) { return $false }
    try {
        $headers = @{ Authorization = "Bearer $ApiKey"; "Content-Type" = "application/json" }
        $body = @{
            model = $Model
            messages = @(@{ role = "user"; content = "ping" })
            temperature = 0
            max_tokens = 4
        } | ConvertTo-Json -Depth 8
        $response = Invoke-WebRequest -Uri "$BaseUrl/chat/completions" -Method Post -Headers $headers -Body $body -TimeoutSec 30 -UseBasicParsing
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

Write-Step "Detecting Python and creating local runtime"
$python = Find-Python
if (-not $python) {
    throw "Python 3.10+ was not found. Install Python 3.10+ or Anaconda, then run this script again."
}

$venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python.Path -m venv (Join-Path $RootDir ".venv")
}

if (-not $NoInstall) {
    Write-Step "Installing runtime dependencies"
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r (Join-Path $RootDir "requirements-runtime.txt")
}

$envPath = Join-Path $RootDir ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $RootDir ".env.example") -Destination $envPath
}

$envValues = Read-DotEnv $envPath
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_BACKEND" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_BACKEND" "kimi_cli")
Set-DotEnvValue $envValues "OLLAMA_BASE_URL" (Get-ValueOrDefault $envValues "OLLAMA_BASE_URL" "http://localhost:11434")
Set-DotEnvValue $envValues "OLLAMA_MODEL" (Get-ValueOrDefault $envValues "OLLAMA_MODEL" "qwen2.5:7b-instruct")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_BASE_URL" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_BASE_URL" "https://api.kimi.com/coding/v1")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_MODEL" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_MODEL" "kimi-for-coding")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_API_KEY" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_API_KEY" "")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS" "false")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_EMBEDDING_MODEL" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_EMBEDDING_MODEL" "")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_HOST" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_HOST" "127.0.0.1")
Set-DotEnvValue $envValues "KNOWLEDGE_RAG_PORT" (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_PORT" "8010")
Set-DotEnvValue $envValues "KIMI_API_KEY" (Get-ValueOrDefault $envValues "KIMI_API_KEY" $envValues["KNOWLEDGE_RAG_API_KEY"])
Set-DotEnvValue $envValues "MOONSHOT_API_KEY" (Get-ValueOrDefault $envValues "MOONSHOT_API_KEY" $envValues["KNOWLEDGE_RAG_API_KEY"])
Set-DotEnvValue $envValues "AGRIKB_FRONTEND_KIMI_API_KEY" (Get-ValueOrDefault $envValues "AGRIKB_FRONTEND_KIMI_API_KEY" $envValues["KNOWLEDGE_RAG_API_KEY"])
Set-DotEnvValue $envValues "AGRIKB_KIMI_TIMEOUT" (Get-ValueOrDefault $envValues "AGRIKB_KIMI_TIMEOUT" "180")
Set-DotEnvValue $envValues "AGRIKB_KIMI_MAX_RETRIES" (Get-ValueOrDefault $envValues "AGRIKB_KIMI_MAX_RETRIES" "1")
Set-DotEnvValue $envValues "AGRIKB_KIMI_CACHE" (Get-ValueOrDefault $envValues "AGRIKB_KIMI_CACHE" "true")
Set-DotEnvValue $envValues "AGRIKB_FAST_MODE" (Get-ValueOrDefault $envValues "AGRIKB_FAST_MODE" "true")

Write-Step "Detecting Ollama and API backend"
$ollamaCommand = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaStatus = Test-OllamaService $envValues["OLLAMA_BASE_URL"]
$requestedBackend = (Get-ValueOrDefault $envValues "KNOWLEDGE_RAG_BACKEND" "auto").ToLowerInvariant()
if (-not $ForceApiBackend -and $requestedBackend -eq "auto" -and -not $ollamaStatus.available -and -not $envValues["KNOWLEDGE_RAG_API_KEY"]) {
    Write-Host "Ollama is not available and no API key is configured." -ForegroundColor Yellow
    $answer = Read-Host "Configure an API key now on this computer? (Y/N)"
    if ($answer -in @("Y", "y", "YES", "yes")) {
        $baseInput = Read-Host "API base URL [https://api.kimi.com/coding/v1]"
        if ($baseInput) { $envValues["KNOWLEDGE_RAG_BASE_URL"] = $baseInput }
        $modelInput = Read-Host "Chat model [kimi-for-coding]"
        if ($modelInput) { $envValues["KNOWLEDGE_RAG_MODEL"] = $modelInput }
        $secureKey = Read-Host "Paste the API key for this computer" -AsSecureString
        $plainKey = Get-PlainText $secureKey
        if ($plainKey) {
            $envValues["KNOWLEDGE_RAG_API_KEY"] = $plainKey
            $envValues["KNOWLEDGE_RAG_BACKEND"] = "kimi_cli"
        }
    }
}
$apiModels = Get-ApiModels $envValues["KNOWLEDGE_RAG_BASE_URL"] $envValues["KNOWLEDGE_RAG_API_KEY"]
$selectedApiModel = Select-ApiModel $apiModels $envValues["KNOWLEDGE_RAG_MODEL"]
$envValues["KNOWLEDGE_RAG_MODEL"] = $selectedApiModel
$apiAvailable = Test-ApiBackend $envValues["KNOWLEDGE_RAG_BASE_URL"] $envValues["KNOWLEDGE_RAG_API_KEY"] $selectedApiModel

if ($ForceApiBackend) {
    if (-not $envValues["KNOWLEDGE_RAG_API_KEY"]) {
        Write-Host "API backend was forced, but KNOWLEDGE_RAG_API_KEY is empty." -ForegroundColor Yellow
    }
    $envValues["KNOWLEDGE_RAG_BACKEND"] = if ($envValues["KNOWLEDGE_RAG_BASE_URL"] -like "*api.kimi.com/coding*") { "kimi_cli" } else { "openai_compatible" }
} elseif ($requestedBackend -eq "kimi_cli") {
    $envValues["KNOWLEDGE_RAG_BACKEND"] = "kimi_cli"
} elseif ($requestedBackend -in @("openai", "openai_compatible", "api_key")) {
    $envValues["KNOWLEDGE_RAG_BACKEND"] = "openai_compatible"
} elseif ($envValues["KNOWLEDGE_RAG_API_KEY"] -and $envValues["KNOWLEDGE_RAG_BASE_URL"] -like "*api.kimi.com/coding*") {
    $envValues["KNOWLEDGE_RAG_BACKEND"] = "kimi_cli"
} elseif ($envValues["KNOWLEDGE_RAG_API_KEY"]) {
    $envValues["KNOWLEDGE_RAG_BACKEND"] = "openai_compatible"
} elseif ($ollamaStatus.available) {
    $envValues["KNOWLEDGE_RAG_BACKEND"] = "ollama"
    if ($ollamaStatus.models.Count -gt 0 -and -not ($ollamaStatus.models -contains $envValues["OLLAMA_MODEL"])) {
        $envValues["OLLAMA_MODEL"] = $ollamaStatus.models[0]
    }
} else {
    $envValues["KNOWLEDGE_RAG_BACKEND"] = "auto"
}

if ($envValues["KNOWLEDGE_RAG_BACKEND"] -in @("openai_compatible", "kimi_cli")) {
    $envValues["KNOWLEDGE_RAG_REMOTE_EMBEDDINGS"] = "false"
}

Write-DotEnv $envPath $envValues

New-Item -ItemType Directory -Path (Join-Path $RootDir "runtime") -Force | Out-Null
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
$report = [pscustomobject]@{
    generated_at = (Get-Date).ToString("s")
    root = $RootDir
    python_source = $python.Path
    python_version = $python.Version
    venv_python = $venvPython
    os = (Get-CimInstance Win32_OperatingSystem).Caption
    memory_gb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
    nvidia_smi_available = [bool]$nvidiaSmi
    ollama_command_available = [bool]$ollamaCommand
    ollama_service_available = [bool]$ollamaStatus.available
    ollama_base_url = $envValues["OLLAMA_BASE_URL"]
    ollama_models = $ollamaStatus.models
    api_key_configured = [bool]$envValues["KNOWLEDGE_RAG_API_KEY"]
    api_base_url = $envValues["KNOWLEDGE_RAG_BASE_URL"]
    api_connection_available = [bool]$apiAvailable
    api_models_detected = $apiModels
    selected_backend = $envValues["KNOWLEDGE_RAG_BACKEND"]
    selected_model = if ($envValues["KNOWLEDGE_RAG_BACKEND"] -eq "ollama") { $envValues["OLLAMA_MODEL"] } else { $envValues["KNOWLEDGE_RAG_MODEL"] }
    remote_embeddings = $envValues["KNOWLEDGE_RAG_REMOTE_EMBEDDINGS"]
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $RootDir "runtime\environment_report.json") -Encoding UTF8

Write-Step "Validating backend import"
& $venvPython -c "from src.backend.app import app; print('backend import OK')"

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Selected backend: $($report.selected_backend)"
Write-Host "Selected model: $($report.selected_model)"
Write-Host "Environment report: runtime\environment_report.json"
