import os
import pytest
import numpy as np

# Ensure we test with the fallback or locally generated model
os.environ["MODEL_VERSION"] = "v1.0.0"

# Note: Adjust paths in inference.py for testing if needed
# The script uses a fallback path, so it should find ml/models if run from root.

import inference

def test_normal_telemetry():
    """Test a completely normal telemetry vector."""
    # Near the mean of the training data: 25.0, 50.0, 0.5, 1013.25
    score = inference.get_anomaly_score(25.0, 50.0, 0.5, 1013.25)
    severity = inference.classify_severity(score)
    assert severity == "NORMAL", f"Expected NORMAL, got {severity} with score {score}"

def test_warning_telemetry():
    """Test a moderately out-of-bounds telemetry vector."""
    # Deviate features to push score below warning_limit but above critical_limit
    score = inference.get_anomaly_score(30.0, 30.0, 0.8, 990.0)
    severity = inference.classify_severity(score)
    assert severity in ["WARNING", "CRITICAL"], f"Expected WARNING or CRITICAL, got {severity} with score {score}"

def test_critical_telemetry():
    """Test an extreme telemetry vector."""
    # Extreme values
    score = inference.get_anomaly_score(500.0, 0.0, 50.0, 5000.0)
    severity = inference.classify_severity(score)
    assert severity == "CRITICAL", f"Expected CRITICAL, got {severity} with score {score}"
