# TensorZero Python Client

**[Website](https://www.tensorzero.com/)** ·
**[Docs](https://www.tensorzero.com/docs)** ·
**[Twitter](https://www.x.com/tensorzero)** ·
**[Slack](https://www.tensorzero.com/slack)** ·
**[Discord](https://www.tensorzero.com/discord)**

**[Quick Start (5min)](https://www.tensorzero.com/docs/gateway/tutorial)** ·
**[Comprehensive Tutorial](https://www.tensorzero.com/docs/gateway/tutorial)** ·
**[Deployment Guide](https://www.tensorzero.com/docs/gateway/deployment)** ·
**[API Reference](https://www.tensorzero.com/docs/gateway/api-reference)** ·
**[Configuration Reference](https://www.tensorzero.com/docs/gateway/deployment)**

The `tensorzero` package provides an async Python client for the TensorZero Gateway.
This client allows you to easily make inference requests and assign feedback to them via the gateway.

See our **[API Reference](https://www.tensorzero.com/docs/gateway/api-reference)** for more information.

## Installation

```bash
pip install tensorzero
```

## Basic Usage

### Non-Streaming Inference

```python
import asyncio

from tensorzero import AsyncTensorZeroGateway


async def run(topic):
    async with AsyncTensorZeroGateway("http://localhost:3000") as client:
        result = await client.inference(
            function_name="generate_haiku",
            input={
                "messages": [
                    {"role": "user", "content": {"topic": topic}},
                ],
            },
        )

        print(result)


if __name__ == "__main__":
    asyncio.run(run("artificial intelligence"))
```

### Streaming Inference

```python
import asyncio

from tensorzero import AsyncTensorZeroGateway


async def run(topic):
    async with AsyncTensorZeroGateway("http://localhost:3000") as client:
        stream = await client.inference(
            function_name="generate_haiku",
            input={
                "messages": [
                    {"role": "user", "content": {"topic": topic}},
                ],
            },
            stream=True,
        )

        async for chunk in stream:
            print(chunk)


if __name__ == "__main__":
    asyncio.run(run("artificial intelligence"))

```

### Feedback

```python
import asyncio

from tensorzero import AsyncTensorZeroGateway


async def run(inference_id):
    async with AsyncTensorZeroGateway("http://localhost:3000") as client:
        result = await client.feedback(
            metric_name="thumbs_up",
            inference_id=inference_id,
            value=True,  # 👍
        )

        print(result)


if __name__ == "__main__":
    asyncio.run(run("00000000-0000-0000-0000-000000000000"))
```

## Integrating MindsDB with TensorZero

To integrate MindsDB with TensorZero, follow these steps:

1. Ensure you have both MindsDB and TensorZero installed and running.
2. Use the `AsyncTensorZeroGateway` or `TensorZeroGateway` classes from the `tensorzero` Python package to interact with TensorZero.
3. Create a MindsDB model and deploy it.
4. Use the TensorZero client to send inference requests to the MindsDB model.

## Creating a Virtual Environment and Installing Dependencies

To create a virtual environment and install dependencies, follow these steps:

1. Create a virtual environment using `venv`:

```bash
python -m venv venv
```

2. Activate the virtual environment:

```bash
# On Windows
venv\Scripts\activate

# On macOS and Linux
source venv/bin/activate
```

3. Install the required dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Setting Up the Gateway

To set up the gateway using `AsyncTensorZeroGateway` or `TensorZeroGateway`, follow these steps:

1. Use the `AsyncTensorZeroGateway` or `TensorZeroGateway` classes from the `tensorzero` Python package to interact with TensorZero.
2. Ensure that the gateway is properly configured and running.

## Automating the Build Process

To automate the build process, follow these steps:

1. Develop a script that automates the build process, including dependency installation, code compilation, testing, and deployment. You can use tools like `Makefile`, `shell scripts`, or CI/CD pipelines.
2. Use continuous integration and continuous deployment (CI/CD) tools like GitHub Actions, Jenkins, or GitLab CI to automate the build process. You can find existing workflows in the `.github/workflows` directory, such as `.github/workflows/general.yml` and `.github/workflows/merge-queue.yml`.

## Setting Up CI/CD Pipelines

To set up CI/CD pipelines, follow these steps:

1. Use continuous integration and continuous deployment (CI/CD) tools like GitHub Actions, Jenkins, or GitLab CI to automate the build process.
2. You can find existing workflows in the `.github/workflows` directory, such as `.github/workflows/general.yml` and `.github/workflows/merge-queue.yml`.
