import os
import sys

# Force unbuffered output so logs appear immediately in docker logs
sys.stdout.reconfigure(line_buffering=True)
import json
import time
import asyncio
import httpx
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
import storage
import sync
import decision_engine
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
main_loop = None


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the broker accepts our connection (paho-mqtt v2 API)."""
    if reason_code == 0:
        print("Edge Service connected to MQTT Broker!", flush=True)
        client.subscribe(TOPIC_WILDCARD)
        print(f"Subscribed to topic: {TOPIC_WILDCARD}", flush=True)
    else:
        print(f"Failed to connect to MQTT Broker, reason code: {reason_code}", flush=True)


def on_message(client, userdata, msg):
    """Called when a message is received on a subscribed topic."""
    try:
        EVENTS_PROCESSED_TOTAL.inc()
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"Received message on {msg.topic}:", flush=True)
        
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
        
        print(json.dumps(payload, indent=2), flush=True)
        
        event_id = str(uuid.uuid4())
        payload["eventId"] = event_id
        
        async def forward_telemetry():
            if not sync.cloud_token:
                print("No JWT token available - caching locally.", flush=True)
                await asyncio.to_thread(storage.save_event_to_outbox, event_id, payload)
                return

            try:
                # Fault Injection: Simulated Cloud Outage
                if FAULT_STATE.get("offline", False):
                    print("Simulated fault active: Offline mode forced. Raising httpx.ConnectError.", flush=True)
                    raise httpx.ConnectError("Simulated cloud outage: Edge service is offline.")

                # Fault Injection: Simulated Network Latency
                latency_ms = FAULT_STATE.get("latency_ms", 0)
                if latency_ms > 0:
                    print(f"Simulated fault active: Delaying HTTP transmission by {latency_ms} ms.", flush=True)
                    await asyncio.sleep(latency_ms / 1000.0)

                headers = {"Authorization": f"Bearer {sync.cloud_token}"}
                timeout_val = max(5.0, (latency_ms / 1000.0) + 5.0)
                async with httpx.AsyncClient(timeout=timeout_val, headers=headers) as http_client:
                    response = await http_client.post("http://cloud-api:3000/api/v1/telemetry", json=payload)
                    if response.status_code == 401:
                        sync.cloud_token = None
                        print("Unauthorized! JWT token invalid. Will re-fetch.", flush=True)
                    response.raise_for_status()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                print(f"Cloud unavailable or error - caching locally. Error: {e}", flush=True)
                await asyncio.to_thread(storage.save_event_to_outbox, event_id, payload)
            except Exception as e:
                print(f"Error forwarding telemetry to Cloud API: {e}", flush=True)
                await asyncio.to_thread(storage.save_event_to_outbox, event_id, payload)
        
        if main_loop:
            asyncio.run_coroutine_threadsafe(forward_telemetry(), main_loop)
            
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


sync_task = None
token_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    global sync_task
    global token_task
    main_loop = asyncio.get_running_loop()
    # Startup
    storage.Base.metadata.create_all(bind=storage.engine)
    setup_mqtt()
    token_task = asyncio.create_task(sync.fetch_token_loop())
    sync_task = asyncio.create_task(sync.sync_worker())
    yield
    # Shutdown
    if token_task:
        token_task.cancel()
    if sync_task:
        sync_task.cancel()
    teardown_mqtt()


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
    return {"status": "Edge service running", "fault_state": FAULT_STATE}


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

