param(
    [string]$ApiKey = "",
    [string]$BaseUrl = "",
    [string]$Model = "",
    [switch]$Force
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

function Set-DotEnvValue($Values, [string]$Key, [string]$Value) {
    if ($null -ne $Value) { $Values[$Key] = $Value }
}

function Get-ValueOrDefault($Values, [string]$Key, [string]$DefaultValue) {
    if ($Values.Contains($Key) -and $null -ne $Values[$Key] -and $Values[$Key] -ne "") {
        return $Values[$Key]
    }
    return $DefaultValue
}

function Get-PlainText([securestring]$SecureValue) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
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

$envPath = Join-Path $RootDir ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $RootDir ".env.example") -Destination $envPath
}

$values = Read-DotEnv $envPath
Set-DotEnvValue $values "KNOWLEDGE_RAG_BACKEND" "kimi_cli"
Set-DotEnvValue $values "OLLAMA_BASE_URL" (Get-ValueOrDefault $values "OLLAMA_BASE_URL" "http://localhost:11434")
Set-DotEnvValue $values "OLLAMA_MODEL" (Get-ValueOrDefault $values "OLLAMA_MODEL" "qwen2.5:7b-instruct")
Set-DotEnvValue $values "KNOWLEDGE_RAG_BASE_URL" ($(if ($BaseUrl) { $BaseUrl } elseif ($values["KNOWLEDGE_RAG_BASE_URL"]) { $values["KNOWLEDGE_RAG_BASE_URL"] } else { "https://api.kimi.com/coding/v1" }))
Set-DotEnvValue $values "KNOWLEDGE_RAG_MODEL" ($(if ($Model) { $Model } elseif ($values["KNOWLEDGE_RAG_MODEL"]) { $values["KNOWLEDGE_RAG_MODEL"] } else { "kimi-for-coding" }))
Set-DotEnvValue $values "AGRIKB_FRONTEND_BASE_URL" (Get-ValueOrDefault $values "AGRIKB_FRONTEND_BASE_URL" $values["KNOWLEDGE_RAG_BASE_URL"])
Set-DotEnvValue $values "AGRIKB_FRONTEND_MODEL" (Get-ValueOrDefault $values "AGRIKB_FRONTEND_MODEL" $values["KNOWLEDGE_RAG_MODEL"])
Set-DotEnvValue $values "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS" "false"
Set-DotEnvValue $values "KNOWLEDGE_RAG_EMBEDDING_MODEL" (Get-ValueOrDefault $values "KNOWLEDGE_RAG_EMBEDDING_MODEL" "")
Set-DotEnvValue $values "KNOWLEDGE_RAG_HOST" (Get-ValueOrDefault $values "KNOWLEDGE_RAG_HOST" "127.0.0.1")
Set-DotEnvValue $values "KNOWLEDGE_RAG_PORT" (Get-ValueOrDefault $values "KNOWLEDGE_RAG_PORT" "8010")
Set-DotEnvValue $values "AGRIKB_KIMI_TIMEOUT" (Get-ValueOrDefault $values "AGRIKB_KIMI_TIMEOUT" "180")
Set-DotEnvValue $values "AGRIKB_KIMI_MAX_RETRIES" (Get-ValueOrDefault $values "AGRIKB_KIMI_MAX_RETRIES" "1")
Set-DotEnvValue $values "AGRIKB_KIMI_CACHE" (Get-ValueOrDefault $values "AGRIKB_KIMI_CACHE" "true")
Set-DotEnvValue $values "AGRIKB_FAST_MODE" (Get-ValueOrDefault $values "AGRIKB_FAST_MODE" "true")

Write-Host ""
Write-Host "API backend will be configured on this computer only." -ForegroundColor Cyan
Write-Host "Base URL: $($values['KNOWLEDGE_RAG_BASE_URL'])"
Write-Host "Model: $($values['KNOWLEDGE_RAG_MODEL'])"
Write-Host ""

if (-not $ApiKey -and -not $Force -and $values["KNOWLEDGE_RAG_API_KEY"]) {
    $answer = Read-Host "An API key is already configured. Replace it? (Y/N)"
    if ($answer -notin @("Y", "y", "YES", "yes")) {
        Write-Host "Keeping existing API key." -ForegroundColor Yellow
        exit 0
    }
}

$plainKey = $ApiKey.Trim()
if (-not $plainKey) {
    $secureKey = Read-Host "Paste the API key for this computer" -AsSecureString
    $plainKey = Get-PlainText $secureKey
}
if (-not $plainKey) {
    throw "API key is empty. Nothing was changed."
}

Set-DotEnvValue $values "KNOWLEDGE_RAG_API_KEY" $plainKey
Set-DotEnvValue $values "KIMI_API_KEY" $plainKey
Set-DotEnvValue $values "MOONSHOT_API_KEY" $plainKey
Set-DotEnvValue $values "AGRIKB_FRONTEND_KIMI_API_KEY" $plainKey
if ($plainKey.StartsWith("sk-kimi-")) {
    Set-DotEnvValue $values "KNOWLEDGE_RAG_BACKEND" "kimi_cli"
    Set-DotEnvValue $values "KNOWLEDGE_RAG_BASE_URL" "https://api.kimi.com/coding/v1"
    Set-DotEnvValue $values "KNOWLEDGE_RAG_MODEL" "kimi-for-coding"
    Set-DotEnvValue $values "AGRIKB_FRONTEND_BASE_URL" "https://api.kimi.com/coding/v1"
    Set-DotEnvValue $values "AGRIKB_FRONTEND_MODEL" "kimi-for-coding"
}
Write-DotEnv $envPath $values

Write-Host ""
Write-Host "API key configured in local .env." -ForegroundColor Green
Write-Host "Next step: run Start-Portable.ps1 or double-click the startup bat file."
