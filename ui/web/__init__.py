"""Web implementation: FastAPI server + a static HTML/CSS/JS page.

Needs `pip install fastapi uvicorn`. Only `main.py` imports this package.
"""
from ui.web.app import create_app

__all__ = ["create_app"]
