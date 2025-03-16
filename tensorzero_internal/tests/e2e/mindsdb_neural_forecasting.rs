use std::collections::HashMap;
use chrono::{DateTime, TimeZone, Utc};
use uuid::Uuid;
use tensorzero_internal::{
    clickhouse::ClickHouseConnectionInfo,
    inference::providers::{MindsDBNeuralProvider, InferenceProvider},
    inference::types::{ModelInferenceRequest, InferenceType, ModelInferenceRequestJsonMode},
    neural_forecasting::{NeuralForecastManager, TimeSeriesDataPoint, TimeSeriesModelConfig},
    error::Error,
    cache::{CacheParamsOptions, CacheEnabledMode},
};

#[tokio::test]
async fn test_neural_forecasting_e2e() -> Result<(), Error> {
    // Set up test environment
    let clickhouse = ClickHouseConnectionInfo::default();
    let manager = NeuralForecastManager::new(clickhouse.clone());

    // Create test model config
    let model_config = TimeSeriesModelConfig {
        model_name: "test_forecast_model".to_string(),
        target_column: "value".to_string(),
        history_window: 30,
        forecast_horizon: 7,
        mindsdb_url: "http://localhost:47334".to_string(),
        additional_params: HashMap::new(),
    };

    // Register the model
    let model_id = manager.create_model(model_config.clone()).await?;

    // Create test data points
    let mut points = Vec::new();
    let base_time = Utc.with_ymd_and_hms(2024, 1, 1, 0, 0, 0).unwrap();
    
    for i in 0..30 {
        points.push(TimeSeriesDataPoint {
            timestamp: base_time + chrono::Duration::hours(i),
            value: i as f64,
            additional_features: HashMap::new(),
        });
    }

    // Add data points
    manager.add_data_points(model_id, points.clone()).await?;

    // Set up MindsDB provider
    let provider = MindsDBNeuralProvider {
        model_name: model_config.model_name.clone(),
        url: model_config.mindsdb_url.clone(),
        history_window: model_config.history_window,
        forecast_horizon: model_config.forecast_horizon,
    };

    // Create inference request
    let input_data = points.iter().map(|p| {
        serde_json::json!({
            "timestamp": p.timestamp.to_rfc3339(),
            "value": p.value,
        })
    }).collect::<Vec<_>>();

    let inference_id = Uuid::now_v7();
    let request = ModelInferenceRequest {
        inference_id,
        input: &serde_json::to_string(&input_data)?,
        output_schema: Some(model_config.target_column.clone()),
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
        json_mode: ModelInferenceRequestJsonMode::Off,
        function_type: InferenceType::Neural,
        clickhouse: Some(clickhouse.clone()),
        inference_params: Default::default(),
    };

    // First request - should not be cached
    let client = reqwest::Client::new();
    let response = provider.infer(&request, &client).await;

    // Should fail since we don't have a real MindsDB server in test
    assert!(response.is_err());
    assert!(response.unwrap_err().to_string().contains("MindsDB request failed"));

    // Test cache operations
    let cache_options = CacheParamsOptions {
        max_age_s: Some(3600),
        enabled: CacheEnabledMode::On,
    };

    // Mock a successful response and write it to cache
    let mock_response = serde_json::json!({
        "prediction": [25.3, 26.1, 27.4, 26.8, 28.2, 27.9, 29.1],
        "confidence": 0.89
    });

    // Write to cache
    clickhouse
        .write(
            &[serde_json::json!({
                "short_cache_key": 12345,
                "long_cache_key": "test_key",
                "inference_id": inference_id,
                "raw_request": serde_json::to_string(&input_data)?,
                "raw_response": mock_response.to_string(),
                "model_name": model_config.model_name,
                "model_provider_name": "mindsdb",
                "prediction": mock_response["prediction"],
                "confidence": mock_response["confidence"],
                "timestamp": chrono::Utc::now()
            })],
            "ModelInferenceCache",
        )
        .await?;

    // Verify cached forecast results
    let forecasts = manager.get_recent_forecasts(model_id, 7).await?;
    assert_eq!(forecasts.len(), 7);

    // Verify the cached values match our mock response
    let mock_predictions: Vec<f64> = serde_json::from_value(mock_response["prediction"].clone())?;
    for (i, (_, value, confidence)) in forecasts.iter().enumerate() {
        assert_eq!(*value, mock_predictions[i]);
        assert_eq!(*confidence, mock_response["confidence"].as_f64().unwrap());
    }

    Ok(())
}

