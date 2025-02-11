from enum import Enum
from typing import Dict, Any, Optional, Union
import docker
import grpc
from tensorzero.gateway import ModelHandler, FlywheelConfig

class GatewayMode(Enum):
    SIMPLE = "simple"
    EXPERT = "expert"
    HYBRID = "hybrid"

class ContainerManager:
    def __init__(self, registry_url: str = "localhost:5000"):
        self.docker_client = docker.from_env()
        self.registry_url = registry_url
        self.user_containers: Dict[str, Any] = {}
        self.shared_memory = {}
        
    async def start_user_container(self, container_config: Dict[str, Any]) -> str:
        """Start a user's custom container and connect it to the gateway"""
        container = self.docker_client.containers.run(
            image=f"{self.registry_url}/{container_config['image']}",
            name=f"user-container-{container_config['id']}",
            network="tensorzero_network",
            environment={
                "FLYWHEEL_ENDPOINT": "http://gateway:3000/flywheel",
                "CONTAINER_ID": container_config['id']
            },
            volumes={
                "tensorzero_shared": {"bind": "/shared", "mode": "rw"}
            },
            detach=True
        )
        self.user_containers[container_config['id']] = container
        return container.id

    async def stop_user_container(self, container_id: str):
        """Stop and remove a user container"""
        if container_id in self.user_containers:
            container = self.user_containers[container_id]
            container.stop()
            container.remove()
            del self.user_containers[container_id]

class DualModeGateway:
    def __init__(self, config_path: str):
        self.model_handler = ModelHandler()
        self.container_manager = ContainerManager()
        self.mode = GatewayMode.HYBRID
        self.load_config(config_path)
        
    async def create_model(
        self, 
        name: str, 
        mode: GatewayMode,
        config: Optional[Dict[str, Any]] = None,
        container_config: Optional[Dict[str, Any]] = None
    ):
        """Create model in either simple or expert mode"""
        if mode == GatewayMode.SIMPLE:
            # Simple mode - use built-in architecture
            return await self._create_simple_model(name, config)
        else:
            # Expert mode - support custom container
            return await self._create_expert_model(name, config, container_config)

    async def _create_simple_model(self, name: str, config: Optional[Dict[str, Any]]):
        """Create a simple model for beginners"""
        if config is None:
            config = {
                "architecture": self.config["simple_mode"]["default_architecture"],
                "auto_optimization": True
            }
        
        model_config = ModelConfig(
            name=name,
            architecture=config["architecture"],
            params={"learning_rate": 0.01},
            flywheel=FlywheelConfig(
                learning_rate=0.01,
                memory_size=self.config["flywheel"]["memory_size"],
                intelligence_factor=self.config["flywheel"]["intelligence_factor"]
            )
        )
        return self.model_handler.create_model(model_config)

    async def _create_expert_model(
        self, 
        name: str, 
        config: Dict[str, Any],
        container_config: Optional[Dict[str, Any]]
    ):
        """Create an expert model with custom container support"""
        if container_config:
            # Start user's custom container
            container_id = await self.container_manager.start_user_container(container_config)
            
            # Register container in flywheel memory
            self.container_manager.shared_memory[name] = {
                "container_id": container_id,
                "config": config,
                "memory": []
            }
        
        # Create base model that will interface with custom container
        model_config = ModelConfig(
            name=name,
            architecture=config["architecture"],
            params=config.get("params", {}),
            flywheel=FlywheelConfig(
                learning_rate=config.get("learning_rate", 0.01),
                memory_size=self.config["flywheel"]["memory_size"],
                intelligence_factor=self.config["flywheel"]["intelligence_factor"],
                use_memory=True
            )
        )
        return self.model_handler.create_model(model_config)

    async def inference(
        self,
        model_name: str,
        input_data: Any,
        use_container: bool = False
    ) -> Any:
        """Run inference in either mode"""
        if use_container and model_name in self.container_manager.shared_memory:
            # Route to custom container
            return await self._container_inference(model_name, input_data)
        else:
            # Use built-in model
            return await self.model_handler.run_model(model_name, input_data)

    async def _container_inference(self, model_name: str, input_data: Any) -> Any:
        """Run inference through user's custom container"""
        container_info = self.container_manager.shared_memory[model_name]
        container = self.user_containers[container_info["container_id"]]
        
        # Send inference request to container
        response = await self._send_container_request(
            container,
            "inference",
            {
                "input": input_data,
                "model": model_name,
                "flywheel_memory": container_info["memory"][-100:]  # Last 100 memories
            }
        )
        
        # Update flywheel memory with container's output
        if response.get("update_memory", False):
            container_info["memory"].append(response["memory_update"])
            if len(container_info["memory"]) > self.config["flywheel"]["memory_size"]:
                container_info["memory"].pop(0)
        
        return response["output"]

    async def _send_container_request(
        self,
        container: Any,
        request_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send GRPC request to user container"""
        # Implementation of container communication
        # This would use GRPC to communicate with user containers
        pass