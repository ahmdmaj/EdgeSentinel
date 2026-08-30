import os
import json
import time
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import paho.mqtt.client as mqtt

MQTT_BROKER_URL = os.environ.get("MQTT_BROKER_URL", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC_WILDCARD = "edgesentinel/devices/+/telemetry"

mqtt_client = None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Edge Service connected to MQTT Broker!")
        client.subscribe(TOPIC_WILDCARD)
        print(f"Subscribed to topic: {TOPIC_WILDCARD}")
    else:
        print(f"Failed to connect to MQTT Broker, return code: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"Received message on {msg.topic}:")
        print(json.dumps(payload, indent=2))
    except json.JSONDecodeError:
        print(f"Failed to parse JSON payload from {msg.topic}: {msg.payload}")
    except Exception as e:
        print(f"Error processing message: {e}")

def on_disconnect(client, userdata, rc):
    print(f"Disconnected from MQTT Broker with return code: {rc}")

def setup_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client(client_id="edge-service-client")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect
    
    # Handle initial connection with retry
    connected = False
    while not connected:
        try:
            mqtt_client.connect(MQTT_BROKER_URL, MQTT_PORT)
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
