use std::time::Duration;

use crate::clickhouse::ClickHouseConnectionInfo;
use crate::clickhouse_migration_manager::migration_trait::Migration;
use crate::error::{Error, ErrorDetails};

use super::check_table_exists;

/// This migration adds support for MindsDB neural forecasting by creating the necessary tables
/// and materialized views for storing time series data and forecasts.
pub struct Migration0012<'a> {
    pub clickhouse: &'a ClickHouseConnectionInfo,
    pub clean_start: bool,
}

impl Migration for Migration0012<'_> {
    async fn can_apply(&self) -> Result<(), Error> {
        self.clickhouse.health().await.map_err(|e| {
            Error::new(ErrorDetails::ClickHouseMigration {
                id: "0012".to_string(),
                message: e.to_string(),
            })
        })
    }

    async fn should_apply(&self) -> Result<bool, Error> {
        let tables = vec![
            "TimeSeriesData",
            "TimeSeriesForecast",
            "TimeSeriesModelConfig",
        ];
        
        for table in tables {
            if !check_table_exists(self.clickhouse, table, "0012").await? {
                return Ok(true);
            }
        }

        Ok(false)
    }

    async fn apply(&self) -> Result<(), Error> {
        // Only gets used when we are not doing a clean start
        let view_offset = Duration::from_secs(15);
        let view_timestamp = (std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|e| {
                Error::new(ErrorDetails::ClickHouseMigration {
                    id: "0012".to_string(),
                    message: e.to_string(),
                })
            })?
            + view_offset)
            .as_secs();

        // Create the TimeSeriesData table for storing training data
        let query = r#"
            CREATE TABLE IF NOT EXISTS TimeSeriesData
            (
                id UUID, -- must be a UUIDv7
                model_id UUID, -- must be a UUIDv7
                timestamp DateTime64(3),
                target_column String,
                value Float64,
                additional_features Map(String, String),
                created_at DateTime MATERIALIZED UUIDv7ToDateTime(id)
            ) ENGINE = MergeTree()
            ORDER BY (model_id, timestamp);
        "#;
        let _ = self.clickhouse.run_query(query.to_string(), None).await?;

        // Create the TimeSeriesForecast table for storing predictions
        let query = r#"
            CREATE TABLE IF NOT EXISTS TimeSeriesForecast
            (
                id UUID, -- must be a UUIDv7
                model_id UUID, -- must be a UUIDv7
                timestamp DateTime64(3),
                target_column String,
                predicted_value Float64,
                confidence Float64,
                created_at DateTime MATERIALIZED UUIDv7ToDateTime(id)
            ) ENGINE = MergeTree()
            ORDER BY (model_id, timestamp);
        "#;
        let _ = self.clickhouse.run_query(query.to_string(), None).await?;

        // Create the TimeSeriesModelConfig table for storing model configurations
        let query = r#"
            CREATE TABLE IF NOT EXISTS TimeSeriesModelConfig
            (
                id UUID, -- must be a UUIDv7
                model_name String,
                target_column String,
                history_window UInt32,
                forecast_horizon UInt32,
                mindsdb_url String,
                additional_params Map(String, String),
                created_at DateTime MATERIALIZED UUIDv7ToDateTime(id),
                updated_at DateTime
            ) ENGINE = MergeTree()
            ORDER BY (model_name, id);
        "#;
        let _ = self.clickhouse.run_query(query.to_string(), None).await?;

        // Create materialized view for TimeSeriesDataByModel
        let view_where_clause = if !self.clean_start {
            format!("WHERE UUIDv7ToDateTime(id) >= toDateTime(toUnixTimestamp({view_timestamp}))")
        } else {
            String::new()
        };

        let query = format!(
            r#"
            CREATE MATERIALIZED VIEW IF NOT EXISTS TimeSeriesDataByModelView
            TO TimeSeriesData
            AS
            SELECT
                id,
                model_id,
                timestamp,
                target_column,
                value,
                additional_features
            FROM TimeSeriesData
            {view_where_clause}
            "#
        );
        let _ = self.clickhouse.run_query(query, None).await?;

        Ok(())
    }

    fn rollback_instructions(&self) -> String {
        r#"
        DROP TABLE IF EXISTS TimeSeriesData;
        DROP TABLE IF EXISTS TimeSeriesForecast;
        DROP TABLE IF EXISTS TimeSeriesModelConfig;
        DROP VIEW IF EXISTS TimeSeriesDataByModelView;
        "#
        .to_string()
    }

    async fn has_succeeded(&self) -> Result<bool, Error> {
        let should_apply = self.should_apply().await?;
        Ok(!should_apply)
    }
}