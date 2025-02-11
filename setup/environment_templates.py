from pathlib import Path
from typing import Dict

# Base template configurations for different model types
MODEL_TEMPLATES = {
    "transformer": {
        "conda_packages": [
            "pytorch>=2.0.1",
            "numpy>=1.20.0",
            "pandas>=1.5.0"
        ],
        "pip_packages": [
            "transformers>=4.0.0",
            "tokenizers>=0.10.0",
            "sentencepiece>=0.1.95"
        ],
        "memory_req": "8GB",
        "gpu_recommended": True
    },
    "neural_network": {
        "conda_packages": [
            "pytorch>=2.0.1",
            "numpy>=1.20.0",
            "scipy>=1.7.0"
        ],
        "pip_packages": [
            "scikit-learn>=0.24.0"
        ],
        "memory_req": "4GB",
        "gpu_recommended": False
    },
    "nlp": {
        "conda_packages": [
            "pytorch>=2.0.1",
            "numpy>=1.20.0",
            "pandas>=1.5.0"
        ],
        "pip_packages": [
            "nltk>=3.6.0",
            "spacy>=3.0.0",
            "gensim>=4.0.0"
        ],
        "memory_req": "6GB",
        "gpu_recommended": True
    }
}

def detect_model_type(architecture: str) -> str:
    """Detect model type from architecture description"""
    architecture = architecture.lower()
    if any(x in architecture for x in ["transformer", "bert", "gpt"]):
        return "transformer"
    elif any(x in architecture for x in ["lstm", "attention", "encoder"]):
        return "nlp"
    return "neural_network"

def generate_environment_config(model_name: str, architecture: str) -> Dict:
    """Generate environment configuration based on model type"""
    model_type = detect_model_type(architecture)
    template = MODEL_TEMPLATES[model_type]
    
    # Generate environment name
    env_name = f"tensorzero_{model_name}_{model_type}"
    
    return {
        "name": env_name,
        "channels": [
            "conda-forge",
            "defaults"
        ],
        "dependencies": [
            "python=3.10",
            *template["conda_packages"],
            {"pip": template["pip_packages"]},
            "panel>=1.0.0",
            "param>=2.0.0"
        ],
        "variables": {
            "MODEL_TYPE": model_type,
            "MEMORY_REQ": template["memory_req"],
            "GPU_RECOMMENDED": str(template["gpu_recommended"]).lower(),
            "CONDA_STDOUT_CAPTURE": "1"
        }
    }