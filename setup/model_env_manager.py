import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
from dataclasses import dataclass

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
        requirements = ModelRequirements(
            python_version="3.10",  # Default Python version
            dependencies=[],
            conda_packages=[],
            pip_packages=[]
        )
        
        # Analyze architecture for requirements
        arch = model_config.get("architecture", "")
        if "transformer" in arch.lower():
            requirements.pip_packages.extend(["transformers", "tokenizers"])
        if "bert" in arch.lower():
            requirements.pip_packages.extend(["bert-tensorflow", "tensorflow"])
        if "gpu" in arch.lower() or model_config.get("gpu_required", False):
            requirements.cuda_required = True
            requirements.conda_packages.append("cudatoolkit")
        
        # Add base requirements
        requirements.conda_packages.extend([
            "pytorch",
            "numpy",
            "pandas",
            "panel",
            "param"
        ])
        
        # Add memory requirement based on model size
        model_size = model_config.get("model_size", "small")
        if model_size == "large":
            requirements.memory_requirement = "16GB"
        elif model_size == "medium":
            requirements.memory_requirement = "8GB"
            
        return requirements
    
    def create_environment_file(self, model_name: str, requirements: ModelRequirements) -> Path:
        """Create a conda environment.yml file for specific model requirements"""
        env_config = {
            "name": f"tensorzero_{model_name}",
            "channels": ["conda-forge", "defaults"],
            "dependencies": [
                f"python={requirements.python_version}",
                "pip",
                *requirements.conda_packages,
                {"pip": requirements.pip_packages}
            ]
        }
        
        # Add CUDA if required
        if requirements.cuda_required:
            env_config["dependencies"].append("cudatoolkit")
        
        env_file = self.base_env_path / f"{model_name}_environment.yml"
        with env_file.open("w") as f:
            yaml.dump(env_config, f, default_flow_style=False)
            
        return env_file
    
    def create_model_environment(self, model_name: str, model_config: Dict) -> str:
        """Create a dedicated conda environment for a specific model"""
        requirements = self.evaluate_model_requirements(model_config)
        env_file = self.create_environment_file(model_name, requirements)
        env_name = f"tensorzero_{model_name}"
        
        # Create conda environment
        try:
            subprocess.run([
                "conda", "env", "create",
                "-f", str(env_file),
                "-n", env_name
            ], check=True)
            
            # Install additional dependencies if needed
            subprocess.run([
                "conda", "run",
                "-n", env_name,
                "pip", "install", "-r", "requirements.txt"
            ], check=True)
            
            return env_name
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create environment for model {model_name}: {str(e)}")
    
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