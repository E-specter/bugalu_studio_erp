"""Arranque local: `uv run python -m bugalu` (recarga automatica, bucle compatible con psycopg)."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "bugalu.main:crear_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
        loop="bugalu.compartido.bucle:crear_bucle",
    )


if __name__ == "__main__":
    main()
