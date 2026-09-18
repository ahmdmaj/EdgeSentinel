import os
import sys
from pathlib import Path

# Force unbuffered output for immediate container logs
sys.stdout.reconfigure(line_buffering=True)  # type: ignore

# Ensure services/edge root is in sys.path for local module imports (inference, decision_engine)
edge_root = str(Path(__file__).resolve().parent.parent)
if edge_root not in sys.path:
    sys.path.insert(0, edge_root)

import json
import time
import asyncio
import signal
import uuid
import logging
import random
from typing import Optional
from contextlib import asynccontextmanager

from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Gauge

import inference  # type: ignore
import decision_engine  # type: ignore
from app.storage.outbox import outbox_repo  # type: ignore
from app.sync.worker import sync_worker  # type: ignore

logger = logging.getLogger("edge.main")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

EVENTS_PROCESSED_TOTAL = Counter(
    "events_processed_total",
    "Total number of telemetry events processed by the edge service"
)

CLOUD_SYNC_SUCCESS_TOTAL = Counter(
    "cloud_sync_success_total",
    "Total number of telemetry events successfully synced to the cloud API"
)

CLOUD_SYNC_FAILURE_TOTAL = Counter(
    "cloud_sync_failure_total",
    "Total number of telemetry events that failed to sync to the cloud API"
)

OUTBOX_PENDING_EVENTS = Gauge(
    "outbox_pending_events",
    "Current number of pending events in the local SQLite outbox"
)

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC_WILDCARD = "edgesentinel/devices/+/telemetry"

FAULT_STATE = {
    "offline": False,
    "latency_ms": 0
}

mqtt_client = None
_shutdown_completed = False


