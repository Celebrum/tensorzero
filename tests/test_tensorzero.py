import os
import pytest
import pandas as pd
from openpyxl import Workbook
from tensorzero.client import AsyncTensorZeroGateway, TensorZeroGateway

# Create a virtual environment
os.system("python -m venv .venv")

# Activate the virtual environment
if os.name == "nt":
    os.system(".venv\\Scripts\\activate")
else:
    os.system("source .venv/bin/activate")

# Install dependencies
os.system("pip install -r requirements.txt")

# Define the test cases
@pytest.mark.asyncio
async def test_async_inference():
    async with AsyncTensorZeroGateway("http://localhost:3000") as client:
        input_data = {
            "system": {"assistant_name": "Alfred Pennyworth"},
            "messages": [{"role": "user", "content": "Hello"}],
        }
        result = await client.inference(function_name="basic_test", input=input_data)
        assert result.variant_name == "test"
        assert result.content[0].text == "Expected response text"

def test_sync_inference():
    with TensorZeroGateway("http://localhost:3000") as client:
        input_data = {
            "system": {"assistant_name": "Alfred Pennyworth"},
            "messages": [{"role": "user", "content": "Hello"}],
        }
        result = client.inference(function_name="basic_test", input=input_data)
        assert result.variant_name == "test"
        assert result.content[0].text == "Expected response text"

# Run the tests and capture the output
def run_tests():
    result = pytest.main(["-v", "--tb=short", "--disable-warnings", "--maxfail=1"])
    return result

# Write the test results to an Excel workbook
def write_results_to_excel(results):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Test Results"

    # Write the headers
    headers = ["Test Case", "Result"]
    sheet.append(headers)

    # Write the results
    for test_case, result in results.items():
        sheet.append([test_case, result])

    # Save the workbook
    workbook.save("test_results.xlsx")

if __name__ == "__main__":
    test_results = run_tests()
    write_results_to_excel(test_results)
