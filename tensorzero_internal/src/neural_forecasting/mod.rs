use crate::error::{Error, ErrorDetails};
use crate::inference::providers::MindsDBConfig;
use tokio::sync::Mutex;
use std::collections::HashMap;
use std::sync::Arc;

pub struct NeuralForecastManager {
    models: Arc<Mutex<HashMap<String, MindsDBConfig>>>,
}

impl NeuralForecastManager {
    pub fn new() -> Self {
        Self {
            models: Arc::new(Mutex::new(HashMap::new())),
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
}

impl Default for NeuralForecastManager {
    fn default() -> Self {
        Self::new()
    }
}