from typing import Optional, Dict, Any
from .model_handler import ModelHandler, ModelConfig, FlywheelConfig
import torch

class TensorZeroGateway:
    """Main gateway class for TensorZero"""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.model_handler = ModelHandler()
        self.config = config or {}
        
    async def create_model(self, name: str, architecture: str, **kwargs):
        """Create a new model with the given architecture"""
        config = ModelConfig(
            name=name,
            architecture=architecture,
            params=kwargs.get('params', {}),
            flywheel=FlywheelConfig(**kwargs.get('flywheel', {}))
        )
        return self.model_handler.create_model(config)
        
    async def predict(self, model_name: str, input_data: torch.Tensor):
        """Run prediction on the given model"""
        return await self.model_handler.run_model(model_name, input_data)

    def get_model_info(self, model_name: str):
        """Get information about a model"""
        if model_name not in self.model_handler.models:
            return None
        model = self.model_handler.models[model_name]
        return {
            "architecture": model.config.architecture,
            "flywheel": self.model_handler.get_flywheel_vars(model_name)
        }