def is_offline() -> bool:
    """Returns whether offline fault simulation is active."""
    return FAULT_STATE.get("offline", False)


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the client connects to the MQTT broker (paho-mqtt v2 API)."""
    if reason_code == 0:
        logger.info(f"Connected to MQTT Broker at {MQTT_HOST}:{MQTT_PORT}. Subscribing to {TOPIC_WILDCARD}...")
        client.subscribe(TOPIC_WILDCARD)
    else:
        logger.error(f"Failed to connect to MQTT Broker with reason code: {reason_code}")


def on_message(client, userdata, msg):
    """
    Processes incoming telemetry messages from MQTT broker.
    Thread-safe and decoupled: ML inference is computed locally, and the event
    is written directly to the local SQLite outbox queue (Section 21 & Section 22).
    The MQTT ingest thread never blocks on cloud network latency or timeouts.
    """
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        logger.info(f"Ingested Telemetry from {msg.topic}")
        EVENTS_PROCESSED_TOTAL.inc()

        # 1. Run local ML Inference
        score = inference.get_anomaly_score(
            payload.get("temperature", 0.0),
            payload.get("humidity", 0.0),
            payload.get("vibration", 0.0),
            payload.get("pressure", 0.0)
        )
        severity = inference.classify_severity(score)

        payload["anomalyScore"] = score
        payload["severity"] = severity

        # 2. Evaluate edge routing policy
        edge_cpu = round(random.uniform(10.0, 90.0), 2)
        simulated_latency = FAULT_STATE.get("latency_ms", 0)
        if simulated_latency > 0:
            network_latency = float(simulated_latency)
        else:
            network_latency = round(random.uniform(15.0, 75.0), 2)

        decision = decision_engine.evaluate_routing_policy(severity, network_latency, edge_cpu)
        payload["edgeCpu"] = edge_cpu
        payload["networkLatency"] = network_latency
        payload["processingDecision"] = decision

        # 3. Assign unique eventId
        event_id = payload.get("eventId") or str(uuid.uuid4())
        payload["eventId"] = event_id

        # 4. Offline-First Resilience (Sections 21 & 22):
        # Enqueue event into local SQLite outbox (outbox_events) with BEGIN IMMEDIATE
        outbox_repo.insert_event(event_id, payload)
        logger.info(f"MQTT Ingest: Telemetry event {event_id} queued to local SQLite outbox.")

    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON payload from {msg.topic}: {msg.payload}")
    except Exception as e:
        logger.error(f"Error processing telemetry message: {e}", exc_info=True)


def on_disconnect(client, userdata, flags, reason_code, properties):
    """Called when the client disconnects from the broker (paho-mqtt v2 API)."""
    logger.warning(f"Disconnected from MQTT Broker with reason code: {reason_code}")


import threading

def _mqtt_connect_loop():
    backoff = 2
    while not _shutdown_completed:
        try:
            mqtt_client.connect(MQTT_HOST, MQTT_PORT)
            mqtt_client.loop_start()
            logger.info("MQTT background listener loop started.")
            break
        except Exception as e:
            logger.warning(f"MQTT broker connection failed: {e}. Retrying in {backoff} seconds...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

def setup_mqtt():
    """Initializes and connects MQTT subscriber."""
    global mqtt_client
    from app.config.settings import settings  # type: ignore
    mqtt_client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=f"edge-service-{uuid.uuid4().hex[:6]}"
    )
    mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    t = threading.Thread(target=_mqtt_connect_loop, daemon=True)
    t.start()


def teardown_mqtt():
    """Safely disconnects and stops the MQTT listener thread."""
    global mqtt_client
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            logger.info("MQTT client disconnected cleanly.")
        except Exception as e:
            logger.warning(f"Error disconnecting MQTT client: {e}")
        finally:
            mqtt_client = None


async def graceful_shutdown():
    """
    Graceful Shutdown Hook (Section 24):
    Captures termination signals to safely flush in-flight outbox writes,
    cancel background sync workers, and close database handles.
    """
    global _shutdown_completed
    if _shutdown_completed:
        return
    _shutdown_completed = True

    logger.info("Section 24: Graceful shutdown initiated...")

    # 1. Teardown MQTT subscriber to stop accepting new messages
    teardown_mqtt()

    # 2. Stop background sync worker loop cleanly
    await sync_worker.stop()

    # 3. Checkpoint WAL and close SQLite database handles
    outbox_repo.close()

    logger.info("Section 24: Graceful shutdown completed cleanly.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure sync worker with fault simulation hook
    sync_worker.is_offline_func = is_offline

    # Startup: Launch background sync worker task and MQTT client
    sync_worker.start()
    setup_mqtt()

    # Register OS signal handlers for graceful shutdown (Section 24)
    loop = asyncio.get_event_loop()

    def _sync_signal_handler(sig_num, frame=None):
        logger.info(f"Received OS signal {sig_num}. Scheduling graceful shutdown...")
        asyncio.create_task(graceful_shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(graceful_shutdown()))
        except (NotImplementedError, RuntimeError):
            # Fallback for platforms/environments where loop.add_signal_handler is not available (e.g. Windows non-proactor)
            try:
                signal.signal(sig, _sync_signal_handler)
            except Exception:
                pass

    try:
        yield
    finally:
        # Executes when FastAPI/Uvicorn triggers shutdown
        await graceful_shutdown()


app = FastAPI(title="Edge Sentinel Service", lifespan=lifespan)

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


def verify_edge_admin(x_edge_admin_token: str = Header(None)):
    from app.config.settings import settings  # type: ignore
    if not x_edge_admin_token or x_edge_admin_token != settings.EDGE_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized Edge Control access")


@app.post("/faults", dependencies=[Depends(verify_edge_admin)])
async def update_faults(request: FaultUpdateRequest):
    if request.offline is not None:
        FAULT_STATE["offline"] = request.offline
    if request.latency_ms is not None:
        FAULT_STATE["latency_ms"] = max(0, request.latency_ms)
    logger.info(f"Fault state updated via HTTP: {FAULT_STATE}")
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


@app.post("/telemetry")
async def ingest_telemetry_http(payload: dict):
    """
    HTTP Ingestion Endpoint for Edge Node (Section 21 Offline-First).
    Accepts telemetry payload, evaluates inference & routing, and durably
    queues the event into the local SQLite outbox (outbox_events) with status PENDING.
    """
    try:
        # Default any missing sensor metrics to standard baseline so schema validation passes
        payload.setdefault("temperature", 25.0)
        payload.setdefault("humidity", 50.0)
        payload.setdefault("vibration", 0.5)
        payload.setdefault("pressure", 1013.25)
        payload.setdefault("machineState", "RUNNING")

        # Run ML inference
        score = inference.get_anomaly_score(
            float(payload.get("temperature", 0.0) or 0.0),
            float(payload.get("humidity", 0.0) or 0.0),
            float(payload.get("vibration", 0.0) or 0.0),
            float(payload.get("pressure", 0.0) or 0.0)
        )
        severity = inference.classify_severity(score)
        payload["anomalyScore"] = score
        payload["severity"] = severity

        edge_cpu = round(random.uniform(10.0, 90.0), 2)
        simulated_latency = FAULT_STATE.get("latency_ms", 0)
        network_latency = float(simulated_latency) if simulated_latency > 0 else round(random.uniform(15.0, 75.0), 2)
        decision = decision_engine.evaluate_routing_policy(severity, network_latency, edge_cpu)
        payload["edgeCpu"] = edge_cpu
        payload["networkLatency"] = network_latency
        payload["processingDecision"] = decision

        event_id = payload.get("eventId") or str(uuid.uuid4())
        payload["eventId"] = event_id

        # Durably enqueue into SQLite outbox
        inserted = outbox_repo.insert_event(event_id, payload)
        logger.info(f"HTTP Ingest: Telemetry event {event_id} queued to local SQLite outbox (status: PENDING).")

        return {
            "status": "QUEUED",
            "message": "Telemetry queued to local outbox",
            "eventId": event_id,
            "outboxStatus": "PENDING"
        }
    except Exception as e:
        logger.error(f"Failed to ingest telemetry via HTTP: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "message": str(e)
        }
