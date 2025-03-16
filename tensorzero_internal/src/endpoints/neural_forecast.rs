use crate::error::Error;
use crate::inference::providers::MindsDBConfig;
use crate::Gateway;
use axum::{
    extract::{Path, State},
    routing::{get, post},
    Json, Router,
};
use std::sync::Arc;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateModelRequest {
    pub name: String,
    pub config: MindsDBConfig,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ForecastRequest {
    pub data: Vec<serde_json::Value>,
    pub target_column: String,
}

#[derive(Debug, Serialize)]
pub struct ForecastResponse {
    pub prediction: Vec<f64>,
    pub confidence: f64,
}

pub fn router() -> Router<Arc<Gateway>> {
    Router::new()
        .route("/models", post(create_model))
        .route("/models", get(list_models))
        .route("/models/:name/forecast", post(forecast))
}

async fn create_model(
    State(gateway): State<Arc<Gateway>>,
    Json(request): Json<CreateModelRequest>,
) -> Result<Json<()>, Error> {
    gateway.neural_forecast_manager.register_model(request.name, request.config).await?;
    Ok(Json(()))
}

async fn list_models(
    State(gateway): State<Arc<Gateway>>,
) -> Result<Json<Vec<String>>, Error> {
    let models = gateway.neural_forecast_manager.list_models().await;
    Ok(Json(models))
}

async fn forecast(
    State(gateway): State<Arc<Gateway>>,
    Path(name): Path<String>,
    Json(request): Json<ForecastRequest>,
) -> Result<Json<ForecastResponse>, Error> {
    let model_config = gateway.neural_forecast_manager.get_model(&name).await?;
    
    let inference_request = crate::inference::types::ModelInferenceRequest {
        inference_id: Uuid::now_v7(),
        function_name: "forecast".into(),
        variant_name: name.clone().into(),
        input: &serde_json::to_string(&request.data)?,
        output_schema: Some(request.target_column),
        episode_id: None,
        tool_params: None,
        inference_params: None,
        tags: None,
    };

    let provider = crate::inference::providers::MindsDBNeuralProvider {
        model_name: model_config.model_name,
        url: model_config.url,
        history_window: model_config.history_window,
        forecast_horizon: model_config.forecast_horizon,
    };

    let client = reqwest::Client::new();
    let response = provider.infer(&inference_request, &client).await?;
    
    let prediction: Vec<f64> = serde_json::from_str(&response.output[0])?;
    let full_response: serde_json::Value = serde_json::from_str(&response.raw_response)?;
    let confidence = full_response.get("confidence")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);

    Ok(Json(ForecastResponse {
        prediction,
        confidence,
    }))
}