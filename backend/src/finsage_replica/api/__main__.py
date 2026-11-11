"""Run the chatbot API.

    uv run python -m finsage_replica.api            # dev fixture source, port 8000

Environment:
    FINSAGE_SOURCE   dev (default). The live pipeline source is wired in T4.
    FINSAGE_PORT     default 8000
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

from finsage_replica.api.app import create_app
from finsage_replica.demo.dev_source import DevSource

REPO = Path(__file__).resolve().parents[4]


def main() -> None:
    source_name = os.environ.get("FINSAGE_SOURCE", "dev")
    if source_name != "dev":
        raise SystemExit(f"FINSAGE_SOURCE={source_name} is not available yet; only 'dev' until T4 lands")
    app = create_app(
        source=DevSource(),
        pdf_dir=REPO / "data" / "financebench" / "pdfs",
        recordings_dir=REPO / "recordings",
    )
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("FINSAGE_PORT", "8000")))


if __name__ == "__main__":
    main()
