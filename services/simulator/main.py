import os
import time
import json
import random
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC = "edgesentinel/devices/DEVICE-001/telemetry"
DEVICE_ID = "DEVICE-001"


def on_connect(client, userdata, flags, reason_code, properties):
    """Called when the broker accepts our connection (paho-mqtt v2 API)."""
    if reason_code == 0:
        print("Simulator connected to MQTT Broker!")
    else:
        print(f"Failed to connect, reason code: {reason_code}")


# Use VERSION2 callback API to suppress all deprecation warnings
client = mqtt.Client(
    callback_api_version=CallbackAPIVersion.VERSION2,
    client_id=f"simulator-{DEVICE_ID}"
)
client.on_connect = on_connect

# Retry loop for initial connection — paho's loop_start handles reconnections after that
connected = False
while not connected:
    try:
        client.connect(MQTT_HOST, MQTT_PORT)
        connected = True
    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5)

client.loop_start()

try:
    while True:
        payload = {
            "deviceId": DEVICE_ID,
            "temperature": round(random.uniform(20.0, 80.0), 2),
            "humidity": round(random.uniform(30.0, 90.0), 2),
            "vibration": round(random.uniform(0.1, 5.0), 2),
            "pressure": round(random.uniform(900.0, 1100.0), 2),
            "machineState": random.choice(["RUNNING", "IDLE", "MAINTENANCE"]),
            "timestamp": int(time.time() * 1000)
        }
        client.publish(TOPIC, json.dumps(payload))
        print(f"Published: {payload}")
        time.sleep(5)
except KeyboardInterrupt:
    print("Simulator stopped.")
finally:
    client.loop_stop()
    client.disconnect()
