import os
import time
import json
import random
import paho.mqtt.client as mqtt

MQTT_BROKER_URL = os.environ.get("MQTT_BROKER_URL", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC = "edgesentinel/devices/DEVICE-001/telemetry"
DEVICE_ID = "DEVICE-001"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

client = mqtt.Client(client_id=f"simulator-{DEVICE_ID}")
client.on_connect = on_connect

# Basic reconnection handling is done implicitly by paho-mqtt's loop_start/reconnect mechanisms,
# but we ensure the initial connection doesn't crash permanently.
connected = False
while not connected:
    try:
        client.connect(MQTT_BROKER_URL, MQTT_PORT)
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
