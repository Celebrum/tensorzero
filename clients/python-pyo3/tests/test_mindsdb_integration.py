import unittest
from tensorzero import AsyncTensorZeroGateway, TensorZeroGateway
import mindsdb_sdk
import asyncio

class TestMindsDBIntegration(unittest.TestCase):

    def setUp(self):
        self.mindsdb_url = "http://localhost:47334"
        self.tensorzero_url = "http://localhost:3000"
        self.model_name = "test_model"
        self.training_data = {
            "feature1": [1.0, 2.0, 3.0],
            "feature2": [4.0, 5.0, 6.0],
            "target": [7.0, 8.0, 9.0]
        }
        self.input_data = {
            "feature1": [1.5, 2.5],
            "feature2": [4.5, 5.5]
        }

    def test_create_and_deploy_mindsdb_model(self):
        client = mindsdb_sdk.Client(self.mindsdb_url)
        model = client.create_model(self.model_name, self.training_data)
        model.deploy()
        self.assertTrue(model.is_deployed())

    def test_inference_with_mindsdb_model(self):
        async def run_inference():
            async with AsyncTensorZeroGateway(self.tensorzero_url) as client:
                result = await client.integrate_mindsdb(
                    mindsdb_url=self.mindsdb_url,
                    model_name=self.model_name,
                    input_data=self.input_data
                )
                return result

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(run_inference())
        self.assertIn("target", result)
        self.assertEqual(len(result["target"]), len(self.input_data["feature1"]))

if __name__ == "__main__":
    unittest.main()
