param(
    [Parameter(Position = 0)]
    [ValidateSet("project", "install")]
    [string]$Mode = "install"
)

Write-Host 'Running install.ps1'
$ErrorActionPreference = 'Stop'

# ---------------------------
# Helper: get script directory
# ---------------------------
$scriptDir = Split-Path -Parent $PSCommandPath

# ---------------------------
# Elevate to administrator
# ---------------------------
$windowsIdentity  = [Security.Principal.WindowsIdentity]::GetCurrent()
$windowsPrincipal = New-Object Security.Principal.WindowsPrincipal($windowsIdentity)
$isAdmin          = $windowsPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Re-launching as administrator..."
    $argList = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-Mode", $Mode
    )

    Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs -WorkingDirectory $scriptDir
    exit
}

Write-Host "Running elevated as administrator."

# ---------------------------
# Decide install directory
# ---------------------------
if ($Mode -eq "project") {
    Write-Host "Mode: project (use files in script directory, no copying)."
    $installDir = $scriptDir
} else {
    Write-Host "Mode: install (copy files to user LOCALAPPDATA\opkvs)."
    $installDir = Join-Path $env:LOCALAPPDATA "opkvs"

    if (-not (Test-Path $installDir)) {
        Write-Host "Creating install directory: $installDir"
        New-Item -ItemType Directory -Path $installDir | Out-Null
    } else {
        Write-Host "Install directory already exists: $installDir"
    }

    if ($scriptDir -ne $installDir) {
        Write-Host "Copying files from $scriptDir to $installDir (excluding virtual env 'pyenv' if present)..."
        Copy-Item -Path (Join-Path $scriptDir '*') -Destination $installDir -Recurse -Force -Exclude 'pyenv'
    } else {
        Write-Host "Script is already in install directory; skipping copy."
    }
}

# Work from install_dir from here on
Set-Location $installDir
Write-Host "Current directory set to install_dir: $installDir"

# ---------------------------
# Helper: confirm usable python
# ---------------------------
function Get-ConfirmedPython {
    $cmd = Get-Command python -ErrorAction SilentlyContinue

    if (-not $cmd) {
        Write-Error @"
The 'python' command was not found on PATH.

Please install Python (e.g. from python.org) and make sure 'python'
is available in your PATH, then re-run this script.
"@
        return $null
    }

    $pythonPath = $cmd.Source
    Write-Host "Found 'python' command:"
    Write-Host "  Name: $($cmd.Name)"
    Write-Host "  Path: $pythonPath"

    # Sanity check: try a tiny command
    try {
        $output = & $pythonPath -c "import sys; print(sys.version.split()[0])"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Python executable '$pythonPath' did not run successfully (exit code $LASTEXITCODE)."
            return $null
        }
        Write-Host "Python appears to work. Detected version: $output"
    }
    catch {
        Write-Error "Failed to execute Python at '$pythonPath': $($_.Exception.Message)"
        return $null
    }

    $answer = Read-Host "Use this 'python' for installation? (Y/n)"
    if ($answer -match '^[Nn]') {
        Write-Error "User declined to use this Python interpreter. Aborting."
        return $null
    }

    return $pythonPath
}

# ---------------------------
# Check / confirm Python
# ---------------------------
$pythonPath = Get-ConfirmedPython
if (-not $pythonPath) {
    exit 1
}

# ---------------------------
# Create / reuse venv: pyenv
# ---------------------------
$venvDir = Join-Path $installDir "pyenv"

if (-not (Test-Path $venvDir)) {
    Write-Host "Creating virtual environment at: $venvDir"
    try {
        & $pythonPath -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "python -m venv pyenv failed with exit code $LASTEXITCODE."
            exit 1
        }
    }
    catch {
        Write-Error "Failed to create virtual environment: $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Host "Virtual environment already exists at: $venvDir (reusing)."
}

# ---------------------------
# Activate venv
# ---------------------------
$activateScript = Join-Path (Join-Path $venvDir "Scripts") "Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Activation script not found at $activateScript. The virtual environment may be corrupted."
    exit 1
}

Write-Host "Activating virtual environment..."
. $activateScript

