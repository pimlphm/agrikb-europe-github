param(
    [switch]$SkipRealModelTest
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
        "KNOWLEDGE_RAG_REMOTE_EMBEDDINGS=false",
        "KNOWLEDGE_RAG_EMBEDDING_MODEL=",
        "",
        "KNOWLEDGE_RAG_HOST=$($Values['KNOWLEDGE_RAG_HOST'])",
        "KNOWLEDGE_RAG_PORT=$($Values['KNOWLEDGE_RAG_PORT'])"
    )
    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

function Set-Default($Values, [string]$Key, [string]$Value) {
    if (-not $Values.Contains($Key) -or -not $Values[$Key]) { $Values[$Key] = $Value }
}

function Ensure-EnvConfig {
    $envPath = Join-Path $RootDir ".env"
    if (-not (Test-Path -LiteralPath $envPath)) {
        if (Test-Path -LiteralPath (Join-Path $RootDir ".env.example")) {
            Copy-Item -LiteralPath (Join-Path $RootDir ".env.example") -Destination $envPath -Force
        } else {
            New-Item -ItemType File -Path $envPath -Force | Out-Null
        }
    }
    $values = Read-DotEnv $envPath
    Set-Default $values "OLLAMA_BASE_URL" "http://localhost:11434"
    Set-Default $values "OLLAMA_MODEL" "qwen2.5:14b"
    Set-Default $values "KNOWLEDGE_RAG_HOST" "127.0.0.1"
    Set-Default $values "KNOWLEDGE_RAG_PORT" "8010"
    Set-Default $values "AGRIKB_KIMI_TIMEOUT" "180"
    Set-Default $values "AGRIKB_KIMI_MAX_RETRIES" "1"
    Set-Default $values "AGRIKB_KIMI_CACHE" "true"
    Set-Default $values "AGRIKB_FAST_MODE" "true"
    $key = @(
        $values["KNOWLEDGE_RAG_API_KEY"],
        $values["KIMI_API_KEY"],
        $values["MOONSHOT_API_KEY"],
        $values["AGRIKB_FRONTEND_KIMI_API_KEY"]
    ) | Where-Object { $_ } | Select-Object -First 1
    if ($key) {
        $values["KNOWLEDGE_RAG_API_KEY"] = $key
        $values["KIMI_API_KEY"] = $key
        $values["MOONSHOT_API_KEY"] = $key
        $values["AGRIKB_FRONTEND_KIMI_API_KEY"] = $key
    }
    $values["KNOWLEDGE_RAG_BACKEND"] = "kimi_cli"
    $values["KNOWLEDGE_RAG_BASE_URL"] = "https://api.kimi.com/coding/v1"
    $values["KNOWLEDGE_RAG_MODEL"] = "kimi-for-coding"
    $values["AGRIKB_FRONTEND_BASE_URL"] = "https://api.kimi.com/coding/v1"
    $values["AGRIKB_FRONTEND_MODEL"] = "kimi-for-coding"
    $values["KNOWLEDGE_RAG_REMOTE_EMBEDDINGS"] = "false"
    $values["KNOWLEDGE_RAG_EMBEDDING_MODEL"] = ""
    Write-DotEnv $envPath $values
}

function Safe-RemoveUnderRoot([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $rootResolved = (Resolve-Path -LiteralPath $RootDir).Path
    $targetResolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not $targetResolved.StartsWith($rootResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside AgriKB: $targetResolved"
    }
    Remove-Item -LiteralPath $targetResolved -Recurse -Force
}

function Copy-TreeFresh([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source)) { throw "Missing source: $Source" }
    Safe-RemoveUnderRoot $Destination
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Find-UvToolDir {
    $candidates = @(
        (Join-Path $env:APPDATA "uv\tools\kimi-cli"),
        (Join-Path $env:USERPROFILE ".local\share\uv\tools\kimi-cli")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $candidate "Lib\site-packages\kimi_cli")) { return $candidate }
    }
    return ""
}

