import os
import time
import json
import random
import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
TOPIC = "edgesentinel/devices/DEVICE-001/telemetry"
DEVICE_ID = "DEVICE-001"


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, result code: {rc}")


client = mqtt.Client(
    client_id=f"simulator-{DEVICE_ID}"
)
mqtt_username = os.environ.get("MQTT_USERNAME")
mqtt_password = os.environ.get("MQTT_PASSWORD")
if mqtt_username and mqtt_password:
    client.username_pw_set(mqtt_username, mqtt_password)
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
