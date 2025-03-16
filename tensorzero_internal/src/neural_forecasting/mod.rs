use crate::error::{Error, ErrorDetails};
use crate::inference::providers::MindsDBConfig;
use tokio::sync::Mutex;
use std::collections::HashMap;
use std::sync::Arc;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use crate::clickhouse::ClickHouseConnectionInfo;

#[derive(Debug, Serialize, Deserialize)]
pub struct TimeSeriesDataPoint {
    pub timestamp: DateTime<Utc>,
    pub value: f64,
    pub additional_features: HashMap<String, String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TimeSeriesModelConfig {
    pub model_name: String,
    pub target_column: String,
    pub history_window: u32,
    pub forecast_horizon: u32,
    pub mindsdb_url: String,
    pub additional_params: HashMap<String, String>,
}

pub struct NeuralForecastManager {
    models: Arc<Mutex<HashMap<String, MindsDBConfig>>>,
    clickhouse: ClickHouseConnectionInfo,
}

impl NeuralForecastManager {
    pub fn new(clickhouse: ClickHouseConnectionInfo) -> Self {
        Self {
            models: Arc::new(Mutex::new(HashMap::new())),
            clickhouse,
        }
    }

    pub async fn register_model(&self, name: String, config: MindsDBConfig) -> Result<(), Error> {
        let mut models = self.models.lock().await;
        models.insert(name, config);
        Ok(())
    }

    pub async fn get_model(&self, name: &str) -> Result<MindsDBConfig, Error> {
        let models = self.models.lock().await;
        models.get(name).cloned().ok_or_else(|| {
            Error::new(ErrorDetails::Generic {
                message: format!("Neural forecast model '{}' not found", name),
            })
        })
    }

    pub async fn list_models(&self) -> Vec<String> {
        let models = self.models.lock().await;
        models.keys().cloned().collect()
    }

    pub async fn create_model(&self, config: TimeSeriesModelConfig) -> Result<Uuid, Error> {
        let model_id = Uuid::now_v7();
        let row = serde_json::json!({
            "id": model_id,
            "model_name": config.model_name,
            "target_column": config.target_column,
            "history_window": config.history_window,
            "forecast_horizon": config.forecast_horizon,
            "mindsdb_url": config.mindsdb_url,
            "additional_params": config.additional_params,
            "updated_at": chrono::Utc::now()
        });

        self.clickhouse.write(&[row], "TimeSeriesModelConfig").await?;
        Ok(model_id)
    }

    pub async fn add_data_points(
        &self,
        model_id: Uuid,
        points: Vec<TimeSeriesDataPoint>,
    ) -> Result<(), Error> {
        let rows: Vec<_> = points
            .into_iter()
            .map(|point| {
                serde_json::json!({
                    "id": Uuid::now_v7(),
                    "model_id": model_id,
                    "timestamp": point.timestamp,
                    "value": point.value,
                    "additional_features": point.additional_features
                })
            })
            .collect();

        self.clickhouse.write(&rows, "TimeSeriesData").await?;
        Ok(())
    }

    pub async fn get_model_config(&self, model_id: Uuid) -> Result<TimeSeriesModelConfig, Error> {
        let query = format!(
            r#"
            SELECT
                model_name,
                target_column,
                history_window,
                forecast_horizon,
                mindsdb_url,
                additional_params
            FROM TimeSeriesModelConfig
            WHERE id = '{}'
            ORDER BY created_at DESC
            LIMIT 1
            FORMAT JSONEachRow
            "#,
            model_id
        );

        let result = self.clickhouse.run_query(query, None).await?;
        if result.is_empty() {
            return Err(Error::new(ErrorDetails::NotFound {
                message: format!("Model with ID {} not found", model_id),
            }));
        }

        serde_json::from_str(&result).map_err(|e| {
            Error::new(ErrorDetails::Serialization {
                message: format!("Failed to deserialize model config: {}", e),
            })
        })
    }

    pub async fn get_recent_forecasts(
        &self,
        model_id: Uuid,
        limit: usize,
    ) -> Result<Vec<(DateTime<Utc>, f64, f64)>, Error> {
        let query = format!(
            r#"
            SELECT
                timestamp,
                predicted_value,
                confidence
            FROM TimeSeriesForecast
            WHERE model_id = '{}'
            ORDER BY timestamp DESC
            LIMIT {}
            FORMAT JSONEachRow
            "#,
            model_id, limit
        );

        let result = self.clickhouse.run_query(query, None).await?;
        let rows: Vec<serde_json::Value> = serde_json::from_str(&result).map_err(|e| {
            Error::new(ErrorDetails::Serialization {
                message: format!("Failed to deserialize forecasts: {}", e),
            })
        })?;

        rows.into_iter()
            .map(|row| {
                let timestamp = DateTime::parse_from_rfc3339(
                    row["timestamp"]
                        .as_str()
                        .ok_or_else(|| {
                            Error::new(ErrorDetails::Serialization {
                                message: "Missing timestamp in forecast".to_string(),
                            })
                        })?,
                )
                .map_err(|e| {
                    Error::new(ErrorDetails::Serialization {
                        message: format!("Failed to parse timestamp: {}", e),
                    })
                })?
                .with_timezone(&Utc);

                let value = row["predicted_value"]
                    .as_f64()
                    .ok_or_else(|| {
                        Error::new(ErrorDetails::Serialization {
                            message: "Missing predicted_value in forecast".to_string(),
                        })
                    })?;

                let confidence = row["confidence"]
                    .as_f64()
                    .ok_or_else(|| {
                        Error::new(ErrorDetails::Serialization {
                            message: "Missing confidence in forecast".to_string(),
                        })
                    })?;

                Ok((timestamp, value, confidence))
            })
            .collect()
    }
}

impl Default for NeuralForecastManager {
    fn default() -> Self {
        Self::new(ClickHouseConnectionInfo::default())
    }
}