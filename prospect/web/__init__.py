"""Web UI for LeadSwarm."""


def __getattr__(name: str):
    # Avoid importing the full FastAPI app (and initializing the DB) at package import time.
    if name == "create_app":
        from prospect.web.app import create_app  # local import by design

        globals()["create_app"] = create_app
        return create_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_app"]
