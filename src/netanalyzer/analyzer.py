"""Core network analysis utilities."""

from __future__ import annotations

import dataclasses
import time
from typing import Dict, Iterable, List, Tuple


@dataclasses.dataclass(frozen=True)
class InterfaceStats:
    name: str
    rx_bytes: int
    rx_packets: int
    rx_errs: int
    rx_drop: int
    rx_fifo: int
    rx_frame: int
    rx_compressed: int
    rx_multicast: int
    tx_bytes: int
    tx_packets: int
    tx_errs: int
    tx_drop: int
    tx_fifo: int
    tx_colls: int
    tx_carrier: int
    tx_compressed: int


@dataclasses.dataclass(frozen=True)
class InterfaceInfo:
    name: str
    mtu: int | None
    speed_mbps: int | None
    operstate: str | None


@dataclasses.dataclass(frozen=True)
class ThroughputSample:
    name: str
    rx_bytes_per_sec: float
    tx_bytes_per_sec: float
    rx_packets_per_sec: float
    tx_packets_per_sec: float
    rx_errs_per_sec: float
    tx_errs_per_sec: float
    rx_drop_per_sec: float
    tx_drop_per_sec: float
    rx_multicast_per_sec: float
    speed_mbps: int | None


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
        stats[name] = InterfaceStats(
            name=name,
            rx_bytes=int(fields[0]),
            rx_packets=int(fields[1]),
            rx_errs=int(fields[2]),
            rx_drop=int(fields[3]),
            rx_fifo=int(fields[4]),
            rx_frame=int(fields[5]),
            rx_compressed=int(fields[6]),
            rx_multicast=int(fields[7]),
            tx_bytes=int(fields[8]),
            tx_packets=int(fields[9]),
            tx_errs=int(fields[10]),
            tx_drop=int(fields[11]),
            tx_fifo=int(fields[12]),
            tx_colls=int(fields[13]),
            tx_carrier=int(fields[14]),
            tx_compressed=int(fields[15]),
        )

    return stats


def _read_sysfs_value(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except (FileNotFoundError, OSError):
        return None


def read_interface_info(names: Iterable[str]) -> Dict[str, InterfaceInfo]:
    info: Dict[str, InterfaceInfo] = {}
    for name in names:
        base = f"/sys/class/net/{name}"
        mtu_value = _read_sysfs_value(f"{base}/mtu")
        speed_value = _read_sysfs_value(f"{base}/speed")
        operstate = _read_sysfs_value(f"{base}/operstate")
        mtu = int(mtu_value) if mtu_value and mtu_value.isdigit() else None
        speed = None
        if speed_value and speed_value.isdigit():
            speed = int(speed_value)
            if speed < 0:
                speed = None
        info[name] = InterfaceInfo(name=name, mtu=mtu, speed_mbps=speed, operstate=operstate)
    return info


def list_interfaces() -> List[str]:
    """Return the list of interface names found in /proc/net/dev."""
    return sorted(read_proc_net_dev().keys())


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
    info = read_interface_info(after.keys())
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
        rx_packets_rate = (after_stats.rx_packets - before_stats.rx_packets) / elapsed
        tx_packets_rate = (after_stats.tx_packets - before_stats.tx_packets) / elapsed
        rx_errs_rate = (after_stats.rx_errs - before_stats.rx_errs) / elapsed
        tx_errs_rate = (after_stats.tx_errs - before_stats.tx_errs) / elapsed
        rx_drop_rate = (after_stats.rx_drop - before_stats.rx_drop) / elapsed
        tx_drop_rate = (after_stats.tx_drop - before_stats.tx_drop) / elapsed
        rx_multicast_rate = (after_stats.rx_multicast - before_stats.rx_multicast) / elapsed
        info_stats = info.get(name)
        samples.append(
            ThroughputSample(
                name=name,
                rx_bytes_per_sec=max(rx_rate, 0.0),
                tx_bytes_per_sec=max(tx_rate, 0.0),
                rx_packets_per_sec=max(rx_packets_rate, 0.0),
                tx_packets_per_sec=max(tx_packets_rate, 0.0),
                rx_errs_per_sec=max(rx_errs_rate, 0.0),
                tx_errs_per_sec=max(tx_errs_rate, 0.0),
                rx_drop_per_sec=max(rx_drop_rate, 0.0),
                tx_drop_per_sec=max(tx_drop_rate, 0.0),
                rx_multicast_per_sec=max(rx_multicast_rate, 0.0),
                speed_mbps=info_stats.speed_mbps if info_stats else None,
            )
        )

    samples.sort(key=lambda item: item.rx_bytes_per_sec + item.tx_bytes_per_sec, reverse=True)
    return samples, elapsed


def summarize_samples(
    samples: Iterable[ThroughputSample],
    limit: int = 5,
    unit: str = "bytes",
    show_packets: bool = False,
    show_errors: bool = False,
    show_drops: bool = False,
    show_multicast: bool = False,
    show_utilization: bool = False,
) -> List[str]:
    """Format samples for display."""
    lines: List[str] = []
    for sample in list(samples)[:limit]:
        total = sample.rx_bytes_per_sec + sample.tx_bytes_per_sec
        parts = [
            f"{sample.name:<12}",
            f"RX {format_rate(sample.rx_bytes_per_sec, unit=unit):>12}",
            f"TX {format_rate(sample.tx_bytes_per_sec, unit=unit):>12}",
            f"TOTAL {format_rate(total, unit=unit):>12}",
        ]
        if show_packets:
            parts.append(
                f"PKTS {format_count_rate(sample.rx_packets_per_sec):>8}/"
                f"{format_count_rate(sample.tx_packets_per_sec):>8}"
            )
        if show_errors:
            parts.append(
                f"ERR {format_count_rate(sample.rx_errs_per_sec):>6}/"
                f"{format_count_rate(sample.tx_errs_per_sec):>6}"
            )
        if show_drops:
            parts.append(
                f"DROP {format_count_rate(sample.rx_drop_per_sec):>6}/"
                f"{format_count_rate(sample.tx_drop_per_sec):>6}"
            )
        if show_multicast:
            parts.append(f"MCAST {format_count_rate(sample.rx_multicast_per_sec):>6}")
        if show_utilization:
            parts.append(f"UTIL {format_utilization(sample):>6}")
        lines.append(" ".join(parts))
    return lines


def format_rate(rate_bytes: float, unit: str = "bytes") -> str:
    if unit not in {"bytes", "bits"}:
        raise ValueError("unit must be 'bytes' or 'bits'")
    multiplier = 8.0 if unit == "bits" else 1.0
    units = ["B/s", "KB/s", "MB/s", "GB/s", "TB/s"]
    if unit == "bits":
        units = ["b/s", "Kb/s", "Mb/s", "Gb/s", "Tb/s"]
    value = float(rate_bytes) * multiplier
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    return f"{value:6.2f} {units[index]}"


def format_count_rate(rate: float) -> str:
    return f"{rate:5.1f}/s"


def format_utilization(sample: ThroughputSample) -> str:
    if not sample.speed_mbps:
        return "n/a"
    total_bits = (sample.rx_bytes_per_sec + sample.tx_bytes_per_sec) * 8.0
    capacity = sample.speed_mbps * 1_000_000
    if capacity <= 0:
        return "n/a"
    utilization = min(total_bits / capacity * 100.0, 999.9)
    return f"{utilization:4.1f}%"
