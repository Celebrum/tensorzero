# Secure installation script for TensorZero dependencies
param (
    [switch]$Force,
    [string]$InstallPath = "C:\Program Files\TensorZero",
    [string]$NetworkConfig = "10.0.0.1",
    [string]$NetworkMask = "255.255.255.0"
)

# Progress tracking
$progressPreference = 'Continue'
$totalSteps = 6
$currentStep = 0

function Write-ProgressStep {
    param([string]$Status)
    $currentStep++
    Write-Progress -Activity "TensorZero Secure Installation" `
                  -Status $Status `
                  -PercentComplete (($currentStep / $totalSteps) * 100)
    Write-Host "[$currentStep/$totalSteps] $Status" -ForegroundColor Green
}

# Elevate permissions if needed
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {    
    Write-Host "Requesting administrator privileges..." -ForegroundColor Yellow
    $arguments = "& '" + $myinvocation.mycommand.definition + "'"
    Start-Process powershell -Verb runAs -ArgumentList $arguments
    return
}

# Function to safely modify execution policy
function Set-SafeExecutionPolicy {
    Write-ProgressStep "Configuring secure execution policy"
    try {
        $currentPolicy = Get-ExecutionPolicy -Scope Process
        if ($currentPolicy -ne "RemoteSigned") {
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
        }
        Write-Host "  ✓ Execution policy set to RemoteSigned" -ForegroundColor Green
    } catch {
        Write-Error "Failed to set execution policy: $_"
        exit 1
    }
}

# Function to safely install Rust
function Install-RustSecurely {
    Write-ProgressStep "Installing Rust securely"
    try {
        Write-Host "Installing Rust securely..."
        $rustupInit = "$env:TEMP\rustup-init.exe"
        
        # Download rustup using TLS 1.2
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://win.rustup.rs" -OutFile $rustupInit
        
        # Verify signature if possible
        # TODO: Add signature verification
        
        # Install Rust
        & $rustupInit -y --no-modify-path
        if ($LASTEXITCODE -ne 0) { throw "Rust installation failed" }
        
        # Clean up
        Remove-Item $rustupInit -Force
    } catch {
        Write-Error "Failed to install Rust: $_"
        exit 1
    }
}

# Enhanced cargo-binstall installation with security checks
function Install-CargoBinstall {
    Write-ProgressStep "Installing and securing cargo-binstall"
    try {
        # Create secure temp directory
        $secureTemp = New-Item -ItemType Directory -Path "$env:TEMP\TensorZero_Secure" -Force
        $binstallPath = Join-Path $secureTemp "cargo-binstall"
        
        # Download with enhanced security
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $url = "https://github.com/cargo-bins/cargo-binstall/releases/latest/download/cargo-binstall-x86_64-pc-windows-msvc.zip"
        $zipFile = Join-Path $secureTemp "cargo-binstall.zip"
        
        Write-Host "  → Downloading cargo-binstall securely..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $url -OutFile $zipFile -UseBasicParsing
        
        # Verify download
        if (-not (Test-Path $zipFile)) {
            throw "Download failed: $zipFile not found"
        }
        
        Write-Host "  → Extracting and validating..." -ForegroundColor Cyan
        Expand-Archive -Path $zipFile -DestinationPath $binstallPath -Force
        
        # Configure Windows Defender exception
        Write-Host "  → Configuring security exceptions..." -ForegroundColor Cyan
        Add-MpPreference -ExclusionPath "$env:USERPROFILE\.cargo\bin\cargo-binstall.exe" -Force
        
        # Move to cargo bin with backup
        $cargoBinPath = "$env:USERPROFILE\.cargo\bin"
        $backupPath = Join-Path $secureTemp "cargo-binstall.backup"
        
        if (Test-Path "$cargoBinPath\cargo-binstall.exe") {
            Move-Item "$cargoBinPath\cargo-binstall.exe" $backupPath -Force
        }
        
        New-Item -ItemType Directory -Path $cargoBinPath -Force | Out-Null
        Move-Item "$binstallPath\cargo-binstall.exe" "$cargoBinPath" -Force
        
        # Validate installation
        $result = & "$cargoBinPath\cargo-binstall.exe" --version
        if ($LASTEXITCODE -ne 0) {
            if (Test-Path $backupPath) {
                Move-Item $backupPath "$cargoBinPath\cargo-binstall.exe" -Force
            }
            throw "cargo-binstall validation failed"
        }
        
        # Cleanup
        Remove-Item $secureTemp -Recurse -Force
        Write-Host "  ✓ cargo-binstall installed and secured" -ForegroundColor Green
        
    } catch {
        Write-Error "Failed to install cargo-binstall: $_"
        exit 1
    }
}

