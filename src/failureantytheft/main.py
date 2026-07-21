"""ASGI entry point: ``uvicorn failureantytheft.main:app``."""

from failureantytheft.api import create_app

app = create_app()

__all__ = ["app"]
