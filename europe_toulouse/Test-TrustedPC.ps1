param(
    [int]$Port = 8095,
    [switch]$RealModel
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

$python = Join-Path $RootDir "runtime\python311\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = Join-Path $RootDir ".venv\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "No usable Python was found in this package."
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:AGRIKB_TRUSTED_PC_ROOT = $RootDir
$envPath = Join-Path $RootDir ".env"
if (Test-Path -LiteralPath $envPath) {
    Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $key, $value = $line.Split("=", 2)
        $key = $key.Trim()
        $value = $value.Trim().Trim('"').Trim("'")
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
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

$args = @("-m", "uvicorn", "src.backend.app:app", "--host", "127.0.0.1", "--port", "$Port")
$proc = Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $RootDir -WindowStyle Hidden -PassThru
try {
    $ok = $false
    for ($i = 0; $i -lt 40; $i += 1) {
        Start-Sleep -Milliseconds 750
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
            if ($health.status -eq "ok") { $ok = $true; break }
        } catch {}
    }
    if (-not $ok) { throw "Health check timed out." }
    $ui = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/ui/?v=20260525agri93" -UseBasicParsing -TimeoutSec 10
    if ($ui.StatusCode -ne 200) { throw "UI returned status $($ui.StatusCode)." }
    $models = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/models" -TimeoutSec 10
    if ($models.active_provider -ne "KimiCliProvider") {
        throw "Expected bundled KimiCliProvider, got $($models.active_provider)."
    }
    if ($RealModel) {
        $marker = "AGRIKB_REAL_KIMI_OK_20260525"
        $script = @"
import re
from src.backend.utils import load_config
from src.backend.service import create_provider
config = load_config()
provider = create_provider(config)
answer = provider.generate("Return only this exact marker: $marker", system="Follow the user instruction exactly.")
answer = re.sub(r"To resume this session: kimi -r [0-9a-f-]+", "", answer or "").strip()
print(answer)
raise SystemExit(0 if "$marker" in answer else 3)
"@
        $script | & $python -
        if ($LASTEXITCODE -ne 0) {
            throw "Real Kimi model test failed."
        }
        Write-Host "Real Kimi model call passed through bundled CLI." -ForegroundColor Green
    }
    Write-Host "Trusted PC package smoke test passed: http://127.0.0.1:$Port/ui/?v=20260525agri93" -ForegroundColor Green
} finally {
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}
