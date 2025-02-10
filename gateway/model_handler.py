# Moving contents from mindsdb_gateway.py to model_handler.py
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
import torch
import torch.nn as nn
import asyncio
from enum import Enum

@dataclass 
class FlywheelConfig:
    """Configuration for intelligence injection via flywheel pattern"""
    learning_rate: float = 0.01
    memory_size: int = 1000
    intelligence_factor: float = 0.5
    use_memory: bool = True

class ExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"

@dataclass
class ModelConfig:
    name: str
    architecture: str
    params: Dict[str, Any]  
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    flywheel: Optional[FlywheelConfig] = None

# ...existing DynamicModel class...

class ModelHandler:
    # ...existing ModelHandler class...