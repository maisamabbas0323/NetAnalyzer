# NetAnalyzer

NetAnalyzer is a lightweight, real-time network throughput monitor built with pure Python. It reads live interface counters from `/proc/net/dev` and turns them into human-friendly rates, making it easy to understand what's happening on your system in the moment.

> "Number one in the world" is a bold goal — this project is designed to be clear, fast, and dependable, giving you a strong foundation to build on for dashboards, alerts, and deep network visibility.

## Features

- **Real-time sampling** of RX/TX throughput per interface.
- **Packets, errors, drops, and multicast rates** on demand.
- **Interface utilization estimates** when link speed is known.
- **Sorting and filtering** by interface or traffic direction.
- **Interface detail inspection** (state, MTU, speed).
- **Aggregate totals** across all interfaces.
- **Zero external dependencies** (Linux `/proc` only).
- **CLI-first workflow** with clean, readable output.
- **Extensible Python API** for integrating into other tools.

## Requirements

- Linux environment with `/proc/net/dev` available.
- Python 3.10+.

## Installation

```bash
python -m pip install -e .
```

## Quick start

Run the CLI and watch live throughput updates:

```bash
python3 netanalyzer.py --interval 1 --top 5
```

Sample output:

```
Sample over 1.00s
======================================================
eth0         RX   12.32 KB/s TX    3.11 KB/s TOTAL   15.43 KB/s
lo           RX    0.00 B/s  TX    0.00 B/s  TOTAL    0.00 B/s
```

You can also run the module directly:

```bash
python3 -m netanalyzer --interval 1 --top 5
```

### Target specific interfaces

```bash
python3 netanalyzer.py --interfaces eth0 wlan0 --interval 0.5 --top 2
```

### Capture a fixed number of samples

```bash
python3 netanalyzer.py --count 10 --interval 2
```

### Show real-time packet, error, and drop rates

```bash
python3 netanalyzer.py --show-packets --show-errors --show-drops --interval 1
```

### Include utilization estimates and aggregate totals

```bash
python3 netanalyzer.py --show-utilization --show-total --interval 1
```

### List interfaces and inspect details

```bash
python3 netanalyzer.py --list-interfaces
python3 netanalyzer.py --details --interval 1 --count 1
```

## CLI options (all functionality)

Use any of these options with `python3 netanalyzer.py` or `python3 -m netanalyzer`:

- `-i`, `--interval`: Sampling interval in seconds.
- `-c`, `--count`: Number of samples to capture (`0` = infinite).
- `-t`, `--top`: Number of interfaces to display per sample.
- `--interfaces`: Space-separated interface names to monitor.
- `--unit`: Display rates in `bytes` or `bits`.
- `--sort`: Sort by `total`, `rx`, `tx`, `rx-pkts`, or `tx-pkts`.
- `--show-packets`: Include packet rates in output.
- `--show-errors`: Include error rates in output.
- `--show-drops`: Include drop rates in output.
- `--show-multicast`: Include multicast receive rates in output.
- `--show-utilization`: Include utilization estimates when link speed is known.
- `--show-total`: Include an aggregate total line across interfaces.
- `--details`: Show interface details (state, MTU, speed) before samples.
- `--list-interfaces`: List detected interfaces and exit.

## Python API

```python
from netanalyzer.analyzer import sample_throughput, summarize_samples

samples, elapsed = sample_throughput(interval=1.0)
for line in summarize_samples(samples, limit=3):
    print(line)
```

## Roadmap (aspirational)

- Live charts and dashboards.
- Top talkers by process (requires elevated permissions).
- Exporters for Prometheus / OpenTelemetry.
- Anomaly detection and alerting.

## Contributing

Ideas and improvements are welcome! If you want to help push this toward world-class quality:

1. Open an issue with ideas or bug reports.
2. Propose enhancements with clear benchmarks.
3. Share real-world usage insights.

## License

MIT
