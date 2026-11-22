import sys
from pathlib import Path

# Add backend directory to sys.path so app module can be found
backend_dir = str(Path(__file__).resolve().parents[1])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app

# Vercel ASGI entry point
app = app
