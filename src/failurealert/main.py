"""ASGI entry point: ``uvicorn failurealert.main:app``."""

from failurealert.api import create_app

app = create_app()

__all__ = ["app"]
