param(
    [Parameter(Position = 0)]
    [ValidateSet("project", "install")]
    [string]$Mode = "install"
)

Write-Host "Running uninstall.ps1"
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
# Decide install directory (same logic as install.ps1)
# ---------------------------
if ($Mode -eq "project") {
    Write-Host "Mode: project"
    Write-Host "Will ONLY remove this script directory from PATH (no file deletions)."
    $installDir = $scriptDir
} else {
    Write-Host "Mode: install"
    $installDir = Join-Path $env:LOCALAPPDATA "opkvs"
}

Write-Host "Assumed install_dir: $installDir"

# ---------------------------
# Helper: remove a directory from PATH
# ---------------------------
function Remove-FromPath {
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
        Write-Host "PATH ($Scope) is empty or not set; nothing to remove."
        return
    }

    $paths = $current.Split(';') | Where-Object { $_ -ne "" }

    $removed = $false
    $filtered = foreach ($p in $paths) {
        if ($p.TrimEnd('\') -ieq $dirNorm) {
            $removed = $true
            continue  # skip this entry (i.e. remove it)
        }
        $p
    }

    if (-not $removed) {
        Write-Host "PATH ($Scope) did not contain: $dirNorm"
        return
    }

    $newPathString = ($filtered -join ';')

    try {
        [Environment]::SetEnvironmentVariable("Path", $newPathString, $Scope)
        Write-Host "Removed all instances of '$dirNorm' from $Scope PATH."
    }
    catch {
        Write-Warning "Failed to update PATH for ${Scope}: $($_.Exception.Message)"
        Write-Warning "Resulting PATH length would have been: $($newPathString.Length) characters."
    }
}

# ---------------------------
# Remove install_dir from PATH (user + system)
# ---------------------------
Write-Host "Removing install_dir from PATH (User + Machine)..."
Remove-FromPath -Scope "User"    -Dir $installDir
Remove-FromPath -Scope "Machine" -Dir $installDir

# ---------------------------
# In 'install' mode, delete the appdata directory
# ---------------------------
if ($Mode -eq "install") {
    Write-Host ""
    Write-Host "Cleaning up installation directory under LOCALAPPDATA..."

    if (Test-Path $installDir) {
        $installNorm = $installDir.TrimEnd('\')
        $scriptNorm  = $scriptDir.TrimEnd('\')

        if ($installNorm -ieq $scriptNorm) {
            Write-Warning "Uninstall script is running from inside the install directory:"
            Write-Warning "  $installDir"
            Write-Warning "Skipping deletion of the directory to avoid issues."
            Write-Warning "Please manually delete this folder if you want to fully remove it."
        } else {
            try {
                Write-Host "Removing directory: $installDir"
                Remove-Item -Path $installDir -Recurse -Force
                Write-Host "Directory removed."
            }
            catch {
                Write-Warning "Failed to delete install directory '$installDir': $($_.Exception.Message)"
                Write-Warning "You may need to close applications using this directory and delete it manually."
            }
        }
    } else {
        Write-Host "No install directory found at: $installDir (nothing to delete)."
    }
} else {
    Write-Host ""
    Write-Host "Project mode: not deleting any files."
}

Write-Host ""
Write-Host "Uninstall steps completed."
Write-Host "PATH changes apply to new terminals / processes."
