use crate::error::{Error, ErrorDetails};
use crate::inference::types::{
    ModelInferenceRequest, ModelInferenceResponse, ProviderInferenceResponse,
    ProviderInferenceResponseChunk, ProviderInferenceResponseStream,
};
use crate::inference::providers::provider_trait::InferenceProvider;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio_stream::Stream;
use futures::stream;
use uuid::Uuid;

#[derive(Debug, Clone)]
pub struct MindsDBNeuralProvider {
    pub model_name: String,
    pub url: String,
    pub history_window: u32,
    pub forecast_horizon: u32,
}

#[derive(Debug, Serialize, Deserialize)]
struct MindsDBPredictionRequest {
    data: Vec<HashMap<String, serde_json::Value>>,
    target_column: String,
}

#[derive(Debug, Deserialize)]
struct MindsDBPredictionResponse {
    prediction: Vec<f64>,
    confidence: f64,
}

impl Default for MindsDBNeuralProvider {
    fn default() -> Self {
        Self {
            model_name: String::new(),
            url: "http://localhost:47334".to_string(),
            history_window: 30,
            forecast_horizon: 7,
        }
    }
}

#[async_trait::async_trait]
impl InferenceProvider for MindsDBNeuralProvider {
    async fn infer(
        &self,
        request: &ModelInferenceRequest<'_>,
        client: &Client,
    ) -> Result<ProviderInferenceResponse, Error> {
        // Convert input to MindsDB format
        let input_data: Vec<HashMap<String, serde_json::Value>> = serde_json::from_str(request.input)?;
        
        let prediction_request = MindsDBPredictionRequest {
            data: input_data,
            target_column: request.output_schema.clone().unwrap_or_else(|| "target".to_string()),
        };

        // Make prediction request to MindsDB
        let response = client
            .post(&format!("{}/api/models/{}/predict", self.url, self.model_name))
            .json(&prediction_request)
            .send()
            .await
            .map_err(|e| Error::new(ErrorDetails::Provider {
                message: format!("MindsDB request failed: {}", e),
                provider_type: "mindsdb".to_string(),
                raw_request: Some(serde_json::to_string(&prediction_request).unwrap_or_default()),
                raw_response: None,
                status_code: None,
            }))?;

        let prediction: MindsDBPredictionResponse = response.json().await.map_err(|e| {
            Error::new(ErrorDetails::Provider {
                message: format!("Failed to parse MindsDB response: {}", e),
                provider_type: "mindsdb".to_string(),
                raw_request: Some(serde_json::to_string(&prediction_request).unwrap_or_default()),
                raw_response: Some(format!("{:?}", response)),
                status_code: Some(response.status().as_u16()),
            })
        })?;

        Ok(ProviderInferenceResponse {
            output: vec![serde_json::to_string(&prediction.prediction)?.into()],
            raw_response: serde_json::to_string(&prediction)?,
            model_provider_name: "mindsdb".into(),
            usage: Default::default(),
        })
    }

    async fn infer_stream(
        &self,
        request: &ModelInferenceRequest<'_>,
        client: &Client,
    ) -> Result<(ProviderInferenceResponseChunk, Box<dyn Stream<Item = Result<ProviderInferenceResponseChunk, Error>> + Unpin + Send>), Error> {
        // For streaming, we'll return predictions as they become available
        let response = self.infer(request, client).await?;
        
        let initial_chunk = ProviderInferenceResponseChunk {
            delta: response.output.first().cloned(),
            raw_delta: Some(response.raw_response.clone()),
            finish_reason: None,
            tool_calls: vec![],
        };

        let stream = stream::empty();
        Ok((initial_chunk, Box::new(stream)))
    }

    async fn start_batch_inference(
        &self,
        requests: &[ModelInferenceRequest<'_>],
        client: &Client,
        _api_keys: &crate::endpoints::inference::InferenceCredentials,
    ) -> Result<crate::inference::types::StartBatchProviderInferenceResponse, Error> {
        let batch_id = Uuid::now_v7();
        
        // Process each request in the batch
        let mut results = Vec::new();
        for request in requests {
            match self.infer(request, client).await {
                Ok(response) => results.push((request.inference_id, Ok(response))),
                Err(e) => results.push((request.inference_id, Err(e))),
            }
        }

        Ok(crate::inference::types::StartBatchProviderInferenceResponse {
            batch_id,
            results: results.into_iter().collect(),
        })
    }
}