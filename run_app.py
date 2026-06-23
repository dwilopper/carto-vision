from __future__ import annotations

import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOCAL_DEPS = BASE_DIR / ".pydeps"

if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

from app.main import app  # noqa: E402


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=False,
    )
