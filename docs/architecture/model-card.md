# EdgeSentinel Anomaly Detection Model Card

## Model Details
- **Model Name:** IsolationForest_AnomalyDetector
- **Algorithm:** Isolation Forest (scikit-learn)
- **Version:** v1.0.0 (loaded via `MODEL_VERSION` environment variable)
- **Purpose:** Identifies anomalous telemetry readings (temperature, humidity, vibration, pressure) indicative of equipment malfunction at the edge.

## Intended Use
- **Primary Use Case:** Real-time stream processing on Edge Nodes.
- **Out-of-Scope:** This model is not intended for predictive maintenance (time-to-failure), as it does not analyze temporal sequences or trends.

## Training Data
- **Source:** Synthetic Baseline Data (Generated via `ml/train_model.py`)
- **Distribution:**
  - Temperature: Normal(μ=25.0, σ=2.0)
  - Humidity: Normal(μ=50.0, σ=5.0)
  - Vibration: Normal(μ=0.5, σ=0.1)
  - Pressure: Normal(μ=1013.25, σ=5.0)
- **Sample Size:** 5,000 synthetic observations.

## Evaluation & Thresholds
- The model outputs an anomaly score (lower is more anomalous).
- **Thresholds:**
  - `WARNING`: Score between `-0.1` and `-0.2`
  - `CRITICAL`: Score `<= -0.2`
- These thresholds are stored alongside the model artifact in `metadata_v1.0.0.json`.

## Expected Limitations & Errors
- **False Positives:** Will occur if equipment naturally operates outside the tight synthetic baseline ranges (e.g., a machine that runs at 40°C normally).
- **False Negatives:** Slow, creeping degradation (e.g., temperature slowly rising over weeks but staying within bounds) will not be flagged until it crosses the threshold.

## Rollback Procedure
The Edge Node loads the model dynamically from the disk mount.
To roll back to a previous model (e.g., `v0.9.0`):
1. Ensure `isolation_forest_v0.9.0.joblib` and `metadata_v0.9.0.json` are present in the `ml/models/` directory.
2. Update `docker-compose.yml` to set `MODEL_VERSION=v0.9.0` for the `edge-service` container.
3. Restart the container: `docker compose up -d edge-service`
