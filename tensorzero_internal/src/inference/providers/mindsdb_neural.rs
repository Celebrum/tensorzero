use std::collections::HashMap;
use async_stream::stream;
use reqwest::Client;
use secrecy::ExposeSecret;
use serde::{Deserialize, Serialize};
use tokio_stream::Stream;
use uuid::Uuid;

use crate::{
    error::{Error, ErrorDetails},
    inference::types::{
        batch::StartBatchProviderInferenceResponse, ContentBlock, ModelInferenceRequest,
        ProviderInferenceResponse, ProviderInferenceResponseChunk,
    },
    endpoints::inference::InferenceCredentials,
};

use super::provider_trait::InferenceProvider;

#[derive(Debug, Serialize, Deserialize)]
pub struct MindsDBNeuralProvider {
    pub model_name: String,
    pub url: String,
    pub history_window: u32,
    pub forecast_horizon: u32,
}

#[derive(Debug, Serialize)]
struct MindsDBPredictionRequest {
    data: Vec<HashMap<String, serde_json::Value>>,
    target_column: String,
}

#[derive(Debug, Deserialize)]
struct MindsDBPredictionResponse {
    prediction: Vec<f64>,
    confidence: f64,
}

#[async_trait::async_trait]
impl InferenceProvider for MindsDBNeuralProvider {
    async fn infer(
        &self,
        request: &ModelInferenceRequest<'_>,
        client: &Client,
    ) -> Result<ProviderInferenceResponse, Error> {
        let input_data: Vec<HashMap<String, serde_json::Value>> = serde_json::from_str(request.input)?;
        
        let target_column = request.output_schema.clone().unwrap_or_else(|| "target".to_string());
        
        let prediction_request = MindsDBPredictionRequest {
            data: input_data,
            target_column: target_column.clone(),
        };

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

        // Store the forecast in ClickHouse
        if let Some(clickhouse) = &request.clickhouse {
            let forecast_rows: Vec<_> = prediction.prediction.iter().enumerate().map(|(i, &value)| {
                serde_json::json!({
                    "id": Uuid::now_v7(),
                    "model_id": request.inference_id,
                    "timestamp": chrono::Utc::now() + chrono::Duration::hours(i as i64),
                    "target_column": target_column,
                    "predicted_value": value,
                    "confidence": prediction.confidence
                })
            }).collect();
            
            tokio::spawn(async move {
                if let Err(e) = clickhouse.write(&forecast_rows, "TimeSeriesForecast").await {
                    tracing::error!("Failed to store forecast in ClickHouse: {}", e);
                }
            });
        }

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
        _api_keys: &InferenceCredentials,
    ) -> Result<StartBatchProviderInferenceResponse, Error> {
        let batch_id = Uuid::now_v7();
        
        // Process each request in the batch
        let mut results = Vec::new();
        for request in requests {
            match self.infer(request, client).await {
                Ok(response) => results.push((request.inference_id, Ok(response))),
                Err(e) => results.push((request.inference_id, Err(e))),
            }
        }

        Ok(StartBatchProviderInferenceResponse {
            batch_id,
            results: results.into_iter().collect(),
        })
    }
}