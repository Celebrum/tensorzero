"""
TensorZero Gateway - Dynamic Model Creation with Intelligence Injection

This module provides tools for creating and managing AI models with built-in
intelligence injection via the flywheel pattern.

Key Features:
- Dynamic model creation from string architecture definitions
- Intelligence injection through memory-based pattern recognition
- Support for sync, async, and parallel execution modes
- No external API dependencies
"""

from .model_handler import (
    ModelHandler,
    ModelConfig,
    FlywheelConfig,
    ExecutionMode,
    DynamicModel
)

__version__ = "0.1.0"
__all__ = [
    'ModelHandler',
    'ModelConfig',
    'FlywheelConfig',
    'ExecutionMode',
    'DynamicModel'
]