"""Entrypoint for local and containerized runs alike.

Binds according to app.config.settings (0.0.0.0 by default per CLAUDE.md
Section 31), so `python run.py` behaves the same on a laptop, a lab server,
or inside a container.
"""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port)
