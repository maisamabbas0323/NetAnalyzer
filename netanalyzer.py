"""Convenience entrypoint for `python3 netanalyzer.py` or `python3 -m netanalyzer`."""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
_PKG = _SRC / "netanalyzer"

if _SRC.exists():
    sys.path.insert(0, str(_SRC))
    __path__ = [str(_PKG)]

from netanalyzer.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
