"""Command-line interface for NetAnalyzer."""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

from netanalyzer.analyzer import (
    list_interfaces,
    read_interface_info,
    sample_throughput,
    summarize_samples,
)


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
    parser.add_argument(
        "--unit",
        choices=["bytes", "bits"],
        default="bytes",
        help="Display rates in bytes or bits (default: bytes).",
    )
    parser.add_argument(
        "--sort",
        choices=["total", "rx", "tx", "rx-pkts", "tx-pkts"],
        default="total",
        help="Sort interfaces by throughput or packet rates.",
    )
    parser.add_argument(
        "--show-packets",
        action="store_true",
        help="Include packet rates in the output.",
    )
    parser.add_argument(
        "--show-errors",
        action="store_true",
        help="Include error rates in the output.",
    )
    parser.add_argument(
        "--show-drops",
        action="store_true",
        help="Include drop rates in the output.",
    )
    parser.add_argument(
        "--show-multicast",
        action="store_true",
        help="Include multicast receive rates in the output.",
    )
    parser.add_argument(
        "--show-utilization",
        action="store_true",
        help="Include utilization estimates when link speed is known.",
    )
    parser.add_argument(
        "--show-total",
        action="store_true",
        help="Include an aggregate total line across interfaces.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show interface details (state, MTU, speed) before samples.",
    )
    parser.add_argument(
        "--list-interfaces",
        action="store_true",
        help="List detected interfaces and exit.",
    )
    return parser


def render(samples: Iterable[str], elapsed: float) -> None:
    print(f"\nSample over {elapsed:.2f}s")
    print("=" * 54)
    for line in samples:
        print(line)


def _sort_samples(samples, mode: str):
    if mode == "rx":
        key = lambda item: item.rx_bytes_per_sec
    elif mode == "tx":
        key = lambda item: item.tx_bytes_per_sec
    elif mode == "rx-pkts":
        key = lambda item: item.rx_packets_per_sec
    elif mode == "tx-pkts":
        key = lambda item: item.tx_packets_per_sec
    else:
        key = lambda item: item.rx_bytes_per_sec + item.tx_bytes_per_sec
    return sorted(samples, key=key, reverse=True)


def _aggregate_sample(samples):
    total_rx = sum(sample.rx_bytes_per_sec for sample in samples)
    total_tx = sum(sample.tx_bytes_per_sec for sample in samples)
    total_rx_pkts = sum(sample.rx_packets_per_sec for sample in samples)
    total_tx_pkts = sum(sample.tx_packets_per_sec for sample in samples)
    total_rx_errs = sum(sample.rx_errs_per_sec for sample in samples)
    total_tx_errs = sum(sample.tx_errs_per_sec for sample in samples)
    total_rx_drop = sum(sample.rx_drop_per_sec for sample in samples)
    total_tx_drop = sum(sample.tx_drop_per_sec for sample in samples)
    total_rx_mcast = sum(sample.rx_multicast_per_sec for sample in samples)
    return type(samples[0])(
        name="TOTAL",
        rx_bytes_per_sec=total_rx,
        tx_bytes_per_sec=total_tx,
        rx_packets_per_sec=total_rx_pkts,
        tx_packets_per_sec=total_tx_pkts,
        rx_errs_per_sec=total_rx_errs,
        tx_errs_per_sec=total_tx_errs,
        rx_drop_per_sec=total_rx_drop,
        tx_drop_per_sec=total_tx_drop,
        rx_multicast_per_sec=total_rx_mcast,
        speed_mbps=None,
    )


def _render_details(interfaces: Iterable[str]) -> None:
    info = read_interface_info(interfaces)
    print("Interface details")
    print("=" * 54)
    for name in sorted(info):
        details = info[name]
        mtu = details.mtu if details.mtu is not None else "n/a"
        speed = f"{details.speed_mbps}Mb/s" if details.speed_mbps else "n/a"
        state = details.operstate or "n/a"
        print(f"{name:<12} state={state:<8} mtu={mtu:<6} speed={speed}")


def run(
    interval: float,
    count: int,
    top: int,
    interfaces: Iterable[str] | None,
    unit: str,
    sort_mode: str,
    show_packets: bool,
    show_errors: bool,
    show_drops: bool,
    show_multicast: bool,
    show_utilization: bool,
    show_total: bool,
    show_details: bool,
) -> int:
    iterations = 0
    if show_details:
        interface_list = list(interfaces or list_interfaces())
        if interface_list:
            _render_details(interface_list)
    try:
        while True:
            samples, elapsed = sample_throughput(interval=interval, interfaces=interfaces)
            if not samples:
                print("No interfaces matched the provided filters.")
                return 1
            ordered = _sort_samples(samples, sort_mode)
            if show_total:
                ordered = [*ordered, _aggregate_sample(ordered)]
            render(
                summarize_samples(
                    ordered,
                    limit=top if not show_total else max(top, len(ordered)),
                    unit=unit,
                    show_packets=show_packets,
                    show_errors=show_errors,
                    show_drops=show_drops,
                    show_multicast=show_multicast,
                    show_utilization=show_utilization,
                ),
                elapsed,
            )
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
    if args.list_interfaces:
        interface_names = args.interfaces or list_interfaces()
        if not interface_names:
            print("No interfaces detected.")
            return 1
        interfaces = read_interface_info(interface_names)
        print("Interfaces")
        print("=" * 54)
        for name in sorted(interfaces):
            details = interfaces[name]
            mtu = details.mtu if details.mtu is not None else "n/a"
            speed = f"{details.speed_mbps}Mb/s" if details.speed_mbps else "n/a"
            state = details.operstate or "n/a"
            print(f"{name:<12} state={state:<8} mtu={mtu:<6} speed={speed}")
        return 0
    return run(
        args.interval,
        args.count,
        args.top,
        args.interfaces,
        args.unit,
        args.sort,
        args.show_packets,
        args.show_errors,
        args.show_drops,
        args.show_multicast,
        args.show_utilization,
        args.show_total,
        args.details,
    )


if __name__ == "__main__":
    sys.exit(main())
