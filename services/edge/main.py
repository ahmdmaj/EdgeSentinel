# Root entrypoint re-exporting from app.main for Dockerfile (CMD ["uvicorn", "main:app"])
from app.main import (
    app,
    lifespan,
    outbox_repo,
    sync_worker,
    setup_mqtt,
    teardown_mqtt,
    graceful_shutdown,
    on_message,
    on_connect,
    on_disconnect,
    FAULT_STATE,
)

__all__ = [
    "app",
    "lifespan",
    "outbox_repo",
    "sync_worker",
    "setup_mqtt",
    "teardown_mqtt",
    "graceful_shutdown",
    "on_message",
    "on_connect",
    "on_disconnect",
    "FAULT_STATE",
]
