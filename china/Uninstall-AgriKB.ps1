param(
    [switch]$Force,
    [switch]$OnlyCurrent,
    [switch]$KeepZips,
    [switch]$DryRun,
    [string]$ProjectRootOverride = "",
    [switch]$Staged
)

$ErrorActionPreference = "Stop"

function Quote-Arg([string]$Value) {
    '"' + $Value.Replace('"', '\"') + '"'
}

$scriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Path }
$scriptRoot = Split-Path -Parent $scriptPath
$projectRoot = if ($ProjectRootOverride) {
    [System.IO.Path]::GetFullPath($ProjectRootOverride)
} else {
    [System.IO.Path]::GetFullPath($scriptRoot)
}

if (-not $Staged -and -not $DryRun) {
    $stageRoot = Join-Path $env:TEMP ("AgriKB-Uninstall-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
    $stageScript = Join-Path $stageRoot "Uninstall-AgriKB.ps1"
    Copy-Item -LiteralPath $scriptPath -Destination $stageScript -Force

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Quote-Arg $stageScript),
        "-ProjectRootOverride", (Quote-Arg $projectRoot),
        "-Staged"
    )
    if ($Force) { $args += "-Force" }
    if ($OnlyCurrent) { $args += "-OnlyCurrent" }
    if ($KeepZips) { $args += "-KeepZips" }
    if ($DryRun) { $args += "-DryRun" }

    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList ($args -join " ") -Wait -PassThru -NoNewWindow
    exit $proc.ExitCode
}

$desktop = [Environment]::GetFolderPath("Desktop")
$logDir = Join-Path $env:TEMP "AgriKB-Uninstall-Logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logPath = Join-Path $logDir ("uninstall-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

function Write-Log([string]$Message, [string]$Color = "Gray") {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $logPath -Encoding UTF8 -Value $line
    Write-Host $Message -ForegroundColor $Color
}

function Start-StagedCleanup {
    if (-not $Staged) { return }
    try {
        $stageToRemove = $scriptRoot
        $cleanup = "ping 127.0.0.1 -n 3 > nul & rmdir /s /q " + (Quote-Arg $stageToRemove)
        Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cleanup) -WindowStyle Hidden | Out-Null
    } catch {}
}