function Find-UvPythonDir([string]$ToolDir) {
    $pyvenv = Join-Path $ToolDir "pyvenv.cfg"
    if (Test-Path -LiteralPath $pyvenv) {
        $homeLine = Get-Content -LiteralPath $pyvenv -Encoding UTF8 | Where-Object { $_ -like "home = *" } | Select-Object -First 1
        if ($homeLine) {
            $home = $homeLine.Split("=", 2)[1].Trim()
            if (Test-Path -LiteralPath (Join-Path $home "python.exe")) { return $home }
        }
    }
    $uvPythonRoot = Join-Path $env:APPDATA "uv\python"
    if (Test-Path -LiteralPath $uvPythonRoot) {
        $found = Get-ChildItem -LiteralPath $uvPythonRoot -Directory -ErrorAction SilentlyContinue |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "python.exe") } |
            Sort-Object Name -Descending |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return ""
}

function Ensure-KimiModuleRuntime {
    $modulePython = Join-Path $RootDir "runtime\kimi\python313\python.exe"
    $modulePkg = Join-Path $RootDir "runtime\kimi\kimi-cli-tool\Lib\site-packages\kimi_cli"
    if ((Test-Path -LiteralPath $modulePython) -and (Test-Path -LiteralPath $modulePkg)) {
        Write-Host "Bundled Kimi module runtime already exists." -ForegroundColor Green
        return
    }

    $toolDir = Find-UvToolDir
    if (-not $toolDir) {
        $uv = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uv) {
            Write-Host "uv was not found. Installing uv for this user..." -ForegroundColor Yellow
            Invoke-Expression ((Invoke-WebRequest -UseBasicParsing -Uri "https://astral.sh/uv/install.ps1").Content)
            $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
        }
        Write-Host "Installing Kimi CLI with uv..." -ForegroundColor Yellow
        & uv tool install kimi-cli --force
        if ($LASTEXITCODE -ne 0) { throw "uv tool install kimi-cli failed." }
        $toolDir = Find-UvToolDir
    }
    if (-not $toolDir) { throw "Kimi CLI tool directory was not found after install." }
    $pythonDir = Find-UvPythonDir $toolDir
    if (-not $pythonDir) { throw "Kimi CLI Python runtime was not found." }

    New-Item -ItemType Directory -Force -Path (Join-Path $RootDir "runtime\kimi") | Out-Null
    Copy-TreeFresh $toolDir (Join-Path $RootDir "runtime\kimi\kimi-cli-tool")
    Copy-TreeFresh $pythonDir (Join-Path $RootDir "runtime\kimi\python313")
    Write-Host "Bundled full Kimi CLI module runtime into runtime\kimi." -ForegroundColor Green
}

