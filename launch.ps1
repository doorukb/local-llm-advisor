$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/doorukb/Local-LLM-Advisor.git'
$DefaultBranch = 'main'
$PythonDownloadUrl = 'https://www.python.org/downloads/'

$WorkDir = $null

function Die {
    param([string]$Message)

    Write-Error "Error: $Message"
    exit 1
}

function Test-ExecutionPolicyAllowed {
    $policy = Get-ExecutionPolicy
    $isLocalScript = -not [string]::IsNullOrEmpty($PSScriptRoot)

    if ($policy -eq 'Restricted') {
        Die @"
PowerShell script execution is blocked (execution policy: Restricted).
Run the following command, then re-run this script:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
"@
    }

    if ($isLocalScript -and $policy -eq 'AllSigned') {
        Die @"
PowerShell script execution is blocked for unsigned local scripts (execution policy: AllSigned).
Run the following command, then re-run this script:
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
"@
    }
}

function Resolve-ScriptDir {
    if (-not [string]::IsNullOrEmpty($PSScriptRoot)) {
        return $PSScriptRoot
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Die 'git is required for remote bootstrap (irm | iex). Install git or clone the repository and run .\launch.ps1 instead.'
    }

    $script:WorkDir = Join-Path $env:TEMP ('llm-advisor-' + [Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $script:WorkDir -Force | Out-Null

    $branch = if ($env:LLM_ADVISOR_BRANCH) { $env:LLM_ADVISOR_BRANCH } else { $DefaultBranch }

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    git clone --depth 1 --branch $branch $RepoUrl $script:WorkDir
    $cloneExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorAction

    if ($cloneExitCode -ne 0) {
        Die "Failed to clone $RepoUrl (branch: $branch). Check your network connection and branch name."
    }

    return $script:WorkDir
}

function Find-Python {
    $candidates = @(
        @{ Label = 'py -3'; Exe = 'py'; ExtraArgs = @('-3') },
        @{ Label = 'python'; Exe = 'python'; ExtraArgs = @() },
        @{ Label = 'python3'; Exe = 'python3'; ExtraArgs = @() }
    )

    $versionGate = 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'
    $versionPrint = 'import sys; print(".".join(map(str, sys.version_info[:3])))'

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) {
            continue
        }

        $extraArgs = @($candidate.ExtraArgs)
        & $candidate.Exe @extraArgs -c $versionGate
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }

        $versionOutput = & $candidate.Exe @extraArgs -c $versionPrint 2>$null
        if ($versionOutput) {
            Die "Python 3.9 or later is required; found $($candidate.Label) version $versionOutput. Install Python from $PythonDownloadUrl"
        }
    }

    Die "Python 3.9 or later was not found on your system. Install Python from $PythonDownloadUrl"
}

try {
    Test-ExecutionPolicyAllowed

    $ScriptDir = Resolve-ScriptDir
    $RequirementsFile = Join-Path $ScriptDir 'requirements.txt'
    $AdvisorFile = Join-Path $ScriptDir 'advisor.py'

    if (-not (Test-Path -LiteralPath $RequirementsFile)) {
        Die "Missing requirements file: $RequirementsFile"
    }

    if (-not (Test-Path -LiteralPath $AdvisorFile)) {
        Die "Missing advisor entrypoint: $AdvisorFile"
    }

    $pythonCandidate = Find-Python

    $VenvDir = Join-Path $env:TEMP ('llm-advisor-venv-' + [Guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $VenvDir -Force | Out-Null

    $pythonExtraArgs = @($pythonCandidate.ExtraArgs)
    & $pythonCandidate.Exe @pythonExtraArgs -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Die 'Failed to create virtual environment.'
    }

    $VenvPython = Join-Path $VenvDir 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        Die "Failed to create virtual environment (missing $VenvPython)."
    }

    & $VenvPython -m pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        Die "Failed to install dependencies from $RequirementsFile"
    }

    $env:LLM_ADVISOR_VENV_DIR = $VenvDir

    & $VenvPython $AdvisorFile @args
    exit $LASTEXITCODE
}
finally {
    if ($WorkDir -and (Test-Path -LiteralPath $WorkDir)) {
        Remove-Item -LiteralPath $WorkDir -Recurse -Force
    }
}