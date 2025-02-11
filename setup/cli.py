import os
import sys
import panel as pn
import param
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import click
import yaml
from .model_env_manager import ModelEnvironmentManager
from .init_model_env import init_model_environment, validate_environment

class ModelConfig(param.Parameterized):
    architecture = param.String(default="x10 -> Linear(20) -> ReLU -> Linear(1)", doc="Model architecture")
    learning_rate = param.Number(default=0.01, bounds=(0.0001, 1.0), doc="Learning rate")
    memory_size = param.Integer(default=1000, bounds=(100, 10000), doc="Memory size for intelligence")
    intelligence_factor = param.Number(default=0.5, bounds=(0, 1), doc="Intelligence injection factor")

def setup_environment():
    """Set up the development environment"""
    # Create virtual environment
    if not os.path.exists(".venv"):
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
    
    # Set environment variables
    env_path = Path(".env")
    if not env_path.exists():
        with env_path.open("w") as f:
            f.write(f"CARGO_HOME={os.path.abspath('.cargo')}\n")
            f.write("RUST_LOG=info\n")
    
    # Load environment variables
    load_dotenv()
    
    # Install dependencies using the activated environment
    python_path = ".venv/Scripts/python" if os.name == "nt" else ".venv/bin/python"
    subprocess.run([python_path, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Install Rust if not present
    if not os.system("rustc --version") == 0:
        if os.name == "nt":
            os.system("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
        else:
            os.system("curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")

def create_ui():
    """Create Panel UI for model configuration"""
    config = ModelConfig()
    
    # Create widgets
    arch_input = pn.widgets.TextInput.from_param(config.param.architecture)
    lr_input = pn.widgets.NumberInput.from_param(config.param.learning_rate)
    memory_input = pn.widgets.IntInput.from_param(config.param.memory_size)
    intel_input = pn.widgets.NumberInput.from_param(config.param.intelligence_factor)
    
    def on_submit(event):
        """Handle form submission"""
        from tensorzero.mindsdb_gateway import MindsDBGateway
        gateway = MindsDBGateway()
        
        # Create model with specified configuration
        model_config = {
            "architecture": config.architecture,
            "learning_rate": config.learning_rate,
            "memory_size": config.memory_size,
            "intelligence_factor": config.intelligence_factor
        }
        gateway.create_model("model_" + str(hash(str(model_config)))[:8], model_config)
        
    submit_button = pn.widgets.Button(name="Create Model", button_type="primary")
    submit_button.on_click(on_submit)
    
    # Layout
    return pn.Column(
        "## TensorZero Model Configuration",
        arch_input,
        lr_input,
        memory_input,
        intel_input,
        submit_button
    )

@click.group()
def cli():
    """TensorZero model environment management CLI"""
    pass

@cli.command()
@click.argument('model_name')
@click.option('--architecture', '-a', help='Model architecture description')
@click.option('--gpu/--no-gpu', default=False, help='Whether GPU support is required')
@click.option('--model-size', type=click.Choice(['small', 'medium', 'large']), default='small')
def create(model_name, architecture, gpu, model_size):
    """Create a new model environment"""
    env_manager = ModelEnvironmentManager()
    try:
        env_name = env_manager.create_model_environment(
            model_name,
            {
                "architecture": architecture,
                "gpu_required": gpu,
                "model_size": model_size
            }
        )
        click.echo(f"Created environment: {env_name}")
    except Exception as e:
        click.echo(f"Error creating environment: {e}", err=True)

@cli.command()
@click.argument('model_name')
def activate(model_name):
    """Activate an existing model environment"""
    env_manager = ModelEnvironmentManager()
    try:
        env_manager.activate_model_environment(model_name)
        click.echo(f"Activated environment for model: {model_name}")
    except Exception as e:
        click.echo(f"Error activating environment: {e}", err=True)

@cli.command()
@click.argument('model_name')
def cleanup(model_name):
    """Remove a model environment"""
    env_manager = ModelEnvironmentManager()
    try:
        env_manager.cleanup_environment(model_name)
        click.echo(f"Cleaned up environment for model: {model_name}")
    except Exception as e:
        click.echo(f"Error cleaning up environment: {e}", err=True)

@cli.command()
def list_envs():
    """List all TensorZero model environments"""
    result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
    envs = [line for line in result.stdout.split('\n') if 'tensorzero_' in line]
    click.echo("TensorZero Model Environments:")
    for env in envs:
        click.echo(f"  {env}")

def main():
    cli()

if __name__ == "__main__":
    main()