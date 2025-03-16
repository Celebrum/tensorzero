from typing import Optional, Dict, Any, List
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

    async def create_time_series_model(
        self,
        name: str,
        data: List[Dict[str, Any]],
        target_column: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """Create a time series model using MindsDB"""
        config = config or {}
        mindsdb_url = config.get("mindsdb_url", "http://localhost:47334")
        
        async with self._mindsdb_lock:
            if mindsdb_url not in self._mindsdb_clients:
                self._mindsdb_clients[mindsdb_url] = mindsdb_sdk.MindsDB(mindsdb_url)
            
            client = self._mindsdb_clients[mindsdb_url]
            model = await client.create_model(
                name=name,
                predict=target_column,
                training_data=data,
                options={
                    'model_type': 'time_series',
                    'window': config.get('history_window', 30),
                    'horizon': config.get('forecast_horizon', 7)
                }
            )
            return model

    async def predict(self, model_name: str, input_data: torch.Tensor):
        """Run prediction on the given model"""
        return await self.model_handler.run_model(model_name, input_data)
        
    async def forecast(
        self,
        model_name: str,
        latest_data: List[Dict[str, Any]],
        mindsdb_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate time series forecast using MindsDB model"""
        mindsdb_url = mindsdb_url or "http://localhost:47334"
        
        async with self._mindsdb_lock:
            if mindsdb_url not in self._mindsdb_clients:
                self._mindsdb_clients[mindsdb_url] = mindsdb_sdk.MindsDB(mindsdb_url)
            
            client = self._mindsdb_clients[mindsdb_url]
            model = await client.get_model(model_name)
            
            # Make prediction
            prediction = await model.predict(latest_data)
            
            # Apply pattern recognition if enabled
            if self.config.get("pattern_recognition", {}).get("enabled", False):
                prediction = await self._enhance_forecast(prediction)
            
            return prediction
            
    async def _enhance_forecast(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Apply pattern recognition enhancements to forecast"""
        if not isinstance(prediction.get("prediction"), torch.Tensor):
            prediction["prediction"] = torch.tensor(prediction["prediction"])
            
        # Apply smoothing for better pattern detection
        window = min(3, len(prediction["prediction"]))
        smoothed = torch.nn.functional.avg_pool1d(
            prediction["prediction"].unsqueeze(0).unsqueeze(0),
            kernel_size=window,
            stride=1,
            padding=window//2
        ).squeeze()
        
        prediction["prediction"] = smoothed
        return prediction

    def get_model_info(self, model_name: str):
        """Get information about a model"""
        if model_name not in self.model_handler.models:
            return None
        model = self.model_handler.models[model_name]
        return {
            "architecture": model.config.architecture,
            "flywheel": self.model_handler.get_flywheel_vars(model_name)
        }
        
    async def close(self):
        """Close all connections and clean up resources"""
        for client in self._mindsdb_clients.values():
            await client.close()
        self._mindsdb_clients.clear()