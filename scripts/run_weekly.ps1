#Requires -Version 5.1
<#
.SYNOPSIS
    Run the full RepoPulse weekly pipeline (snapshot + reports).
.DESCRIPTION
    Computes last Monday (UTC), runs snapshots, generates weekly.csv and
    deepdive_queue.csv, then prints a summary.
#>

param(
    [string]$Since
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
# Ensure exports/ directory exists
# ---------------------------------------------------------------------------
$exportsDir = Join-Path $PSScriptRoot "..\exports"
if (-not (Test-Path $exportsDir)) {
    New-Item -ItemType Directory -Path $exportsDir | Out-Null
    Write-Host "Created: $exportsDir"
}

$weeklyOut   = Join-Path $exportsDir "weekly.csv"
$deepdiveOut = Join-Path $exportsDir "deepdive_queue.csv"

# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== [1/4] DB check ==="
repopulse db check

Write-Host ""
Write-Host "=== [2/4] Snapshots run ==="
repopulse snapshots run

Write-Host ""
Write-Host "=== [3/4] Weekly report ==="
repopulse report weekly --since $Since --out $weeklyOut

Write-Host ""
Write-Host "=== [4/4] Deep-dive queue ==="
repopulse deepdive queue --out $deepdiveOut

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Done ==="
Write-Host "  Week start : $Since"
Write-Host "  Weekly CSV : $weeklyOut"
Write-Host "  Deepdive   : $deepdiveOut"
