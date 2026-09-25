import os
import json
import joblib
import numpy as np

# Load model version from environment, defaulting to v1.0.0
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1.0.0")

# Paths inside the container where the models directory is mounted
MODELS_DIR = "/app/models"
MODEL_PATH = os.path.join(MODELS_DIR, f"isolation_forest_{MODEL_VERSION}.joblib")
METADATA_PATH = os.path.join(MODELS_DIR, f"metadata_{MODEL_VERSION}.json")

# Fallback paths for local testing
if not os.path.exists(MODELS_DIR):
    MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml", "models")
    MODEL_PATH = os.path.join(MODELS_DIR, f"isolation_forest_{MODEL_VERSION}.joblib")
    METADATA_PATH = os.path.join(MODELS_DIR, f"metadata_{MODEL_VERSION}.json")

try:
    print(f"Loading model artifact: {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    
    print(f"Loading model metadata: {METADATA_PATH}")
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)
        
    WARNING_LIMIT = metadata.get("thresholds", {}).get("warning_limit", -0.1)
    CRITICAL_LIMIT = metadata.get("thresholds", {}).get("critical_limit", -0.2)
except Exception as e:
    print(f"Warning: Failed to load model or metadata: {e}")
    # Fallback dummy model/thresholds if files are missing
    from sklearn.ensemble import IsolationForest
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    # Dummy training to avoid NotFittedError during fallback
    model.fit(np.random.normal(loc=0, scale=1, size=(100, 4)))
    WARNING_LIMIT = -0.08
    CRITICAL_LIMIT = -0.12

def get_anomaly_score(temperature: float, humidity: float, vibration: float, pressure: float) -> float:
    """
    Calculate the anomaly score for the given telemetry.
    """
    X = np.array([[temperature, humidity, vibration, pressure]])
    score = model.decision_function(X)[0]
    return float(score)

def classify_severity(score: float) -> str:
    """
    Classify severity based on the loaded anomaly score thresholds.
    """
    if score >= WARNING_LIMIT:
        return "NORMAL"
    elif score >= CRITICAL_LIMIT:
        return "WARNING"
    else:
        return "CRITICAL"
