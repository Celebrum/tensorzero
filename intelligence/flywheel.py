"""
TensorZero Simple Time Series Forecasting
Using MindsDB Auto-build and Pattern Recognition
"""

from typing import Dict, Any, List
import numpy as np
from mindsdb_sdk import MindsDB
from datetime import datetime, timedelta

class TimeSeriesEngine:
    def __init__(self, config: Dict[str, Any]):
        """Initialize with MindsDB connection and basic settings"""
        self.mindsdb = MindsDB(config.get("mindsdb_url", "http://localhost:47334"))
        self.history_window = config.get("history_window", 30)
        self.forecast_horizon = config.get("forecast_horizon", 7)
        
    async def create_forecaster(self, 
                              name: str,
                              data: List[Dict[str, Any]],
                              target_column: str) -> str:
        """Auto-build a time series model"""
        try:
            # Validate data format
            if not all('timestamp' in x and target_column in x for x in data):
                raise ValueError("Data must contain 'timestamp' and target column")
                
            # Create and train model
            model = await self.mindsdb.create_model(
                name=name,
                predict=target_column,
                training_data=data,
                options={
                    'model_type': 'time_series',
                    'window': self.history_window,
                    'horizon': self.forecast_horizon
                }
            )
            return f"Model {name} created successfully"
            
        except Exception as e:
            return f"Error creating model: {str(e)}"
    
    async def predict(self,
                     model_name: str,
                     latest_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate time series forecast"""
        try:
            model = self.mindsdb.get_model(model_name)
            
            # Make prediction
            prediction = await model.predict(latest_data)
            
            # Enhance prediction with simple smoothing
            enhanced = self._smooth_prediction(prediction["prediction"])
            
            return {
                "forecast": enhanced,
                "confidence": prediction.get("confidence", 0.0),
                "horizon": self.forecast_horizon
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _smooth_prediction(self, prediction: np.ndarray) -> np.ndarray:
        """Apply simple moving average smoothing"""
        window = min(3, len(prediction))
        return np.convolve(prediction, np.ones(window)/window, mode='valid')