#[tokio::test]
async fn test_neural_forecast_cache_key_generation() -> Result<(), Error> {
    let model_name = "test_model";
    let provider_name = "mindsdb";
    let target_column = "value";
    let history_window = 30;
    
    // Create two identical sets of data
    let data1 = vec![
        serde_json::json!({"timestamp": "2024-01-01T00:00:00Z", "value": 1.0}),
        serde_json::json!({"timestamp": "2024-01-01T01:00:00Z", "value": 2.0}),
    ];
    
    let data2 = data1.clone();

    let mut data_hasher = blake3::Hasher::new();
    for point in &data1 {
        data_hasher.update(point.to_string().as_bytes());
    }
    let data_hash = data_hasher.finalize();

    // Generate cache keys
    let key1 = CacheKey::from_neural_data(
        model_name,
        provider_name,
        target_column,
        history_window,
        data_hash.as_bytes(),
    );

    let mut data_hasher = blake3::Hasher::new();
    for point in &data2 {
        data_hasher.update(point.to_string().as_bytes());
    }
    let data_hash = data_hasher.finalize();

    let key2 = CacheKey::from_neural_data(
        model_name,
        provider_name,
        target_column,
        history_window,
        data_hash.as_bytes(),
    );

    // Keys should match for identical data
    assert_eq!(key1, key2);

    // Change a value and verify key changes
    let data3 = vec![
        serde_json::json!({"timestamp": "2024-01-01T00:00:00Z", "value": 1.0}),
        serde_json::json!({"timestamp": "2024-01-01T01:00:00Z", "value": 3.0}), // Changed value
    ];

    let mut data_hasher = blake3::Hasher::new();
    for point in &data3 {
        data_hasher.update(point.to_string().as_bytes());
    }
    let data_hash = data_hasher.finalize();

    let key3 = CacheKey::from_neural_data(
        model_name,
        provider_name,
        target_column,
        history_window,
        data_hash.as_bytes(),
    );

    // Key should be different for different data
    assert_ne!(key1, key3);

    Ok(())
}

#[tokio::test]
async fn test_neural_forecast_cache_invalidation() -> Result<(), Error> {
    let clickhouse = ClickHouseConnectionInfo::default();
    let manager = NeuralForecastManager::new(clickhouse.clone());

    // Create test model config
    let model_config = TimeSeriesModelConfig {
        model_name: "test_forecast_model".to_string(),
        target_column: "value".to_string(),
        history_window: 30,
        forecast_horizon: 7,
        mindsdb_url: "http://localhost:47334".to_string(),
        additional_params: HashMap::new(),
    };

    let model_id = manager.create_model(model_config.clone()).await?;

    // Create and cache some test forecasts
    let mock_forecasts = vec![
        (DateTime::from_timestamp(1704067200, 0).unwrap(), 25.3, 0.89),
        (DateTime::from_timestamp(1704070800, 0).unwrap(), 26.1, 0.89),
        (DateTime::from_timestamp(1704074400, 0).unwrap(), 27.4, 0.89),
    ];

    for (timestamp, value, confidence) in &mock_forecasts {
        let forecast = serde_json::json!({
            "id": Uuid::now_v7(),
            "model_id": model_id,
            "timestamp": timestamp,
            "target_column": model_config.target_column,
            "predicted_value": value,
            "confidence": confidence,
        });

        clickhouse
            .write(&[forecast], "TimeSeriesForecast")
            .await?;
    }

    // Verify forecasts are in cache
    let cached_forecasts = manager.get_recent_forecasts(model_id, 3).await?;
    assert_eq!(cached_forecasts.len(), 3);
    for (i, (timestamp, value, confidence)) in cached_forecasts.iter().enumerate() {
        assert_eq!(*timestamp, mock_forecasts[i].0);
        assert_eq!(*value, mock_forecasts[i].1);
        assert_eq!(*confidence, mock_forecasts[i].2);
    }

    // Test cache invalidation by time
    let outdated_forecasts = manager
        .get_recent_forecasts_with_max_age(model_id, 3, chrono::Duration::hours(1))
        .await?;
    assert!(outdated_forecasts.is_empty());

    Ok(())
}