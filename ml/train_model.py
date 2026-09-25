import os
import json
import joblib
import datetime
import numpy as np
from sklearn.ensemble import IsolationForest

def generate_synthetic_data(num_samples: int = 1000) -> np.ndarray:
    """Generate baseline normal synthetic telemetry data."""
    # Features: temperature, humidity, vibration, pressure
    # Normal operating ranges:
    # Temp: ~25.0, Humidity: ~50.0, Vib: ~0.5, Pressure: ~1013.25
    X = np.zeros((num_samples, 4))
    
    # Add some random normal noise around the baseline
    X[:, 0] = np.random.normal(loc=25.0, scale=2.0, size=num_samples) # Temperature
    X[:, 1] = np.random.normal(loc=50.0, scale=5.0, size=num_samples) # Humidity
    X[:, 2] = np.random.normal(loc=0.5, scale=0.1, size=num_samples) # Vibration
    X[:, 3] = np.random.normal(loc=1013.25, scale=5.0, size=num_samples) # Pressure
    
    return X

def main():
    model_version = "v1.0.0"
    model_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, f"isolation_forest_{model_version}.joblib")
    metadata_path = os.path.join(model_dir, f"metadata_{model_version}.json")
    
    print("Generating synthetic baseline data...")
    X_train = generate_synthetic_data(5000)
    
    print("Training IsolationForest model...")
    model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    model.fit(X_train)
    
    print(f"Saving model artifact to {model_path}...")
    joblib.dump(model, model_path)
    
    # Define thresholds
    # In sklearn IsolationForest, score_samples returns negative anomaly scores
    # Lower values (more negative) indicate more anomalous. 
    # For our edge service, we historically transformed this or we can just define thresholds here.
    # Let's say we define scoring thresholds based on the model's decision function:
    metadata = {
        "model_name": "IsolationForest_AnomalyDetector",
        "model_version": model_version,
        "training_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "features": ["temperature", "humidity", "vibration", "pressure"],
        "thresholds": {
            "warning_limit": -0.05,
            "critical_limit": -0.14
        }
    }
    
    print(f"Saving model metadata to {metadata_path}...")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
        
    print("Training complete!")

if __name__ == "__main__":
    main()
