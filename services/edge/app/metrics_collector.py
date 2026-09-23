"""
metrics_collector.py — Real Edge Node System Metrics

Collects actual CPU and memory utilization from the host via psutil,
and measures real network latency to the Cloud API via a timed socket
connection. These values replace all random() mocks in the routing path.
"""
import os
import socket
import time
import logging

import psutil

logger = logging.getLogger("edge.metrics_collector")

# Read the Cloud API host from env (strip scheme and path, keep host only)
_API_BASE_URL = os.environ.get("API_BASE_URL", "http://cloud-api:3000")
_API_HOST = _API_BASE_URL.replace("http://", "").replace("https://", "").split(":")[0]
_API_PORT_STR = _API_BASE_URL.replace("http://", "").replace("https://", "").split(":")[-1].split("/")[0]
try:
    _API_PORT = int(_API_PORT_STR)
except ValueError:
    _API_PORT = 80

_LATENCY_TIMEOUT_S = 2.0   # socket connect timeout in seconds
_LATENCY_ON_FAILURE_MS = 9999.0  # returned when the cloud is unreachable


def get_cpu_percent() -> float:
    """Returns the current host CPU utilization as a percentage (0-100)."""
    return psutil.cpu_percent(interval=0.1)


def get_memory_percent() -> float:
    """Returns the current host memory utilization as a percentage (0-100)."""
    return psutil.virtual_memory().percent


def get_api_latency_ms() -> float:
    """
    Measures network latency to the Cloud API by timing a raw TCP socket
    connection to the API host:port. Returns the round-trip time in ms,
    or _LATENCY_ON_FAILURE_MS if the API is unreachable.
    """
    try:
        start = time.perf_counter()
        with socket.create_connection((_API_HOST, _API_PORT), timeout=_LATENCY_TIMEOUT_S):
            elapsed_ms = (time.perf_counter() - start) * 1000
            return round(elapsed_ms, 2)
    except Exception as e:
        logger.warning(f"API latency probe failed ({_API_HOST}:{_API_PORT}): {e}")
        return _LATENCY_ON_FAILURE_MS


def collect() -> dict:
    """
    Returns a snapshot of real edge node metrics:
      - cpu_percent: host CPU utilization
      - memory_percent: host memory utilization
      - api_latency_ms: measured TCP latency to Cloud API
    """
    return {
        "cpu_percent": get_cpu_percent(),
        "memory_percent": get_memory_percent(),
        "api_latency_ms": get_api_latency_ms(),
    }
