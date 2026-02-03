"""Command-line interface for NetAnalyzer."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

from netanalyzer.analyzer import sample_throughput, summarize_samples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Real-time network throughput monitoring via /proc/net/dev.",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=1.0,
        help="Sampling interval in seconds (default: 1.0).",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=0,
        help="Number of samples to capture (0 = infinite).",
    )
    parser.add_argument(
        "-t",
        "--top",
        type=int,
        default=5,
        help="Number of interfaces to display per sample.",
    )
    parser.add_argument(
        "--interfaces",
        nargs="*",
        default=None,
        help="Specific interface names to monitor.",
    )
    return parser


def render(samples: Iterable[str], elapsed: float) -> None:
    print(f"\nSample over {elapsed:.2f}s")
    print("=" * 54)
    for line in samples:
        print(line)


def run(interval: float, count: int, top: int, interfaces: Iterable[str] | None) -> int:
    iterations = 0
    try:
        while True:
            samples, elapsed = sample_throughput(interval=interval, interfaces=interfaces)
            render(summarize_samples(samples, limit=top), elapsed)
            iterations += 1
            if count and iterations >= count:
                break
    except KeyboardInterrupt:
        print("\nStopping NetAnalyzer.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.interval <= 0:
        parser.error("interval must be greater than zero")
    if args.top <= 0:
        parser.error("top must be greater than zero")
    if args.count < 0:
        parser.error("count must be zero or positive")
    return run(args.interval, args.count, args.top, args.interfaces)


if __name__ == "__main__":
    sys.exit(main())
