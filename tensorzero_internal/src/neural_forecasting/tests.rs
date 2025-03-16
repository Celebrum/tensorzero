#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{TimeZone, Utc};
    use std::collections::HashMap;
    use uuid::Uuid;

    fn create_test_data_points() -> Vec<TimeSeriesDataPoint> {
        let mut points = Vec::new();
        let base_time = Utc.with_ymd_and_hms(2024, 1, 1, 0, 0, 0).unwrap();
        
        for i in 0..10 {
            points.push(TimeSeriesDataPoint {
                timestamp: base_time + chrono::Duration::hours(i),
                value: i as f64,
                additional_features: HashMap::new(),
            });
        }
        points
    }

    fn create_test_model_config() -> TimeSeriesModelConfig {
        TimeSeriesModelConfig {
            model_name: "test_model".to_string(),
            target_column: "value".to_string(),
            history_window: 24,
            forecast_horizon: 12,
            mindsdb_url: "http://localhost:47334".to_string(),
            additional_params: HashMap::new(),
        }
    }

    #[tokio::test]
    async fn test_create_model() {
        let manager = NeuralForecastManager::new(ClickHouseConnectionInfo::default());
        let config = create_test_model_config();
        let model_id = manager.create_model(config.clone()).await.unwrap();
        
        let retrieved_config = manager.get_model_config(model_id).await.unwrap();
        assert_eq!(retrieved_config.model_name, config.model_name);
        assert_eq!(retrieved_config.target_column, config.target_column);
        assert_eq!(retrieved_config.history_window, config.history_window);
        assert_eq!(retrieved_config.forecast_horizon, config.forecast_horizon);
    }

    #[tokio::test]
    async fn test_add_data_points() {
        let manager = NeuralForecastManager::new(ClickHouseConnectionInfo::default());
        let model_id = Uuid::now_v7();
        let points = create_test_data_points();
        
        manager.add_data_points(model_id, points.clone()).await.unwrap();
        
        // Verify points were added by querying recent forecasts
        let retrieved = manager.get_recent_forecasts(model_id, points.len()).await.unwrap();
        assert_eq!(retrieved.len(), points.len());
        
        for (i, (timestamp, value, _)) in retrieved.iter().enumerate() {
            assert_eq!(timestamp.timestamp(), points[i].timestamp.timestamp());
            assert_eq!(*value, points[i].value);
        }
    }

    #[tokio::test]
    async fn test_mindsdb_provider() {
        use crate::inference::providers::{MindsDBNeuralProvider, InferenceProvider};
        use crate::inference::types::ModelInferenceRequest;

        let provider = MindsDBNeuralProvider {
            model_name: "test_model".to_string(),
            url: "http://localhost:47334".to_string(),
            history_window: 24,
            forecast_horizon: 12,
        };

        let input_data = vec![
            serde_json::json!({
                "timestamp": "2024-01-01T00:00:00Z",
                "value": 1.0,
            }),
            serde_json::json!({
                "timestamp": "2024-01-01T01:00:00Z",
                "value": 2.0,
            }),
        ];

        let request = ModelInferenceRequest {
            inference_id: Uuid::now_v7(),
            input: &serde_json::to_string(&input_data).unwrap(),
            output_schema: Some("value".to_string()),
            messages: vec![],
            system: None,
            tool_config: None,
            temperature: None,
            top_p: None,
            presence_penalty: None,
            frequency_penalty: None,
            max_tokens: None,
            seed: None,
            stream: false,
            json_mode: crate::inference::types::ModelInferenceRequestJsonMode::Off,
            function_type: crate::inference::types::FunctionType::Chat,
            clickhouse: Some(ClickHouseConnectionInfo::default()),
        };

        let client = reqwest::Client::new();
        let response = provider.infer(&request, &client).await;
        
        // Since this is a test, we expect it to fail due to no MindsDB server
        // but we verify the error handling works as expected
        assert!(response.is_err());
        match response {
            Err(e) => {
                assert!(e.to_string().contains("MindsDB request failed"));
            }
            _ => panic!("Expected error"),
        }
    }
}