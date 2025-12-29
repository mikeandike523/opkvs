[CmdletBinding()]
param(
    # Capture and pass through all arguments verbatim to opkvs.py
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsFromUser
)

$ErrorActionPreference = 'Stop'

# ----------------------------------------
# Determine script_dir (dir of opkvs.ps1)
# ----------------------------------------
$scriptDir = Split-Path -Parent $PSCommandPath

# ----------------------------------------
# Locate and activate venv: script_dir/pyenv/Scripts/activate.ps1
# ----------------------------------------
$venvActivate = Join-Path $scriptDir "pyenv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Error "Virtual environment not found. Expected: $venvActivate"
    Write-Error "Make sure install.ps1 has been run successfully."
    exit 1
}

# Dot-source the activate script to modify PATH/ENV in this process.
# NOTE: We are NOT changing the current directory, just the environment.
. $venvActivate

# ----------------------------------------
# Ensure python is available (from the venv)
# ----------------------------------------
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "After activating the virtual environment, 'python' is not available."
    exit 1
}

# ----------------------------------------
# Run python opkvs.py, keeping the user's cwd intact
# ----------------------------------------
$opkvsPy = Join-Path $scriptDir "opkvs.py"
if (-not (Test-Path $opkvsPy)) {
    Write-Error "Could not find opkvs.py at: $opkvsPy"
    exit 1
}

# IMPORTANT:
# - We do NOT change directory.
# - We pass the full path to opkvs.py.
#   Python's working directory remains whatever the user was in when they ran 'opkvs'.
& $pythonCmd.Source $opkvsPy @ArgsFromUser
$exitCode = $LASTEXITCODE

# No explicit 'deactivate' needed: this script runs in its own PowerShell process.
exit $exitCode
