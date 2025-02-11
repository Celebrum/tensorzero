param(
    [switch]$EnableExceptions,
    [switch]$DisableRealTime,
    [string]$CargoPath
)

$DefenderPath = "HKLM:\SOFTWARE\Microsoft\Windows Defender"
$SecurityPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"

function Set-DefenderException {
    param([string]$Path)
    
    try {
        # Add path exclusion
        Add-MpPreference -ExclusionPath $Path -Force
        Write-Host "Added Defender exception for: $Path" -ForegroundColor Green
        
        # Verify exception was added
        $exclusions = Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
        if ($exclusions -contains $Path) {
            return $true
        }
        Write-Warning "Failed to verify exclusion for: $Path"
        return $false
    } catch {
        Write-Error "Failed to set Defender exception: $_"
        return $false
    }
}

function Set-SecurityPolicy {
    try {
        # Enable PowerShell scripts
        Set-ItemProperty -Path $SecurityPath -Name "EnableLUA" -Value 1
        Set-ItemProperty -Path $SecurityPath -Name "ConsentPromptBehaviorAdmin" -Value 0
        
        Write-Host "Security policy configured for TensorZero installation" -ForegroundColor Green
        return $true
    } catch {
        Write-Error "Failed to configure security policy: $_"
        return $false
    }
}

if ($EnableExceptions) {
    # Add required exceptions for TensorZero
    $paths = @(
        "$CargoPath\cargo-binstall.exe",
        "$CargoPath\cargo.exe",
        "$env:USERPROFILE\Miniconda3",
        "C:\Program Files\TensorZero"
    )
    
    foreach ($path in $paths) {
        if (!(Set-DefenderException $path)) {
            Write-Error "Failed to set exception for: $path"
            exit 1
        }
    }
}

if ($DisableRealTime) {
    try {
        Set-MpPreference -DisableRealtimeMonitoring $true
        Write-Host "Temporarily disabled real-time monitoring" -ForegroundColor Yellow
    } catch {
        Write-Warning "Failed to disable real-time monitoring: $_"
    }
}

# Configure security policy
if (!(Set-SecurityPolicy)) {
    Write-Error "Failed to configure security policy"
    exit 1
}

Write-Host "Security configuration completed successfully" -ForegroundColor Green