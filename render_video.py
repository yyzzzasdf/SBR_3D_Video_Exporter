"""Standalone entry point; imports only this directory's src package."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from video_export.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
