#Requires -Version 5.1
<#
.SYNOPSIS
  Create a git tag and GitHub Release for RepoPulse.
.DESCRIPTION
  1) Validates clean working tree
  2) Creates annotated tag vX.Y.Z (or uses provided)
  3) Pushes tag
  4) Creates a GitHub Release via GitHub API (requires GITHUB_TOKEN)

EXAMPLE
  .\scripts\release.ps1 -Version 0.3.1 -Title "RepoPulse v0.3.1" -NotesFile .\docs\release-notes-v0.3.1.md
#>

param(
  [Parameter(Mandatory=$true)]
  [string]$Version,                 # e.g. 0.3.1 (script will prefix "v")

  [string]$Title = "",              # default: "v<Version>"

  [string]$NotesFile = "",          # optional path to markdown file for body

  [switch]$Draft,                   # create as draft release
  [switch]$PreRelease               # mark as prerelease
)

$ErrorActionPreference = "Stop"

function Die($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# --- Preconditions ---
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { Die "Not inside a git repo." }

$status = git status --porcelain
if ($status) { Die "Working tree not clean. Commit/stash first." }

$tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
if (-not $Title) { $Title = $tag }

# Ensure on main (optional)
# git checkout main
# git pull

# --- Create annotated tag if missing ---
git show-ref --tags --quiet --verify "refs/tags/$tag"
if ($LASTEXITCODE -eq 0) {
  Write-Host "Tag already exists: $tag" -ForegroundColor Yellow
} else {
  git tag -a $tag -m "$Title"
  if ($LASTEXITCODE -ne 0) { Die "Failed to create tag." }
  Write-Host "Created tag: $tag" -ForegroundColor Green
}

# --- Push tag ---
git push origin $tag
if ($LASTEXITCODE -ne 0) { Die "Failed to push tag to origin." }
Write-Host "Pushed tag: $tag" -ForegroundColor Green

# --- Create GitHub Release ---
$token = $env:GITHUB_TOKEN
if (-not $token) { Die "GITHUB_TOKEN not set in environment." }

# Determine owner/repo from origin URL
$origin = (git remote get-url origin).Trim()
# Supports https://github.com/owner/repo.git and git@github.com:owner/repo.git
$ownerRepo = $null
if ($origin -match "github\.com[:/](?<owner>[^/]+)/(?<repo>[^/.]+)") {
  $owner = $Matches["owner"]
  $repo  = $Matches["repo"]
  $ownerRepo = "$owner/$repo"
} else {
  Die "Could not parse GitHub owner/repo from origin: $origin"
}

$notes = ""
if ($NotesFile) {
  if (-not (Test-Path $NotesFile)) { Die "NotesFile not found: $NotesFile" }
  $notes = Get-Content -Raw -Path $NotesFile
}

$uri = "https://api.github.com/repos/$ownerRepo/releases"

$payload = @{
  tag_name   = $tag
  name       = $Title
  body       = $notes
  draft      = [bool]$Draft
  prerelease = [bool]$PreRelease
} | ConvertTo-Json -Depth 6

$headers = @{
  Authorization = "Bearer $token"
  "X-GitHub-Api-Version" = "2022-11-28"
  Accept = "application/vnd.github+json"
}

try {
  $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $payload
  Write-Host "Created GitHub Release: $($resp.html_url)" -ForegroundColor Green
} catch {
  Write-Host "Failed to create GitHub Release. Response:" -ForegroundColor Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  throw
}