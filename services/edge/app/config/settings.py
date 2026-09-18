import os
from pathlib import Path

# Look for .env in services/edge/.env or root .env
def load_env_file():
    current_dir = Path(__file__).resolve().parent
    candidates = [
        current_dir.parent.parent / ".env",  # services/edge/.env
        current_dir.parent.parent.parent.parent / ".env",  # root .env
    ]
    for env_path in candidates:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            os.environ.setdefault(key, val)
            except Exception:
                pass

load_env_file()

class Settings:
    API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://cloud-api:3000")
    API_EMAIL: str = os.environ.get("API_EMAIL", "admin@edgesentinel.local")
    
    API_PASSWORD: str | None = os.environ.get("API_PASSWORD")
    EDGE_ADMIN_TOKEN: str | None = os.environ.get("EDGE_ADMIN_TOKEN")
    
    MQTT_USERNAME: str | None = os.environ.get("MQTT_USERNAME")
    MQTT_PASSWORD: str | None = os.environ.get("MQTT_PASSWORD")

    def __init__(self):
        if not self.API_PASSWORD or self.API_PASSWORD == "admin123":
            raise ValueError("FATAL: API_PASSWORD is missing or insecure.")
        if not self.EDGE_ADMIN_TOKEN:
            raise ValueError("FATAL: EDGE_ADMIN_TOKEN environment variable is missing.")
        if not self.MQTT_USERNAME:
            raise ValueError("FATAL: MQTT_USERNAME environment variable is missing.")
        if not self.MQTT_PASSWORD or self.MQTT_PASSWORD == "admin123":
            raise ValueError("FATAL: MQTT_PASSWORD environment variable is missing or insecure.")

settings = Settings()