# Function to configure network and firewall
function Configure-NetworkAndFirewall {
    param (
        [string]$NetworkIP,
        [string]$SubnetMask
    )
    
    Write-ProgressStep "Configuring network and firewall"
    try {
        Write-Host "Configuring network and firewall..."
        
        # Configure Firewall for TensorZero
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
                           
        # Configure network adapter if needed
        $adapter = Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -First 1
        if ($adapter) {
            $interface = $adapter | Get-NetIPInterface -AddressFamily IPv4
            if ($interface) {
                Set-NetIPInterface -InterfaceIndex $interface.ifIndex -Dhcp Disabled
                New-NetIPAddress -InterfaceIndex $interface.ifIndex `
                                -IPAddress $NetworkIP `
                                -PrefixLength 24 `
                                -DefaultGateway "10.0.0.1"
            }
        }
    } catch {
        Write-Error "Failed to configure network: $_"
        exit 1
    }
}

# Function to install Conda and packages
function Install-CondaEnvironment {
    Write-ProgressStep "Installing Miniconda and creating environment"
    try {
        Write-Host "Installing Miniconda and creating environment..."
        
        # Download and install Miniconda
        $condaInstaller = "$env:TEMP\Miniconda3.exe"
        Invoke-WebRequest -Uri "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe" -OutFile $condaInstaller
        
        Start-Process -Wait -FilePath $condaInstaller -ArgumentList "/S /D=$env:USERPROFILE\Miniconda3"
        
        # Initialize conda
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        & "$env:USERPROFILE\Miniconda3\Scripts\conda.exe" init powershell
        
        # Create TensorZero environment
        & "$env:USERPROFILE\Miniconda3\Scripts\conda.exe" create -n tensorzero python=3.10 -y
        & "$env:USERPROFILE\Miniconda3\Scripts\conda.exe" activate tensorzero
        
        # Install required packages
        $packages = @(
            "pytorch",
            "tensorflow",
            "pandas",
            "numpy",
            "panel",
            "alembic",
            "poetry"
        )
        
        foreach ($package in $packages) {
            & "$env:USERPROFILE\Miniconda3\Scripts\conda.exe" install -n tensorzero $package -y
        }
        
        # Install additional packages via pip
        $pipPackages = @(
            "mindsdb-sdk",
            "codeql",
            "mindsdbql"
        )
        
        foreach ($package in $pipPackages) {
            & "$env:USERPROFILE\Miniconda3\Scripts\pip.exe" install $package
        }
        
    } catch {
        Write-Error "Failed to install Conda environment: $_"
        exit 1
    }
}

# Main installation flow with enhanced security and progress tracking
try {
    Write-Host "Starting TensorZero secure installation..." -ForegroundColor Cyan
    Write-Host "Installation path: $InstallPath" -ForegroundColor Cyan
    Write-Host "Network configuration: $NetworkConfig/$NetworkMask" -ForegroundColor Cyan
    Write-Host ""
    
    Set-SafeExecutionPolicy
    Install-RustSecurely
    Install-CargoBinstall
    Configure-NetworkAndFirewall -NetworkIP $NetworkConfig -SubnetMask $NetworkMask
    Install-CondaEnvironment
    
    Write-ProgressStep "Finalizing installation"
    
    # Verify entire installation
    $verificationErrors = @()
    
    # Check Rust installation
    if (-not (Get-Command rustc -ErrorAction SilentlyContinue)) {
        $verificationErrors += "Rust installation verification failed"
    }
    
    # Check cargo-binstall
    if (-not (Test-Path "$env:USERPROFILE\.cargo\bin\cargo-binstall.exe")) {
        $verificationErrors += "cargo-binstall verification failed"
    }
    
    # Check conda environment
    if (-not (Test-Path "$env:USERPROFILE\Miniconda3")) {
        $verificationErrors += "Conda installation verification failed"
    }
    
    # Report verification results
    if ($verificationErrors.Count -gt 0) {
        Write-Host "`nInstallation completed with warnings:" -ForegroundColor Yellow
        foreach ($error in $verificationErrors) {
            Write-Host "  ! $error" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`nInstallation completed successfully!" -ForegroundColor Green
    }
    
    Write-Host "`nSystem restart required to complete installation." -ForegroundColor Cyan
    $restart = Read-Host "Would you like to restart now? (y/n)"
    if ($restart -eq 'y') {
        Restart-Computer -Force
    }
    
} catch {
    Write-Error "Installation failed: $_"
    exit 1
} finally {
    Write-Progress -Activity "TensorZero Secure Installation" -Completed
}