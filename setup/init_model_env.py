import os
import subprocess
from pathlib import Path
from typing import Optional

def init_model_environment(model_name: str) -> None:
    """Initialize the model environment system"""
    # Create environments directory if it doesn't exist
    env_dir = Path("environments")
    env_dir.mkdir(exist_ok=True)
    
    # Create model-specific directory
    model_dir = env_dir / model_name
    model_dir.mkdir(exist_ok=True)
    
    # Create model-specific .env file
    env_file = model_dir / ".env"
    if not env_file.exists():
        with env_file.open("w") as f:
            f.write(f"MODEL_NAME={model_name}\n")
            f.write("CONDA_PREFIX=${CONDA_PREFIX}\n")
            f.write("PYTHONPATH=${CONDA_PREFIX}/lib/python3.10/site-packages\n")
    
    # Initialize git for version control of model environment
    subprocess.run(["git", "init"], cwd=str(model_dir))
    
    # Create .gitignore
    gitignore = model_dir / ".gitignore"
    if not gitignore.exists():
        with gitignore.open("w") as f:
            f.write("__pycache__/\n")
            f.write("*.pyc\n")
            f.write(".env\n")
            f.write("*.log\n")

def cleanup_model_environment(model_name: str) -> None:
    """Clean up model environment in case of failure"""
    env_dir = Path("environments") / model_name
    if env_dir.exists():
        import shutil
        shutil.rmtree(env_dir)

def validate_environment(model_name: str) -> bool:
    """Validate that the model environment is properly set up"""
    env_dir = Path("environments") / model_name
    required_files = [".env", ".gitignore"]
    return all((env_dir / file).exists() for file in required_files)