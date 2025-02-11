from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Union
import torch
import torch.nn as nn
import asyncio
from enum import Enum

#######################
# Configuration Classes
#######################

@dataclass
class FlywheelConfig:
    """Configuration for intelligence injection via flywheel pattern"""
    learning_rate: float = 0.01
    memory_size: int = 100
    intelligence_factor: float = 0.3
    use_memory: bool = True  # Added use_memory flag
    pattern_recognition: bool = False
    pattern_memory_size: Optional[int] = None

    def __post_init__(self):
        if self.pattern_recognition and self.pattern_memory_size is None:
            self.pattern_memory_size = self.memory_size

class ExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"
    PARALLEL = "parallel"

@dataclass
class ModelConfig:
    """Configuration for TensorZero model"""
    name: str
    architecture: str
    params: Dict[str, Any]
    execution_mode: ExecutionMode = ExecutionMode.SYNC
    flywheel: Optional[FlywheelConfig] = None
    use_mindsdb: bool = False
    mindsdb_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.use_mindsdb and not self.mindsdb_config:
            self.mindsdb_config = {
                "host": "localhost",
                "port": 47334
            }
        if self.use_mindsdb and not self.flywheel:
            # Enable intelligence injection by default for MindsDB integration
            self.flywheel = FlywheelConfig()

########################
# Model Implementation
########################

class DynamicModel(nn.Module):
    """Dynamic neural network model with intelligence injection capability"""
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.memory = []
        self.layers = nn.ModuleList(self._build_architecture())
        
        # Initialize flywheel if not provided
        if self.config.flywheel is None:
            self.config.flywheel = FlywheelConfig()
        
    def _build_architecture(self) -> List[nn.Module]:
        """Build model architecture from string definition"""
        layers = []
        parts = self.config.architecture.split("->")
        
        # Input size from first part (e.g., "x5" -> 5)
        input_size = int(parts[0].strip().replace("x", ""))
        current_size = input_size
        
        # Process each layer definition
        for part in parts[1:]:
            part = part.strip()
            if "Linear" in part:
                size = int(part.split("(")[1].split(")")[0])
                layers.append(nn.Linear(current_size, size))
                current_size = size
            elif part == "ReLU":
                layers.append(nn.ReLU())
            elif part == "Tanh":
                layers.append(nn.Tanh())
            elif part == "Sigmoid":
                layers.append(nn.Sigmoid())
            
        return layers

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Basic forward pass
        for layer in self.layers:
            x = layer(x)
            
        # Apply intelligence injection if using flywheel
        if self.config.flywheel and self.config.flywheel.use_memory:
            x = self._apply_intelligence(x)
            
        return x
        
    def _apply_intelligence(self, x: torch.Tensor) -> torch.Tensor:
        """Apply learned patterns from memory to current output"""
        if not self.memory:
            self.memory.append(x.detach())
            return x
            
        # Calculate influence from memory
        memory_tensor = torch.stack(self.memory[-self.config.flywheel.memory_size:])
        memory_influence = torch.mean(memory_tensor, dim=0)
        
        # Combine current output with memory influence
        intelligence_factor = self.config.flywheel.intelligence_factor
        enhanced_output = (1 - intelligence_factor) * x + intelligence_factor * memory_influence
        
        # Update memory
        self.memory.append(x.detach())
        if len(self.memory) > self.config.flywheel.memory_size:
            self.memory.pop(0)
            
        return enhanced_output

########################
# Model Handler
########################

from tensorzero.quantum.sequence_integration import SequenceQuantumManager
from tensorzero.quantum.electron_interface import ElectronQuantumInterface
from tensorzero.quantum.quantum_memory import QuantumMemoryManager

class ModelHandler:
    """Handles model creation and execution in various modes"""
    def __init__(self, config: ModelConfig):
        self.config = config
        self.models = {}
        self.quantum_manager = None
        self.electron_interface = None
        self.quantum_memory = None
        
        if config.quantum_enabled:
            self._setup_quantum_components()
            
    def _setup_quantum_components(self):
        """Initialize quantum components"""
        self.quantum_manager = SequenceQuantumManager(self.config.quantum_config)
        self.electron_interface = ElectronQuantumInterface(self.config.quantum_config)
        self.quantum_memory = QuantumMemoryManager(self.config.quantum_config)
        
    async def apply_quantum_enhancement(self, model_input: torch.Tensor, model_id: str) -> torch.Tensor:
        """Apply quantum enhancement to model input"""
        if not self.quantum_manager:
            return model_input
            
        # Store pattern in quantum memory
        success = await self.quantum_memory.store_pattern(model_input, model_id)
        if not success:
            return model_input
            
        # Generate entanglement between relevant nodes
        await self.quantum_manager.generate_entanglement(f"router_{model_id}", "router_central")
        
        # Retrieve quantum-enhanced pattern
        enhanced_input = await self.quantum_memory.retrieve_pattern(model_id)
        if enhanced_input is None:
            return model_input
            
        # Update visualization if available
        if self.electron_interface:
            state = self.quantum_manager.get_network_state()
            await self.electron_interface.update_quantum_state(state)
            
        return enhanced_input
        
    async def predict(self, model_id: str, input_data: torch.Tensor) -> torch.Tensor:
        """Enhanced prediction with quantum support"""
        model = self.models.get(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
            
        # Apply quantum enhancement if enabled
        if self.quantum_manager:
            input_data = await self.apply_quantum_enhancement(input_data, model_id)
            
        # Use enhanced input for prediction
        return model(input_data)
    
    def create_model(self, config: ModelConfig) -> DynamicModel:
        """Create a new model from config"""
        model = DynamicModel(config)
        self.models[config.name] = model
        return model
    
    async def _run_async(self, model: DynamicModel, input_data: torch.Tensor) -> torch.Tensor:
        """Run model asynchronously"""
        return await asyncio.to_thread(model.forward, input_data)
    
    async def _run_parallel(self, model: DynamicModel, input_data: List[torch.Tensor]) -> List[torch.Tensor]:
        """Run model in parallel for multiple inputs"""
        tasks = [self._run_async(model, x) for x in input_data]
        return await asyncio.gather(*tasks)
    
    async def run_model(
        self, 
        model_name: str, 
        input_data: Union[torch.Tensor, List[torch.Tensor]]
    ) -> Union[torch.Tensor, List[torch.Tensor]]:
        """Run model with specified execution mode"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
            
        model = self.models[model_name]
        mode = model.config.execution_mode
        
        if mode == ExecutionMode.SYNC:
            return model(input_data)
            
        elif mode == ExecutionMode.ASYNC:
            return await self._run_async(model, input_data)
            
        elif mode == ExecutionMode.PARALLEL:
            if not isinstance(input_data, list):
                raise ValueError("Parallel mode requires list of inputs")
            return await self._run_parallel(model, input_data)

    def get_flywheel_vars(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get current flywheel variables for a model"""
        if model_name not in self.models:
            return None
        model = self.models[model_name]
        if not model.config.flywheel:
            return None
        return {
            "memory_size": len(model.memory) if model.memory else 0,
            "intelligence_factor": model.config.flywheel.intelligence_factor,
            "learning_enabled": model.config.flywheel.use_memory
        }