function Test-AgriKbRoot([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $markers = @(
        "README_AGRIKB.md",
        "package_manifest.json",
        "web\index.html",
        "src\backend\app.py",
        "Start-Mobile-Test.ps1"
    )
    $hits = 0
    foreach ($marker in $markers) {
        if (Test-Path -LiteralPath (Join-Path $Path $marker)) { $hits += 1 }
    }
    return $hits -ge 2
}

function Test-SafeDeletePath([string]$Path) {
    if (-not $Path) { return $false }
    $full = [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
    $desktopFull = [System.IO.Path]::GetFullPath($desktop).TrimEnd("\")
    if ($full -match "^[A-Za-z]:$") { return $false }
    if ($full -match "^[A-Za-z]:\\$") { return $false }
    if ($full.Equals($desktopFull, [StringComparison]::OrdinalIgnoreCase)) { return $false }
    if (-not $full.StartsWith($desktopFull + "\", [StringComparison]::OrdinalIgnoreCase)) { return $false }
    return $true
}

function Add-Target([hashtable]$Map, [string]$Path, [string]$Kind) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $full = [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
    if (-not (Test-SafeDeletePath $full)) {
        Write-Log "Skip unsafe path: $full" "Yellow"
        return
    }
    if (-not $Map.ContainsKey($full)) {
        $Map[$full] = [pscustomobject]@{
            Path = $full
            Kind = $Kind
        }
    }
}

function Get-ProcessMatchesTarget([object]$Process, [string[]]$TargetDirs) {
    $cmd = [string]$Process.CommandLine
    $exe = [string]$Process.ExecutablePath
    foreach ($dir in $TargetDirs) {
        if ($cmd.IndexOf($dir, [StringComparison]::OrdinalIgnoreCase) -ge 0) { return $true }
        if ($exe.IndexOf($dir, [StringComparison]::OrdinalIgnoreCase) -ge 0) { return $true }
    }
    return $false
}

Write-Log "AgriKB uninstall started. Log: $logPath" "Cyan"
Write-Log "Project root: $projectRoot" "Cyan"

if (-not (Test-AgriKbRoot $projectRoot)) {
    Write-Log "This folder does not look like an AgriKB project. Stop to avoid accidental deletion." "Red"
    Start-StagedCleanup
    exit 2
}

$targets = @{}
Add-Target $targets $projectRoot "current project"

if (-not $OnlyCurrent) {
    Get-ChildItem -LiteralPath $desktop -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "AgriKB*" -or
            $_.Name -like "*AgriKB*" -or
            $_.Name -like "*AgriKB*"
        } |
        ForEach-Object {
            if ($_.PSIsContainer) {
                if ((Test-AgriKbRoot $_.FullName) -or $_.Name -like "AgriKB_*" -or $_.Name -like "AgriKB-*") {
                    Add-Target $targets $_.FullName "AgriKB desktop folder"
                }
            } elseif (-not $KeepZips -and $_.Extension -eq ".zip" -and ($_.Name -like "AgriKB*.zip" -or $_.Name -like "*AgriKB*.zip")) {
                Add-Target $targets $_.FullName "AgriKB zip archive"
            }
        }
}

$orderedTargets = $targets.Values | Sort-Object -Property @{ Expression = { $_.Path.Length }; Descending = $true }
$targetDirs = @($orderedTargets | Where-Object { Test-Path -LiteralPath $_.Path -PathType Container } | ForEach-Object { $_.Path })

Write-Log ""
Write-Log "The following AgriKB assets will be removed:" "Yellow"
foreach ($target in $orderedTargets) {
    Write-Log ("  - [{0}] {1}" -f $target.Kind, $target.Path) "Yellow"
}
Write-Log ""
Write-Log "Will not remove: system Python, global Kimi/Codex tools, WeChat files, E-drive source files, or non-AgriKB personal files." "Cyan"

if ($DryRun) {
    Write-Log "DryRun mode: no files will be removed." "Green"
    Start-StagedCleanup
    exit 0
}

if (-not $Force) {
    $answer = Read-Host "Type UNINSTALL to confirm, or press Enter to cancel"
    if ($answer -ne "UNINSTALL") {
        Write-Log "Uninstall cancelled by user." "Yellow"
        Start-StagedCleanup
        exit 0
    }
}

Write-Log "Stopping AgriKB background processes." "Cyan"
$protectedPids = @($PID)
try {
    $self = Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
    if ($self.ParentProcessId) { $protectedPids += [int]$self.ParentProcessId }
} catch {}

$processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ProcessId -notin $protectedPids -and
        (Get-ProcessMatchesTarget $_ $targetDirs)
    }

foreach ($proc in $processes) {
    try {
        Write-Log ("Stop process PID={0} Name={1}" -f $proc.ProcessId, $proc.Name) "Yellow"
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
    } catch {
        Write-Log ("Failed to stop process PID={0}: {1}" -f $proc.ProcessId, $_.Exception.Message) "Yellow"
    }
}

$ports = @(8010)
try {
    $envPath = Join-Path $projectRoot ".env"
    if (Test-Path -LiteralPath $envPath) {
        Get-Content -LiteralPath $envPath -Encoding UTF8 | ForEach-Object {
            if ($_ -match "^\s*KNOWLEDGE_RAG_PORT\s*=\s*(\d+)") {
                $ports += [int]$Matches[1]
            }
        }
    }
} catch {}
$ports = $ports | Sort-Object -Unique

foreach ($conn in (Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in $ports })) {
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessId -notin $protectedPids -and (Get-ProcessMatchesTarget $proc $targetDirs)) {
            Write-Log ("Stop AgriKB listener on port {0}, PID={1}" -f $conn.LocalPort, $proc.ProcessId) "Yellow"
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        }
    } catch {
        Write-Log ("Port cleanup skipped or failed: {0}" -f $_.Exception.Message) "Yellow"
    }
}

Write-Log "Removing desktop shortcuts and optional firewall rules." "Cyan"
try {
    $shell = New-Object -ComObject WScript.Shell
    Get-ChildItem -LiteralPath $desktop -Filter "*.lnk" -Force -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $shortcut = $shell.CreateShortcut($_.FullName)
            $targetPath = [string]$shortcut.TargetPath
            foreach ($dir in $targetDirs) {
                if ($targetPath.IndexOf($dir, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    Write-Log "Remove shortcut: $($_.FullName)" "Yellow"
                    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
                    break
                }
            }
        } catch {}
    }
} catch {
    Write-Log "Shortcut cleanup skipped: $($_.Exception.Message)" "Yellow"
}

try {
    Get-NetFirewallRule -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "*AgriKB*" -or $_.DisplayName -like "*AeroKB*" } |
        ForEach-Object {
            Write-Log "Remove firewall rule: $($_.DisplayName)" "Yellow"
            Remove-NetFirewallRule -Name $_.Name -ErrorAction Stop
        }
} catch {
    Write-Log "Firewall cleanup skipped or permission denied: $($_.Exception.Message)" "Yellow"
}

Write-Log "Removing project files." "Cyan"
Set-Location $env:TEMP
foreach ($target in $orderedTargets) {
    if (-not (Test-Path -LiteralPath $target.Path)) { continue }
    try {
        Write-Log ("Remove [{0}] {1}" -f $target.Kind, $target.Path) "Yellow"
        Remove-Item -LiteralPath $target.Path -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Log ("Remove failed: {0}; reason: {1}" -f $target.Path, $_.Exception.Message) "Red"
    }
}

Write-Log "AgriKB uninstall completed. Log saved at: $logPath" "Green"

Start-StagedCleanup

exit 0
