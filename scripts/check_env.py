#!/usr/bin/env python3
"""Check the minimal runtime needed by the whiteboard renderer."""

from __future__ import annotations

import importlib.util
import shutil
import sys


def main() -> int:
    missing: list[str] = []
    for module, package in (("PIL", "Pillow"), ("numpy", "numpy")):
        if importlib.util.find_spec(module) is None:
            missing.append(package)

    edge_available = importlib.util.find_spec("edge_tts") is not None
    if not edge_available:
        missing.append("edge-tts")

    ffmpeg = shutil.which("ffmpeg")
    imageio = importlib.util.find_spec("imageio_ffmpeg") is not None
    if not ffmpeg and not imageio:
        missing.append("imageio-ffmpeg")

    if missing:
        joined = " ".join(dict.fromkeys(missing))
        print("Missing runtime dependencies:", joined)
        print("Create a project-local environment and install them with:")
        print("  python3 -m venv .whiteboard-venv")
        print("  .whiteboard-venv/bin/python -m pip install", joined)
        return 1

    print("Python:", sys.executable)
    print("Pillow: available")
    print("NumPy: available")
    print("Edge TTS:", "available" if edge_available else "not installed")
    print("FFmpeg:", ffmpeg or "provided by imageio-ffmpeg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
