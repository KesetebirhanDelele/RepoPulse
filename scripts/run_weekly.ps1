#Requires -Version 5.1
<#
.SYNOPSIS
    Run the RepoPulse weekly pipeline (snapshots + optional reports + optional dashboard).
.DESCRIPTION
    Computes last Monday (UTC) unless -Since is provided. Always runs DB check + snapshots.
    If -Reports is set, generates weekly.csv and deepdive_queue.csv.
    If -Dashboard is set, starts the dashboard server (this blocks until Ctrl+C).
#>

param(
    [string]$Since,
    [switch]$Reports,
    [switch]$Dashboard,
    [string]$BindHost = "127.0.0.1",
    [int]$BindPort = 8000
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Determine week start
# ---------------------------------------------------------------------------
if ($Since) {
    Write-Host "Week start (override): $Since"
} else {
    $today = [System.DateTime]::UtcNow.Date
    $dayOfWeek = [int]$today.DayOfWeek   # 0=Sunday, 1=Monday ... 6=Saturday
    $daysBack = if ($dayOfWeek -eq 1) { 0 } elseif ($dayOfWeek -eq 0) { 6 } else { $dayOfWeek - 1 }
    $Since = $today.AddDays(-$daysBack).ToString("yyyy-MM-dd")
    Write-Host "Week start (last Monday UTC): $Since"
}

# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== [1/2] DB check ==="
repopulse db check

Write-Host ""
Write-Host "=== [2/2] Snapshots run ==="
repopulse snapshots run

# ---------------------------------------------------------------------------
# Optional reports
# ---------------------------------------------------------------------------
$exportsDir = $null
$weeklyOut = $null
$deepdiveOut = $null

if ($Reports) {
    # Ensure exports/ directory exists
    $exportsDir = Join-Path $PSScriptRoot "..\exports"
    if (-not (Test-Path $exportsDir)) {
        New-Item -ItemType Directory -Path $exportsDir | Out-Null
        Write-Host "Created: $exportsDir"
    }

    $weeklyOut   = Join-Path $exportsDir "weekly.csv"
    $deepdiveOut = Join-Path $exportsDir "deepdive_queue.csv"

    Write-Host ""
    Write-Host "=== Reports ==="
    Write-Host "Generating weekly.csv and deepdive_queue.csv..."

    repopulse report weekly --since $Since --out $weeklyOut
    repopulse deepdive queue --out $deepdiveOut
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Done ==="
Write-Host "  Week start : $Since"

if ($Reports) {
    Write-Host "  Weekly CSV : $weeklyOut"
    Write-Host "  Deepdive   : $deepdiveOut"
} else {
    Write-Host "  Reports    : skipped (run with -Reports)"
}

if ($Dashboard) {
    Write-Host ""
    Write-Host "=== Dashboard ==="
    Write-Host "Starting dashboard at http://$BindHost`:$BindPort/ (Ctrl+C to stop)"
    repopulse dashboard run --host $BindHost --port $BindPort
} else {
    Write-Host "  Dashboard  : skipped (run with -Dashboard)"
}