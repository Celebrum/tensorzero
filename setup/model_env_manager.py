import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
from dataclasses import dataclass
from .environment_templates import generate_environment_config, detect_model_type

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
        """Create a dedicated conda environment for a specific model"""
        requirements = self.evaluate_model_requirements(model_config)
        env_file = self.create_environment_file(model_name, requirements)
        env_name = f"tensorzero_{model_name}"
        
        # Check if environment already exists
        result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
        if env_name in result.stdout:
            print(f"Environment {env_name} already exists, updating...")
            update_cmd = ["conda", "env", "update", "-n", env_name, "-f", str(env_file)]
            subprocess.run(update_cmd, check=True)
        else:
            # Create new environment
            create_cmd = ["conda", "env", "create", "-f", str(env_file)]
            subprocess.run(create_cmd, check=True)
        
        # Install additional dependencies
        with subprocess.Popen(
            f"conda run -n {env_name} pip install -r requirements.txt",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) as proc:
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                print(f"Warning: pip install returned {proc.returncode}: {stderr.decode()}")
            
        return env_name
    
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