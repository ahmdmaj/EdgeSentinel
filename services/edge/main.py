import os
import sys

# Force unbuffered output so logs appear immediately in docker logs
sys.stdout.reconfigure(line_buffering=True)
import json
import time
import asyncio
import uuid
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter
import inference
import decision_engine
from app.storage.outbox import outbox_repo
from app.sync.worker import sync_worker
import random

EVENTS_PROCESSED_TOTAL = Counter(
    "events_processed_total",
    "Total number of telemetry events processed by the edge service"
)

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC_WILDCARD = "edgesentinel/devices/+/telemetry"

FAULT_STATE = {
    "offline": False,
    "latency_ms": 0
}

mqtt_client = None


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the client connects to the broker (paho-mqtt v2 API)."""
    if reason_code == 0:
        print(f"Connected to MQTT Broker at {MQTT_HOST}:{MQTT_PORT}. Subscribing to {TOPIC_WILDCARD}...", flush=True)
        client.subscribe(TOPIC_WILDCARD)
    else:
        print(f"Failed to connect to MQTT Broker with reason code: {reason_code}", flush=True)


def on_message(client, userdata, msg):
    """Processes incoming telemetry messages from MQTT broker."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"\n--- Ingested Telemetry from {msg.topic} ---", flush=True)
        EVENTS_PROCESSED_TOTAL.inc()
        
        # Run ML Inference
        score = inference.get_anomaly_score(
            payload.get("temperature", 0.0),
            payload.get("humidity", 0.0),
            payload.get("vibration", 0.0),
            payload.get("pressure", 0.0)
        )
        severity = inference.classify_severity(score)
        
        # Append ML results to payload
        payload["anomalyScore"] = score
        payload["severity"] = severity
        
        # Simulate edge metrics and evaluate routing policy
        edge_cpu = round(random.uniform(10.0, 90.0), 2)
        
        # Read simulated latency if fault injection is active
        simulated_latency = FAULT_STATE.get("latency_ms", 0)
        if simulated_latency > 0:
            network_latency = float(simulated_latency)
        else:
            network_latency = round(random.uniform(15.0, 75.0), 2)

        decision = decision_engine.evaluate_routing_policy(severity, network_latency, edge_cpu)
        
        payload["edgeCpu"] = edge_cpu
        payload["networkLatency"] = network_latency
        payload["processingDecision"] = decision
        
        event_id = str(uuid.uuid4())
        payload["eventId"] = event_id
        
        print(json.dumps(payload, indent=2), flush=True)

        # Offline-First Architecture (Section 21 & Section 22):
        # Durably enqueue event into local SQLite outbox queue first.
        # The MQTT ingestion thread never blocks or crashes on network timeouts.
        outbox_repo.enqueue(event_id, payload)
        print(f"MQTT Ingest: Telemetry event {event_id} queued to local SQLite outbox.", flush=True)
            
    except json.JSONDecodeError:
        print(f"Failed to parse JSON payload from {msg.topic}: {msg.payload}", flush=True)
    except Exception as e:
        print(f"Error processing message: {e}", flush=True)


def on_disconnect(client, userdata, flags, reason_code, properties):
    """Called when the client disconnects from the broker (paho-mqtt v2 API)."""
    print(f"Disconnected from MQTT Broker with reason code: {reason_code}", flush=True)


def setup_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id="edge-service-client"
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    # Handle initial connection with retry
    connected = False
    while not connected:
        try:
            mqtt_client.connect(MQTT_HOST, MQTT_PORT)
            connected = True
        except Exception as e:
            print(f"Edge MQTT connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    mqtt_client.loop_start()


def teardown_mqtt():
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("MQTT client stopped.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch background sync worker and connect MQTT
    sync_worker.start()
    setup_mqtt()
    yield
    # Shutdown: Cleanly stop MQTT and cancel background sync worker
    teardown_mqtt()
    await sync_worker.stop()


app = FastAPI(title="Edge Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


class FaultUpdateRequest(BaseModel):
    offline: Optional[bool] = None
    latency_ms: Optional[int] = None


@app.get("/")
def read_root():
    return {
        "status": "Edge service running",
        "fault_state": FAULT_STATE,
        "outbox_stats": outbox_repo.get_stats(),
    }


@app.get("/faults")
def get_faults():
    return FAULT_STATE


@app.post("/faults")
async def update_faults(request: FaultUpdateRequest):
    if request.offline is not None:
        FAULT_STATE["offline"] = request.offline
    if request.latency_ms is not None:
        FAULT_STATE["latency_ms"] = max(0, request.latency_ms)
    print(f"Fault state updated via HTTP: {FAULT_STATE}", flush=True)
    return {
        "status": "success",
        "message": "Fault state updated successfully",
        "fault_state": FAULT_STATE
    }


@app.get("/outbox/stats")
def get_outbox_stats():
    """Returns real-time status counts of the local SQLite outbox queue."""
    return {
        "status": "success",
        "stats": outbox_repo.get_stats(),
    }
