# Secure installation script for TensorZero dependencies
param (
    [switch]$Force,
    [string]$InstallPath = "C:\Program Files\TensorZero",
    [string]$NetworkConfig = "10.0.0.1",
    [string]$NetworkMask = "255.255.255.0"
)

# Elevate permissions if needed
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {    
    $arguments = "& '" + $myinvocation.mycommand.definition + "'"
    Start-Process powershell -Verb runAs -ArgumentList $arguments
    return
}

# Function to safely modify execution policy
function Set-SafeExecutionPolicy {
    try {
        Write-Host "Configuring execution policy for installation..."
        $currentPolicy = Get-ExecutionPolicy -Scope Process
        if ($currentPolicy -ne "RemoteSigned") {
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
        }
    } catch {
        Write-Error "Failed to set execution policy: $_"
        exit 1
    }
}

# Function to safely install Rust
function Install-RustSecurely {
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

# Function to safely configure cargo-binstall
function Install-CargoBinstall {
    try {
        Write-Host "Installing cargo-binstall..."
        $binstallPath = "$env:TEMP\cargo-binstall"
        
        # Download using TLS 1.2
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $url = "https://github.com/cargo-bins/cargo-binstall/releases/latest/download/cargo-binstall-x86_64-pc-windows-msvc.zip"
        $zipFile = "$env:TEMP\cargo-binstall.zip"
        
        Invoke-WebRequest -Uri $url -OutFile $zipFile
        
        # Safely extract and install
        if (Test-Path $binstallPath) {
            Remove-Item $binstallPath -Recurse -Force
        }
        
        Expand-Archive -Path $zipFile -DestinationPath $binstallPath -Force
        
        # Move to cargo bin directory
        $cargoBinPath = "$env:USERPROFILE\.cargo\bin"
        if (-not (Test-Path $cargoBinPath)) {
            New-Item -ItemType Directory -Path $cargoBinPath -Force
        }
        
        Move-Item -Path "$binstallPath\cargo-binstall.exe" -Destination $cargoBinPath -Force
        
        # Clean up
        Remove-Item $zipFile -Force
        Remove-Item $binstallPath -Recurse -Force
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

# Main installation flow
try {
    Write-Host "Starting secure TensorZero installation..."
    
    Set-SafeExecutionPolicy
    Install-RustSecurely
    Install-CargoBinstall
    Configure-NetworkAndFirewall -NetworkIP $NetworkConfig -SubnetMask $NetworkMask
    Install-CondaEnvironment
    
    Write-Host "Installation completed successfully. System restart required."
    
    $restart = Read-Host "Would you like to restart now? (y/n)"
    if ($restart -eq 'y') {
        Restart-Computer -Force
    }
    
} catch {
    Write-Error "Installation failed: $_"
    exit 1
}