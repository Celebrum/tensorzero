@dataclass
class NetworkConfig:
    ip_address: str = "10.0.0.1"
    subnet_mask: str = "255.255.255.0"
    gateway_port: int = 3000
    flywheel_port: int = 3001

class SecurityPolicyManager:
    def __init__(self):
        self.network_config = NetworkConfig()
        self.cargo_path = Path.home() / ".cargo" / "bin"
        self.conda_path = Path.home() / "Miniconda3"
        
    def configure_persistence(self):
        """Configure settings to persist after reboot"""
        startup_script = """
        @echo off
        :: Restore TensorZero network configuration
        netsh interface ip set address name="TensorZero" static {ip} {mask} {gateway}
        netsh advfirewall firewall add rule name="TensorZero Gateway" dir=in action=allow protocol=TCP localport={gport}
        netsh advfirewall firewall add rule name="TensorZero Flywheel" dir=in action=allow protocol=TCP localport={fport}
        
        :: Restore cargo environment
        set PATH=%PATH%;{cargo_path}
        
        :: Initialize conda
        call {conda_path}\\Scripts\\activate.bat tensorzero
        """.format(
            ip=self.network_config.ip_address,
            mask=self.network_config.subnet_mask,
            gateway=self.network_config.ip_address,
            gport=self.network_config.gateway_port,
            fport=self.network_config.flywheel_port,
            cargo_path=self.cargo_path,
            conda_path=self.conda_path
        )
        
        # Write startup script
        startup_path = Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp/tensorzero_init.bat")
        startup_path.write_text(startup_script)
        
    def verify_installation(self) -> bool:
        """Verify all components are properly installed"""
        checks = [
            self._check_rust_installation(),
            self._check_cargo_binstall(),
            self._check_conda_environment(),
            self._check_network_configuration()
        ]
        return all(checks)
    
    def _check_rust_installation(self) -> bool:
        try:
            subprocess.run(["rustc", "--version"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
            
    def _check_cargo_binstall(self) -> bool:
        try:
            subprocess.run(["cargo-binstall", "--version"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
            
    def _check_conda_environment(self) -> bool:
        try:
            subprocess.run(["conda", "env", "list"], check=True)
            return Path(self.conda_path).exists()
        except subprocess.CalledProcessError:
            return False
            
    def _check_network_configuration(self) -> bool:
        try:
            result = subprocess.run(["ipconfig"], capture_output=True, text=True)
            return self.network_config.ip_address in result.stdout
        except subprocess.CalledProcessError:
            return False

    def cleanup_failed_install(self):
        """Clean up any remnants of a failed installation"""
        try:
            # Remove firewall rules
            subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule", 
                          "name=TensorZero Gateway"], check=False)
            subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule",
                          "name=TensorZero Flywheel"], check=False)
            
            # Reset network configuration
            subprocess.run(["netsh", "interface", "ip", "set", "address", 
                          "name=TensorZero", "source=dhcp"], check=False)
            
            # Remove startup script
            startup_path = Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp/tensorzero_init.bat")
            if startup_path.exists():
                startup_path.unlink()
                
        except Exception as e:
            print(f"Warning: Cleanup failed: {str(e)}")