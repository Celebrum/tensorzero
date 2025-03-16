pub mod anthropic;
pub mod aws_bedrock;
pub mod azure;
#[cfg(test)]
pub mod common;
#[cfg(any(test, feature = "e2e_tests"))]
pub mod dummy;
pub mod fireworks;
pub mod gcp_vertex_anthropic;
pub mod gcp_vertex_gemini;
pub mod google_ai_studio_gemini;
pub mod hyperbolic;
pub mod mindsdb_neural;
pub mod mistral;
pub mod openai;
pub mod provider_trait;
pub mod sglang;
pub mod tgi;
pub mod together;
pub mod vllm;
pub mod xai;

use self::mindsdb_neural::MindsDBNeuralProvider;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum ProviderConfig {
    MindsDB(MindsDBConfig),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MindsDBConfig {
    pub model_name: String,
    #[serde(default = "default_mindsdb_url")]
    pub url: String,
    #[serde(default = "default_history_window")]
    pub history_window: u32,
    #[serde(default = "default_forecast_horizon")]
    pub forecast_horizon: u32,
}

fn default_mindsdb_url() -> String {
    "http://localhost:47334".to_string()
}

fn default_history_window() -> u32 {
    30
}

fn default_forecast_horizon() -> u32 {
    7
}

impl From<MindsDBConfig> for Box<dyn InferenceProvider> {
    fn from(config: MindsDBConfig) -> Self {
        Box::new(MindsDBNeuralProvider {
            model_name: config.model_name,
            url: config.url,
            history_window: config.history_window,
            forecast_horizon: config.forecast_horizon,
        })
    }
}
