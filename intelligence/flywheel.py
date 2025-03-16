"""
TensorZero Simple Time Series Forecasting
Using MindsDB Auto-build and Pattern Recognition
"""

from typing import Dict, Any, List
import numpy as np
from mindsdb_sdk import MindsDB
from datetime import datetime, timedelta
import torch

class TimeSeriesEngine:
    def __init__(self, config: Dict[str, Any]):
        """Initialize with MindsDB connection and dual mode settings"""
        self.mindsdb = MindsDB(config.get("mindsdb_url", "http://localhost:47334"))
        self.history_window = config.get("history_window", 30)
        self.forecast_horizon = config.get("forecast_horizon", 7)
        self.pattern_memory = []
        self.dual_mode_enabled = config.get("dual_mode", {}).get("enabled", True)
        self.smoothing_window = config.get("smoothing", {}).get("window_size", 3)
        
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
        """Generate time series forecast with dual pattern recognition"""
        try:
            model = self.mindsdb.get_model(model_name)
            
            # Make prediction
            prediction = await model.predict(latest_data)
            
            if self.dual_mode_enabled:
                # Convert to tensor for pattern analysis
                pred_tensor = torch.tensor(prediction["prediction"])
                
                # Apply adaptive smoothing
                window = min(self.smoothing_window, len(pred_tensor))
                smoothed = torch.nn.functional.avg_pool1d(
                    pred_tensor.unsqueeze(0).unsqueeze(0),
                    kernel_size=window,
                    stride=1,
                    padding=window//2
                ).squeeze()
                
                # Store pattern in memory
                self.pattern_memory.append({
                    "timestamp": datetime.now(),
                    "pattern": smoothed.numpy(),
                    "confidence": prediction.get("confidence", 0.0)
                })
                
                # Update prediction with enhanced pattern
                prediction["prediction"] = smoothed.numpy()
            
            return {
                "forecast": prediction["prediction"],
                "confidence": prediction.get("confidence", 0.0),
                "horizon": self.forecast_horizon,
                "pattern_detected": self.dual_mode_enabled
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _smooth_prediction(self, prediction: np.ndarray) -> np.ndarray:
        """Apply simple moving average smoothing"""
        window = min(3, len(prediction))
        return np.convolve(prediction, np.ones(window)/window, mode='valid')

    def _detect_patterns(self, data: np.ndarray) -> Optional[Dict[str, Any]]:
        """Detect statistical patterns in time series data"""
        if len(data) < 2:
            return None
            
        # Calculate trend
        x = np.arange(len(data))
        z = np.polyfit(x, data, 1)
        trend = np.poly1d(z)
        
        # Calculate seasonality using FFT
        fft = np.fft.fft(data)
        freqs = np.fft.fftfreq(len(data))
        peak_freq = freqs[np.argmax(np.abs(fft))]
        
        return {
            "trend_slope": float(z[0]),
            "seasonality_freq": float(peak_freq),
            "strength": float(np.max(np.abs(fft)) / len(data))
        }