function Patch-Provider {
    $provider = Join-Path $RootDir "src\backend\providers\kimi_cli.py"
    if (-not (Test-Path -LiteralPath $provider)) { throw "Provider file not found: $provider" }
    $text = Get-Content -Raw -LiteralPath $provider -Encoding UTF8
    if ($text -notmatch "module_python") {
        $text = $text -replace '(\s+self\.embedding_dim = retrieval\.get\("dense_embedding_dim", 128\)\r?\n)', "`$1        self.module_python = (ROOT / `"runtime`" / `"kimi`" / `"python313`" / `"python.exe`").resolve()`r`n        self.module_site_packages = (ROOT / `"runtime`" / `"kimi`" / `"kimi-cli-tool`" / `"Lib`" / `"site-packages`").resolve()`r`n        self.module_scripts = (ROOT / `"runtime`" / `"kimi`" / `"kimi-cli-tool`" / `"Scripts`").resolve()`r`n"
        $text = $text -replace '(\s+def check_connection\(self\) -> bool:\r?\n)', "`$1        if self._module_runner_available():`r`n            return True`r`n"
        $old = @'
        env["PATH"] = os.pathsep.join(item for item in (kimi_bin, bundled_rg, env.get("PATH", "")) if item)
        command = [
            self.executable,
'@
        $new = @'
        python_bin = str(self.module_python.parent) if self.module_python.exists() else ""
        module_scripts = str(self.module_scripts) if self.module_scripts.exists() else ""
        pywin32_system32 = str(self.module_site_packages / "pywin32_system32")
        env["PATH"] = os.pathsep.join(
            item for item in (python_bin, pywin32_system32, module_scripts, kimi_bin, bundled_rg, env.get("PATH", "")) if item
        )
        if self._module_runner_available():
            env["PYTHONPATH"] = os.pathsep.join(
                item
                for item in (
                    str(self.module_site_packages),
                    str(self.module_site_packages / "win32"),
                    str(self.module_site_packages / "win32" / "lib"),
                    str(self.module_site_packages / "pythonwin"),
                    env.get("PYTHONPATH", ""),
                )
                if item
            )
            command = [
                str(self.module_python),
                "-m",
                "kimi_cli",
            ]
        else:
            command = [
                self.executable,
'@
        $text = $text.Replace($old, $new)
        $text = $text -replace '(\r?\n    def _resolve_executable\(self, value: str\) -> str:)', "`r`n    def _module_runner_available(self) -> bool:`r`n        return self.module_python.exists() and (self.module_site_packages / `"kimi_cli`").exists()`r`n`$1"
        Set-Content -LiteralPath $provider -Value $text -Encoding UTF8
        Write-Host "Patched kimi_cli.py to use bundled python -m kimi_cli." -ForegroundColor Green
    } else {
        Write-Host "kimi_cli.py already contains the module-runner fix." -ForegroundColor Green
    }
}

function Stop-AgriKBService {
    $values = Read-DotEnv (Join-Path $RootDir ".env")
    $port = 8010
    if ($values["KNOWLEDGE_RAG_PORT"]) { [int]::TryParse($values["KNOWLEDGE_RAG_PORT"], [ref]$port) | Out-Null }
    $listeners = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction Stop
            if ([string]$proc.CommandLine -match "uvicorn" -and [string]$proc.CommandLine -match "src\.backend\.app:app") {
                Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
                Write-Host "Stopped old AgriKB service on port $port." -ForegroundColor Yellow
            }
        } catch {}
    }
}

function Test-KimiModuleRuntime {
    $py = Join-Path $RootDir "runtime\kimi\python313\python.exe"
    $sp = Join-Path $RootDir "runtime\kimi\kimi-cli-tool\Lib\site-packages"
    $oldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = @($sp, (Join-Path $sp "win32"), (Join-Path $sp "win32\lib"), (Join-Path $sp "pythonwin"), $oldPythonPath) -join ";"
    $env:PATH = "$(Join-Path $RootDir "runtime\kimi\python313");$(Join-Path $sp "pywin32_system32");$(Join-Path $RootDir "runtime\kimi\kimi-cli-tool\Scripts");$env:PATH"
    $version = & $py -m kimi_cli --version 2>&1 | Select-Object -First 1
    $env:PYTHONPATH = $oldPythonPath
    Write-Host "Kimi module runtime: $version" -ForegroundColor Green
}

Write-Host ""
Write-Host "AgriKB Kimi trampoline repair" -ForegroundColor Cyan
Write-Host "Project root: $RootDir" -ForegroundColor DarkGray

Ensure-EnvConfig
Ensure-KimiModuleRuntime
Patch-Provider
Stop-AgriKBService
Test-KimiModuleRuntime

$python = Join-Path $RootDir "runtime\python311\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = Join-Path $RootDir ".venv\Scripts\python.exe" }
if (Test-Path -LiteralPath $python) {
    & $python -m py_compile (Join-Path $RootDir "src\backend\providers\kimi_cli.py")
    if ($LASTEXITCODE -ne 0) { throw "Provider py_compile failed." }
}

if (-not $SkipRealModelTest -and (Test-Path -LiteralPath (Join-Path $RootDir "NewPC-Preflight.ps1"))) {
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RootDir "NewPC-Preflight.ps1") -RealModel -Port 8098
}

Write-Host ""
Write-Host "Repair complete. Now run START_AgriKB_TRUSTED_PC.bat." -ForegroundColor Green
