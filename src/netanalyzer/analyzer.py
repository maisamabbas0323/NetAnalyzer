"""Core network analysis utilities."""

from __future__ import annotations

import dataclasses
import time
from typing import Dict, Iterable, List, Tuple


@dataclasses.dataclass(frozen=True)
class InterfaceStats:
    name: str
    rx_bytes: int
    tx_bytes: int


@dataclasses.dataclass(frozen=True)
class ThroughputSample:
    name: str
    rx_bytes_per_sec: float
    tx_bytes_per_sec: float


def read_proc_net_dev() -> Dict[str, InterfaceStats]:
    """Read /proc/net/dev and return per-interface totals.

    This is Linux-specific and uses only the standard library.
    """
    stats: Dict[str, InterfaceStats] = {}
    with open("/proc/net/dev", "r", encoding="utf-8") as handle:
        lines = handle.readlines()

    for line in lines[2:]:
        if ":" not in line:
            continue
        name_part, data_part = line.split(":", 1)
        name = name_part.strip()
        fields = data_part.split()
        if len(fields) < 9:
            continue
        rx_bytes = int(fields[0])
        tx_bytes = int(fields[8])
        stats[name] = InterfaceStats(name=name, rx_bytes=rx_bytes, tx_bytes=tx_bytes)

    return stats


def sample_throughput(
    interval: float = 1.0,
    interfaces: Iterable[str] | None = None,
) -> Tuple[List[ThroughputSample], float]:
    """Return throughput samples for interfaces over an interval.

    Returns a tuple of (samples, elapsed_seconds).
    """
    start = time.perf_counter()
    before = read_proc_net_dev()
    time.sleep(interval)
    after = read_proc_net_dev()
    end = time.perf_counter()
    elapsed = max(end - start, 1e-6)

    selected = set(interfaces) if interfaces else None
    samples: List[ThroughputSample] = []

    for name, after_stats in after.items():
        if selected and name not in selected:
            continue
        before_stats = before.get(name)
        if not before_stats:
            continue
        rx_rate = (after_stats.rx_bytes - before_stats.rx_bytes) / elapsed
        tx_rate = (after_stats.tx_bytes - before_stats.tx_bytes) / elapsed
        samples.append(
            ThroughputSample(
                name=name,
                rx_bytes_per_sec=max(rx_rate, 0.0),
                tx_bytes_per_sec=max(tx_rate, 0.0),
            )
        )

    samples.sort(key=lambda item: item.rx_bytes_per_sec + item.tx_bytes_per_sec, reverse=True)
    return samples, elapsed


def summarize_samples(samples: Iterable[ThroughputSample], limit: int = 5) -> List[str]:
    """Format samples for display."""
    lines: List[str] = []
    for sample in list(samples)[:limit]:
        total = sample.rx_bytes_per_sec + sample.tx_bytes_per_sec
        lines.append(
            f"{sample.name:<12} RX {format_rate(sample.rx_bytes_per_sec):>10} "
            f"TX {format_rate(sample.tx_bytes_per_sec):>10} "
            f"TOTAL {format_rate(total):>10}"
        )
    return lines


def format_rate(rate_bytes: float) -> str:
    units = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]
    value = float(rate_bytes)
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    return f"{value:6.2f} {units[index]}"
