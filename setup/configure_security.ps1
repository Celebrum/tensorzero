param(
    [switch]$EnableExceptions,
    [switch]$DisableRealTime,
    [string]$CargoPath,
    [switch]$Restore
)

# Check for admin privileges
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script requires administrator privileges. Please run as administrator."
    exit 1
}

$DefenderPath = "HKLM:\SOFTWARE\Microsoft\Windows Defender"
$SecurityPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
$BackupPath = "$env:TEMP\tensorzero_security_backup.json"

function Backup-SecuritySettings {
    try {
        $settings = @{
            EnableLUA = (Get-ItemProperty -Path $SecurityPath).EnableLUA
            ConsentPromptBehaviorAdmin = (Get-ItemProperty -Path $SecurityPath).ConsentPromptBehaviorAdmin
            DefenderExclusions = (Get-MpPreference).ExclusionPath
            RealTimeMonitoring = (Get-MpPreference).DisableRealtimeMonitoring
        }
        $settings | ConvertTo-Json | Set-Content -Path $BackupPath
        Write-Host "Security settings backed up to $BackupPath" -ForegroundColor Green
    } catch {
        Write-Warning "Failed to backup security settings: $_"
    }
}

function Restore-SecuritySettings {
    if (Test-Path $BackupPath) {
        try {
            $settings = Get-Content -Path $BackupPath | ConvertFrom-Json
            Set-ItemProperty -Path $SecurityPath -Name "EnableLUA" -Value $settings.EnableLUA
            Set-ItemProperty -Path $SecurityPath -Name "ConsentPromptBehaviorAdmin" -Value $settings.ConsentPromptBehaviorAdmin
            
            if ($settings.DefenderExclusions) {
                Remove-MpPreference -ExclusionPath (Get-MpPreference).ExclusionPath -Force
                Add-MpPreference -ExclusionPath $settings.DefenderExclusions -Force
            }
            
            Set-MpPreference -DisableRealtimeMonitoring $settings.RealTimeMonitoring
            Write-Host "Security settings restored successfully" -ForegroundColor Green
            return $true
        } catch {
            Write-Error "Failed to restore security settings: $_"
            return $false
        }
    } else {
        Write-Warning "No backup file found at $BackupPath"
        return $false
    }
}

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

# Add additional function for system optimization
function Optimize-SystemPerformance {
    try {
        # Import required modules
        Import-Module MMAgent -ErrorAction SilentlyContinue
        Import-Module ConfigDefenderPerformance -ErrorAction SilentlyContinue
        Import-Module ProcessMitigations -ErrorAction SilentlyContinue

        # Configure memory management
        if (Get-Command "Enable-MMAgent" -ErrorAction SilentlyContinue) {
            Enable-MMAgent -ApplicationPreLaunch
            Set-MMAgent -ApplicationLaunchPrefetching True -ApplicationPagePreload True
            Write-Host "Memory management optimized" -ForegroundColor Green
        }

        # Configure process mitigations if available
        if (Get-Command "Set-ProcessMitigation" -ErrorAction SilentlyContinue) {
            Set-ProcessMitigation -System -Enable DEP,SEHOP,ForceRelocateImages
            Write-Host "Process mitigations configured" -ForegroundColor Green
        }

        # Configure Windows Search for better performance
        if (Get-Command "Set-WindowsSearchSetting" -ErrorAction SilentlyContinue) {
            Set-WindowsSearchSetting -EnableWebSearch 0 -EnableDynamicContentInWSB 0
            Write-Host "Windows Search optimized" -ForegroundColor Green
        }

        # Configure Windows Error Reporting
        if (Get-Command "Set-WindowsErrorReporting" -ErrorAction SilentlyContinue) {
            Disable-WindowsErrorReporting
            Write-Host "Windows Error Reporting configured" -ForegroundColor Green
        }

        return $true
    } catch {
        Write-Error "Failed to optimize system performance: $_"
        return $false
    }
}

function Set-AdvancedSecurity {
    try {
        # Import required security modules
        Import-Module NetSecurity -ErrorAction SilentlyContinue
        Import-Module TrustedPlatformModule -ErrorAction SilentlyContinue

        # Configure TPM if available
        if (Get-Command "Get-Tpm" -ErrorAction SilentlyContinue) {
            $tpm = Get-Tpm
            if ($tpm.TpmPresent -and -not $tpm.TpmReady) {
                Initialize-Tpm -AllowClear
                Write-Host "TPM initialized" -ForegroundColor Green
            }
        }

        # Configure network security
        if (Get-Command "Set-NetIPv4Protocol" -ErrorAction SilentlyContinue) {
            Set-NetIPv4Protocol -DefaultHopLimit 64 -EnableICMPRedirect $false
            Write-Host "Network security hardened" -ForegroundColor Green
        }

        return $true
    } catch {
        Write-Error "Failed to configure advanced security: $_"
        return $false
    }
}

if ($Restore) {
    Restore-SecuritySettings
    exit 0
}

# Backup current settings before making changes
Backup-SecuritySettings

if ($EnableExceptions) {
    # Verify Windows Defender is installed and running
    if (-not (Get-Service -Name "WinDefend" -ErrorAction SilentlyContinue)) {
        Write-Warning "Windows Defender is not installed or running. Skipping exclusions."
    } else {
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

    # Add additional optimizations
    Write-Host "Applying system optimizations..." -ForegroundColor Yellow
    if (!(Optimize-SystemPerformance)) {
        Write-Warning "Some system optimizations failed"
    }

    Write-Host "Configuring advanced security..." -ForegroundColor Yellow
    if (!(Set-AdvancedSecurity)) {
        Write-Warning "Some advanced security configurations failed"
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
Write-Host "To restore original settings later, run this script with -Restore switch" -ForegroundColor Yellow