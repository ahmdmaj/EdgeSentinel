import os
import time
import json
import random
import threading
import paho.mqtt.client as mqtt

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "edge_client")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

# Fleet of 5 distinct simulated devices
DEVICE_IDS = [f"DEVICE-{str(i).zfill(3)}" for i in range(1, 6)]
MACHINE_STATES = ["RUNNING", "IDLE", "MAINTENANCE"]


def make_payload(device_id: str) -> dict:
    """Generate a realistic telemetry reading for a given device."""
    return {
        "deviceId": device_id,
        "temperature": round(random.uniform(20.0, 80.0), 2),
        "humidity": round(random.uniform(30.0, 90.0), 2),
        "vibration": round(random.uniform(0.1, 5.0), 2),
        "pressure": round(random.uniform(900.0, 1100.0), 2),
        "machineState": random.choice(MACHINE_STATES),
        "timestamp": int(time.time() * 1000),
    }


def run_device(device_id: str):
    """Each device runs in its own thread with its own MQTT client connection."""
    topic = f"edgesentinel/devices/{device_id}/telemetry"
    client = mqtt.Client(client_id=f"simulator-{device_id}")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    def on_connect(c, userdata, flags, rc):
        if rc == 0:
            print(f"[{device_id}] Connected to MQTT broker.")
        else:
            print(f"[{device_id}] Connection failed, rc={rc}")

    client.on_connect = on_connect

    # Retry loop until we connect
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT)
            break
        except Exception as e:
            print(f"[{device_id}] Broker unreachable: {e}. Retrying in 5s...")
            time.sleep(5)

    client.loop_start()

    # Stagger device start times so they don't all publish at T=0
    time.sleep(random.uniform(0, 3))

    try:
        while True:
            payload = make_payload(device_id)
            client.publish(topic, json.dumps(payload))
            print(f"[{device_id}] Published to {topic}: state={payload['machineState']} temp={payload['temperature']}")
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
        print(f"[{device_id}] Disconnected.")


def main():
    print(f"Starting EdgeSentinel Fleet Simulator with {len(DEVICE_IDS)} devices: {DEVICE_IDS}")
    threads = []
    for device_id in DEVICE_IDS:
        t = threading.Thread(target=run_device, args=(device_id,), daemon=True, name=f"device-{device_id}")
        threads.append(t)
        t.start()

    # Block main thread indefinitely; daemon threads exit on KeyboardInterrupt
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulator shutting down.")


if __name__ == "__main__":
    main()
