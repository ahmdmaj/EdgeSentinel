import os
import sys

# Force unbuffered output so logs appear immediately in docker logs
sys.stdout.reconfigure(line_buffering=True)
import json
import time
from fastapi import FastAPI
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC_WILDCARD = "edgesentinel/devices/+/telemetry"

mqtt_client = None


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
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"Received message on {msg.topic}:", flush=True)
        print(json.dumps(payload, indent=2), flush=True)
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
    # Startup
    setup_mqtt()
    yield
    # Shutdown
    teardown_mqtt()


app = FastAPI(title="Edge Service", lifespan=lifespan)


@app.get("/")
def read_root():
    return {"status": "Edge service running"}
