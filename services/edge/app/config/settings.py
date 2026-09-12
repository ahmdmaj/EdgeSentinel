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
    API_PASSWORD: str = os.environ.get("API_PASSWORD", "admin123")

settings = Settings()
