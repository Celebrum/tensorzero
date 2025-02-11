import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
from dataclasses import dataclass
from .environment_templates import generate_environment_config, detect_model_type
from .security_policy import SecurityPolicyManager

@dataclass
class ModelRequirements:
    python_version: str
    dependencies: List[str]
    conda_packages: List[str]
    pip_packages: List[str]
    cuda_required: bool = False
    memory_requirement: str = "4GB"

class ModelEnvironmentManager:
    def __init__(self, base_env_path: str = "environments"):
        self.base_env_path = Path(base_env_path)
        self.base_env_path.mkdir(exist_ok=True)
        self.security_manager = SecurityPolicyManager()
        
    def _verify_secure_environment(self) -> bool:
        """Verify security prerequisites are met"""
        if not self.security_manager.verify_installation():
            # Attempt to fix security configuration
            try:
                # Run secure installation script
                script_path = Path(__file__).parent / "secure_install.ps1"
                subprocess.run([
                    "powershell", 
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(script_path)
                ], check=True)
                
                # Configure persistence
                self.security_manager.configure_persistence()
                
                return self.security_manager.verify_installation()
            except Exception as e:
                print(f"Failed to configure secure environment: {str(e)}")
                self.security_manager.cleanup_failed_install()
                return False
        return True
        
    def evaluate_model_requirements(self, model_config: Dict) -> ModelRequirements:
        """Analyze model configuration and determine requirements"""
        # Detect model type and get base requirements
        model_type = detect_model_type(model_config.get("architecture", ""))
        env_config = generate_environment_config(
            model_config.get("name", "unnamed"),
            model_config.get("architecture", "")
        )
        
        requirements = ModelRequirements(
            python_version=env_config.get("dependencies", ["python=3.10"])[0].split("=")[1],
            dependencies=[],
            conda_packages=[dep for dep in env_config.get("dependencies", []) if isinstance(dep, str)],
            pip_packages=env_config.get("dependencies", [{}])[-1].get("pip", [])
        )
        
        # Add GPU requirements if needed
        if (model_config.get("gpu_required", False) or 
            env_config.get("variables", {}).get("GPU_RECOMMENDED", "false") == "true"):
            requirements.cuda_required = True
            requirements.conda_packages.append("cudatoolkit")
        
        # Set memory requirement
        requirements.memory_requirement = env_config.get("variables", {}).get("MEMORY_REQ", "4GB")
            
        return requirements
    
    def create_environment_file(self, model_name: str, requirements: ModelRequirements) -> Path:
        """Create a conda environment.yml file for specific model requirements"""
        env_config = generate_environment_config(model_name, requirements)
        
        env_file = self.base_env_path / f"{model_name}_environment.yml"
        with env_file.open("w") as f:
            yaml.dump(env_config, f, default_flow_style=False)
            
        return env_file
    
    def create_model_environment(self, model_name: str, model_config: Dict) -> str:
        """Create a dedicated conda environment for a specific model with security checks"""
        if not self._verify_secure_environment():
            raise RuntimeError("Failed to verify secure environment")
            
        try:
            # Create environment with security policies
            env_name = f"tensorzero_{model_name}"
            
            # Check if environment exists
            result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
            if env_name in result.stdout:
                print(f"Environment {env_name} already exists, updating...")
                update_cmd = ["conda", "env", "update", "-n", env_name, "-f", str(self._generate_env_file(model_name, model_config))]
                subprocess.run(update_cmd, check=True)
            else:
                # Create new environment
                create_cmd = ["conda", "env", "create", "-f", str(self._generate_env_file(model_name, model_config))]
                subprocess.run(create_cmd, check=True)

            # Set up model-specific security policies
            self._configure_model_security(model_name)
            
            return env_name
            
        except Exception as e:
            self.cleanup_environment(model_name)
            raise RuntimeError(f"Failed to create model environment: {str(e)}")
            
    def _configure_model_security(self, model_name: str):
        """Configure model-specific security settings"""
        model_dir = self.base_env_path / model_name
        model_dir.mkdir(exist_ok=True)
        
        # Create model-specific security policy
        policy_file = model_dir / "security_policy.toml"
        policy = {
            "network": {
                "allowed_ports": [3000, 3001],  # Gateway and Flywheel ports
                "allowed_ips": ["10.0.0.1/24"]
            },
            "execution": {
                "allow_cuda": True,
                "allow_network": True
            }
        }
        
        with policy_file.open("w") as f:
            import toml
            toml.dump(policy, f)
            
    def _generate_env_file(self, model_name: str, model_config: Dict) -> Path:
        """Generate environment file with security configurations"""
        env_file = self.base_env_path / f"{model_name}_environment.yml"
        
        env_config = {
            "name": f"tensorzero_{model_name}",
            "channels": ["conda-forge", "defaults"],
            "dependencies": [
                "python=3.10",
                "pip",
                "pytorch>=2.0.1",
                "tensorflow>=2.0.0",
                "numpy>=1.20.0",
                "pandas>=1.5.0",
                "panel>=1.0.0",
                "param>=2.0.0",
                "alembic>=1.0.0",
                {"pip": [
                    "mindsdb-sdk>=3.0.0",
                    "poetry>=1.0.0",
                    "codeql>=2.0.0",
                    "mindsdbql>=1.0.0"
                ]}
            ],
            "variables": {
                "TENSORZERO_SECURE": "1",
                "CARGO_HOME": str(Path.home() / ".cargo"),
                "CONDA_STDOUT_CAPTURE": "1"
            }
        }
        
        # Add model-specific requirements
        if "gpu_required" in model_config and model_config["gpu_required"]:
            env_config["dependencies"].append("cudatoolkit")
            
        with env_file.open("w") as f:
            yaml.dump(env_config, f, default_flow_style=False)
            
        return env_file
    
    def activate_model_environment(self, model_name: str) -> None:
        """Activate the conda environment for a specific model"""
        env_name = f"tensorzero_{model_name}"
        if os.name == "nt":  # Windows
            activate_cmd = f"conda activate {env_name}"
        else:  # Linux/Mac
            activate_cmd = f"source activate {env_name}"
            
        subprocess.run(activate_cmd, shell=True, check=True)
    
    def cleanup_environment(self, model_name: str) -> None:
        """Remove a model's conda environment"""
        env_name = f"tensorzero_{model_name}"
        subprocess.run(["conda", "env", "remove", "-n", env_name], check=True)