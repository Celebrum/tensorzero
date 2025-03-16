from typing import Optional, Dict, Any
from .model_handler import ModelHandler, ModelConfig, FlywheelConfig
import torch
import mindsdb_sdk
from asyncio import Lock

class TensorZeroGateway:
    """Main gateway class for TensorZero"""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.model_handler = ModelHandler()
        self.config = config or {}
        self._mindsdb_lock = Lock()
        self._mindsdb_clients = {}
        
    async def create_model(self, name: str, architecture: str, **kwargs):
        """Create a new model with the given architecture"""
        config = ModelConfig(
            name=name,
            architecture=architecture,
            params=kwargs.get('params', {}),
            flywheel=FlywheelConfig(
                batch_size=kwargs.get('batch_size', 32),
                learning_rate=kwargs.get('learning_rate', 0.001),
                optimizer=kwargs.get('optimizer', 'adam'),
                **kwargs.get('flywheel', {})
            )
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

    async def integrate_mindsdb(self, mindsdb_url: str, model_name: str, input_data: Dict[str, Any]):
        """Integrate with MindsDB for additional ML capabilities
        
        Args:
            mindsdb_url: The URL of the MindsDB instance
            model_name: Name of the MindsDB model to use
            input_data: Input data for prediction
        """
        async with self._mindsdb_lock:
            if mindsdb_url not in self._mindsdb_clients:
                self._mindsdb_clients[mindsdb_url] = mindsdb_sdk.Client(mindsdb_url)
            
            client = self._mindsdb_clients[mindsdb_url]
            model = await client.get_model(model_name)
            result = await model.predict(input_data)
            return result

    async def close(self):
        """Close all connections and clean up resources"""
        async with self._mindsdb_lock:
            for client in self._mindsdb_clients.values():
                await client.close()
            self._mindsdb_clients.clear()