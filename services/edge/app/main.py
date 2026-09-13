# Entrypoint re-export for modular imports
import sys
from pathlib import Path

# Ensure services/edge root is in sys.path
edge_root = str(Path(__file__).resolve().parent.parent)
if edge_root not in sys.path:
    sys.path.insert(0, edge_root)

from main import app, lifespan

__all__ = ["app", "lifespan"]
