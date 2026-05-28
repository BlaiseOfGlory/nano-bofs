param(
    [string]$Tag,
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if ([string]::IsNullOrWhiteSpace($env:UV_CACHE_DIR)) {
    $env:UV_CACHE_DIR = Join-Path $repoRoot ".local\uv-cache"
}

function Step($Message) {
    Write-Host "==> $Message"
}

function Invoke-Native($Command, [string[]]$Arguments) {
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

function Invoke-NativeOutput($Command, [string[]]$Arguments) {
    $output = & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
    return $output
}

$UvPython = @("run", "--no-project", "--python", "3.11", "python")

Step "Reading project version"
$version = Invoke-NativeOutput "uv" ($UvPython + @("-c", "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"))
$expectedTag = "v$version"

if ([string]::IsNullOrWhiteSpace($Tag)) {
    $Tag = $expectedTag
}

Step "Checking release metadata contracts"
Invoke-Native "uv" ($UvPython + @("scripts\release_contract_check.py", "--tag", $Tag))

Step "Checking working tree"
$status = Invoke-NativeOutput "git" @("status", "--porcelain")
if (-not [string]::IsNullOrWhiteSpace($status)) {
    Write-Host $status
    throw "Working tree is not clean. Commit or stash changes before tagging a release."
}

Step "Checking current commit is on master"
Invoke-Native "git" @("fetch", "origin", "master:refs/remotes/origin/master", "--depth=1")
Invoke-Native "git" @("merge-base", "--is-ancestor", "HEAD", "origin/master")

Step "Checking tag does not already exist"
$existingLocalTag = Invoke-NativeOutput "git" @("tag", "--list", $Tag)
if (-not [string]::IsNullOrWhiteSpace($existingLocalTag)) {
    throw "Local tag '$Tag' already exists."
}

$existingRemoteTag = Invoke-NativeOutput "git" @("ls-remote", "--tags", "origin", "refs/tags/$Tag")
if (-not [string]::IsNullOrWhiteSpace($existingRemoteTag)) {
    throw "Remote tag '$Tag' already exists on origin."
}

Step "Syncing root dependencies from lockfile"
Invoke-Native "uv" @("sync", "--locked", "--python", "3.11")

Step "Clearing nano-bofs environment overrides"
Remove-Item Env:NANO_BOFS_CONFIG -ErrorAction SilentlyContinue
Remove-Item Env:NANO_BOFS_DEFAULT_BACKEND -ErrorAction SilentlyContinue
Remove-Item Env:NANO_BOFS_DOCKER_IMAGE -ErrorAction SilentlyContinue
Remove-Item Env:NANO_BOFS_STATE_DIR -ErrorAction SilentlyContinue

Step "Running unit tests"
Invoke-Native "uv" @("run", "python", "-m", "unittest")

Step "Building Python package"
Invoke-Native "uv" @("build", "--python", "3.11")

Step "Smoke testing built wheel"
$wheelEnv = Join-Path $repoRoot ".local\wheel-smoke"
Remove-Item -Recurse -Force $wheelEnv -ErrorAction SilentlyContinue
Invoke-Native "uv" ($UvPython + @("-m", "venv", $wheelEnv))
$wheelPython = Join-Path $wheelEnv "Scripts\python.exe"
$wheelCli = Join-Path $wheelEnv "Scripts\nano-bofs.exe"
Invoke-Native $wheelPython @("-m", "pip", "install", "--no-index", "--find-links", "dist", "nano-bofs")
Invoke-Native $wheelCli @("list")
Invoke-Native $wheelPython @("-c", "import nano_bofs.template_catalog as c; names=set(c.discover_templates()); assert 'probe' in names and 'ldapsearch' in names; print(f'loaded {len(names)} templates from installed wheel')")

Step "Syncing Mythic runtime dependencies from lockfile"
Push-Location "Payload_Type\nano_bofs"
try {
    Invoke-Native "uv" @("sync", "--locked", "--python", "3.11")

    Step "Smoke testing Mythic runtime imports"
    Invoke-Native "uv" @("run", "python", "-c", "import mythic_container, nano_bofs.template_catalog as c; names=set(c.discover_templates()); assert 'mythicSmoke' in names and 'ldapsearch' in names; print(f'loaded {len(names)} Mythic runtime templates')")
}
finally {
    Pop-Location
}

if (-not $SkipDocker) {
    Step "Building Docker image"
    Invoke-Native "docker" @("build", "--pull=false", "--tag", "nano-bofs-release-check:$version", "--file", "Payload_Type/nano_bofs/Dockerfile", ".")

    Step "Smoke testing Docker image imports"
    Invoke-Native "docker" @("run", "--rm", "--entrypoint", "python", "nano-bofs-release-check:$version", "-c", "import mythic_container, nano_bofs.template_catalog as c; names=set(c.discover_templates()); assert 'mythicSmoke' in names and 'ldapsearch' in names; print(f'loaded {len(names)} Docker templates')")
}

Step "Release preflight passed for $Tag"
Write-Host "Next:"
Write-Host "  git tag -a $Tag -m `"$Tag`""
Write-Host "  git push origin $Tag"
