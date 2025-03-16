use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeuralProviderConfig {
    pub model_name: String,
    pub algorithm: NeuralAlgorithm,
    #[serde(default = "default_history_window")]
    pub history_window: u32,
    #[serde(default = "default_forecast_horizon")] 
    pub forecast_horizon: u32,
    #[serde(default = "HashMap::new")]
    pub algorithm_params: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NeuralAlgorithm {
    AutoML,
    DeepLearning,
    GBM,
    GLM,
    DRF,
    XGBoost,
    GAM,
    StackedEnsemble,
    DecisionTree,
    SVM,
    NaiveBayes,
}

fn default_history_window() -> u32 {
    30 // Default 30 day history window
}

fn default_forecast_horizon() -> u32 {
    7 // Default 7 day forecast horizon
}