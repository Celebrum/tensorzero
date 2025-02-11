import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
from pathlib import Path
from .security_policy import SecurityPolicyManager
import subprocess
import logging

class TensorZeroSecurityService(win32serviceutil.ServiceFramework):
    _svc_name_ = "TensorZeroSecurity"
    _svc_display_name_ = "TensorZero Security Monitor"
    _svc_description_ = "Maintains secure configuration for TensorZero components"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.security_manager = SecurityPolicyManager()
        
        # Set up logging
        log_path = Path("C:/ProgramData/TensorZero/logs")
        log_path.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=str(log_path / "security_service.log"),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        """Main service run loop"""
        try:
            logging.info("TensorZero Security Service starting...")
            
            # Initial security verification
            if not self.security_manager.verify_installation():
                logging.warning("Security configuration needs repair")
                self._repair_security_config()
            
            while True:
                # Check if service should stop
                rc = win32event.WaitForSingleObject(self.stop_event, 5000)
                if rc == win32event.WAIT_OBJECT_0:
                    break
                    
                # Periodic security checks
                self._perform_security_checks()
                
        except Exception as e:
            logging.error(f"Service error: {str(e)}")
            servicemanager.LogErrorMsg(str(e))

    def _perform_security_checks(self):
        """Perform periodic security verification"""
        try:
            # Verify firewall rules
            self._verify_firewall_rules()
            
            # Verify network configuration
            self._verify_network_config()
            
            # Verify cargo-binstall installation
            self._verify_cargo_binstall()
            
            # Verify conda environment
            self._verify_conda_env()
            
        except Exception as e:
            logging.error(f"Security check failed: {str(e)}")
            self._repair_security_config()

    def _verify_firewall_rules(self):
        """Verify firewall rules are properly configured"""
        try:
            # Check Gateway rule
            gateway_check = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", "name=TensorZero Gateway"],
                capture_output=True, text=True
            )
            
            # Check Flywheel rule
            flywheel_check = subprocess.run(
                ["netsh", "advfirewall", "firewall", "show", "rule", "name=TensorZero Flywheel"],
                capture_output=True, text=True
            )
            
            if "No rules match the specified criteria" in gateway_check.stdout or \
               "No rules match the specified criteria" in flywheel_check.stdout:
                logging.warning("Firewall rules need repair")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Firewall verification failed: {str(e)}")
            return False

    def _verify_network_config(self):
        """Verify network configuration"""
        try:
            result = subprocess.run(["ipconfig"], capture_output=True, text=True)
            if "10.0.0.1" not in result.stdout:
                logging.warning("Network configuration needs repair")
                return False
            return True
        except Exception as e:
            logging.error(f"Network verification failed: {str(e)}")
            return False

    def _verify_cargo_binstall(self):
        """Verify cargo-binstall is properly installed"""
        cargo_path = Path.home() / ".cargo" / "bin" / "cargo-binstall.exe"
        if not cargo_path.exists():
            logging.warning("cargo-binstall needs repair")
            return False
        return True

    def _verify_conda_env(self):
        """Verify conda environment"""
        try:
            result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
            if "tensorzero" not in result.stdout:
                logging.warning("Conda environment needs repair")
                return False
            return True
        except Exception as e:
            logging.error(f"Conda verification failed: {str(e)}")
            return False

    def _repair_security_config(self):
        """Repair security configuration"""
        try:
            logging.info("Attempting to repair security configuration...")
            
            # Run secure installation script
            script_path = Path(__file__).parent / "secure_install.ps1"
            subprocess.run([
                "powershell",
                "-ExecutionPolicy", "Bypass",
                "-File", str(script_path),
                "-Force"  # Force reinstallation
            ], check=True)
            
            # Reconfigure persistence
            self.security_manager.configure_persistence()
            
            logging.info("Security configuration repaired successfully")
            
        except Exception as e:
            logging.error(f"Failed to repair security configuration: {str(e)}")
            
if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TensorZeroSecurityService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TensorZeroSecurityService)