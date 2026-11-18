"""hiaok - lightweight permission center (DDD, event-driven, read/write split)."""

import sys


def main() -> None:
    """``hiaok`` (API) | ``hiaok worker`` (event consumer)."""
    command = sys.argv[1] if len(sys.argv) > 1 else "api"
    if command == "api":
        from .main import run_api

        run_api()
    elif command == "worker":
        import anyio

        from .main import run_worker

        anyio.run(run_worker)
    else:
        raise SystemExit(f"unknown command {command!r} (expected: api | worker)")
