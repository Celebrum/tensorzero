param(
    [switch]$EnableExceptions,
    [string]$CargoPath
)

# Check for admin privileges
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script requires administrator privileges. Please run as administrator."
    exit 1
}

function Set-DefenderException {
    param([string]$Path)
    try {
        Add-MpPreference -ExclusionPath $Path -Force
        Write-Host "Added Defender exception for: $Path" -ForegroundColor Green
        return $true
    } catch {
        Write-Error "Failed to set Defender exception: $_"
        return $false
    }
}

# Configure core paths for TensorZero
$corePaths = @(
    "$CargoPath\cargo.exe",
    "$env:USERPROFILE\Miniconda3",
    "C:\Program Files\TensorZero"
)

# Add exceptions for core components
foreach ($path in $corePaths) {
    if (!(Set-DefenderException $path)) {
        Write-Error "Failed to set exception for: $path"
        exit 1
    }
}

# Configure firewall for Gateway and Flywheel
New-NetFirewallRule -DisplayName "TensorZero Gateway" `
                   -Direction Inbound `
                   -Action Allow `
                   -Protocol TCP `
                   -LocalPort 3000

New-NetFirewallRule -DisplayName "TensorZero Flywheel" `
                   -Direction Inbound `
                   -Action Allow `
                   -Protocol TCP `
                   -LocalPort 3001

Write-Host "Core security configuration completed" -ForegroundColor Green