# ---------------------------
# Install Python requirements
# ---------------------------
$requirements = Join-Path $installDir "requirements.txt"
if (Test-Path $requirements) {
    Write-Host "Installing dependencies from requirements.txt..."
    try {
        python -m pip install -r $requirements
        if ($LASTEXITCODE -ne 0) {
            Write-Error "pip install -r requirements.txt failed with exit code $LASTEXITCODE."
            exit 1
        }
    }
    catch {
        Write-Error "pip failed: $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Warning "requirements.txt not found in $installDir; skipping dependency installation."
}

# ---------------------------
# Deactivate venv (optional)
# ---------------------------
if (Get-Command deactivate -ErrorAction SilentlyContinue) {
    Write-Host "Deactivating virtual environment..."
    deactivate
} else {
    Write-Host "No 'deactivate' command found; skipping deactivation."
}

# ---------------------------
# Check Windows path-length limit (Win32 long paths)
# ---------------------------
$longPathsKey = "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem"
$longPathsEnabled = $null

try {
    $props = Get-ItemProperty -Path $longPathsKey -Name LongPathsEnabled -ErrorAction SilentlyContinue
    if ($props -and $props.LongPathsEnabled -eq 1) {
        $longPathsEnabled = $true
    } else {
        $longPathsEnabled = $false
    }
}
catch {
    Write-Warning "Could not read LongPathsEnabled registry value: $($_.Exception.Message)"
    $longPathsEnabled = $null
}

if ($longPathsEnabled -eq $false) {
    Write-Host ""
    Write-Host "The Windows path length limit (MAX_PATH) appears to be ENABLED."
    Write-Host "This can cause issues when installing Python packages with deep dependency trees."
    $answer = Read-Host "Do you want to DISABLE the path length limit now by enabling Win32 long paths? (y/N)"

    if ($answer -match '^[Yy]') {
        try {
            Set-ItemProperty -Path $longPathsKey -Name LongPathsEnabled -Type DWord -Value 1
            Write-Host "Win32 long paths have been enabled (LongPathsEnabled = 1). A reboot may be required for all apps to see this."
        }
        catch {
            Write-Warning "Failed to modify LongPathsEnabled: $($_.Exception.Message)"
        }
    } else {
        Write-Host "Leaving path length limit as-is."
    }
} elseif ($longPathsEnabled -eq $true) {
    Write-Host "Win32 long paths are already enabled (path length limit effectively disabled)."
} else {
    Write-Warning "Could not conclusively determine path-length-limit status."
}

# ---------------------------
# Helper: add install_dir to PATH (user and system)
# ---------------------------
function Add-ToPath {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("Machine", "User")]
        [string]$Scope,

        [Parameter(Mandatory = $true)]
        [string]$Dir
    )

    $dirNorm = $Dir.TrimEnd('\')

    $current = [Environment]::GetEnvironmentVariable("Path", $Scope)
    if ([string]::IsNullOrWhiteSpace($current)) {
        $paths = @()
    } else {
        $paths = $current.Split(';') | Where-Object { $_ -ne "" }
    }

    if ($paths | Where-Object { $_.TrimEnd('\') -ieq $dirNorm }) {
        Write-Host "PATH ($Scope) already contains: $dirNorm"
        return
    }

    $newPaths = @($paths + $dirNorm)
    $newPathString = ($newPaths -join ';')

    try {
        [Environment]::SetEnvironmentVariable("Path", $newPathString, $Scope)
        Write-Host "Added to $Scope PATH: $dirNorm"
    }
    catch {
        Write-Warning "Failed to update PATH for ${Scope}: $($_.Exception.Message)"
        Write-Warning "New PATH length would have been: $($newPathString.Length) characters."
        if ($newPathString.Length -ge 32767) {
            Write-Warning "This likely failed because the PATH is too long (exceeds Windows limit). Consider removing unused entries."
        }
    }
}

# ---------------------------
# Add install_dir to system and user PATH
# ---------------------------
Write-Host "Ensuring install_dir is on PATH for both user and system..."
Add-ToPath -Scope "User"    -Dir $installDir
Add-ToPath -Scope "Machine" -Dir $installDir

Write-Host ""
Write-Host "Installation steps completed."
Write-Host "New PATH entries will be picked up by new terminals / processes."
