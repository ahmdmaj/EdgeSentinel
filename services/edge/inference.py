import numpy as np
from sklearn.ensemble import IsolationForest

# Initialize the Isolation Forest model
model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)

def train_dummy_model():
    """
    Train the model on a dummy dataset representing normal operating ranges.
    Features: [temperature, humidity, vibration, pressure]
    """
    np.random.seed(42)
    # Calibrated to match simulator normal ranges:
    # Temperature: 20 to 80, Humidity: 30 to 70, Vibration: 0.1 to 2.5, Pressure: 980 to 1025
    normal_data = np.column_stack([
        np.random.uniform(20.0, 80.0, 200),
        np.random.uniform(30.0, 70.0, 200),
        np.random.uniform(0.1, 2.5, 200),
        np.random.uniform(980.0, 1025.0, 200)
    ])
    model.fit(normal_data)

# Train the model upon initialization
train_dummy_model()

def get_anomaly_score(temperature: float, humidity: float, vibration: float, pressure: float) -> float:
    """
    Calculate the anomaly score for the given telemetry.
    The score is typically negative for anomalies and positive for normal points.
    """
    X = np.array([[temperature, humidity, vibration, pressure]])
    score = model.decision_function(X)[0]
    return float(score)

def classify_severity(score: float) -> str:
    """
    Classify severity based on the anomaly score.
    """
    if score >= -0.08:
        return "NORMAL"
    elif score >= -0.12:
        return "WARNING"
    else:
        return "CRITICAL"
