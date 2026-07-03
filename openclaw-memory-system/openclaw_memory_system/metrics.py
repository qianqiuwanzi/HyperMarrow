"""
HyperMarrow Observability Module
================================

Provides:
  - RPCMetrics: tracks latency, error rates, call counts per method
  - LatencyBreakdown: measures sub-operation latency within DC.check/record
  - HealthCheck: system health based on component availability + latency

Usage:
    from openclaw_memory_system.metrics import RPCMetrics, LatencyBreakdown

    metrics = RPCMetrics()
    with metrics.track("check"):
        result = dc.check(...)
    print(metrics.summary())
"""

import time
import threading
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass, field
import statistics


# ── RPC Metrics ────────────────────────────────────────────────────────────────
@dataclass
class MethodMetrics:
    """Per-method rolling metrics."""
    count: int = 0
    errors: int = 0
    total_ms: float = 0.0
    latencies_ms: list = field(default_factory=list)  # rolling window
    _lock: threading.Lock = field(default_factory=threading.Lock)

    MAX_WINDOW = 200  # keep last 200 latencies for percentile calc

    def record(self, latency_ms: float, error: bool = False):
        with self._lock:
            self.count += 1
            if error:
                self.errors += 1
            self.total_ms += latency_ms
            self.latencies_ms.append(latency_ms)
            if len(self.latencies_ms) > self.MAX_WINDOW:
                self.latencies_ms = self.latencies_ms[-self.MAX_WINDOW:]

    @property
    def mean_ms(self) -> float:
        with self._lock:
            return self.total_ms / self.count if self.count > 0 else 0.0

    @property
    def error_rate(self) -> float:
        with self._lock:
            return self.errors / self.count if self.count > 0 else 0.0

    @property
    def p50_ms(self) -> float:
        with self._lock:
            if not self.latencies_ms:
                return 0.0
            return float(statistics.median(self.latencies_ms))

    @property
    def p95_ms(self) -> float:
        with self._lock:
            if not self.latencies_ms:
                return 0.0
            sorted_lat = sorted(self.latencies_ms)
            idx = int(len(sorted_lat) * 0.95)
            return float(sorted_lat[min(idx, len(sorted_lat) - 1)])

    @property
    def p99_ms(self) -> float:
        with self._lock:
            if not self.latencies_ms:
                return 0.0
            sorted_lat = sorted(self.latencies_ms)
            idx = int(len(sorted_lat) * 0.99)
            return float(sorted_lat[min(idx, len(sorted_lat) - 1)])


class RPCMetrics:
    """
    Thread-safe RPC call metrics tracker.

    Tracks per-method: call count, error rate, mean/p50/p95/p99 latency.
    """

    def __init__(self):
        self._methods: dict[str, MethodMetrics] = defaultdict(MethodMetrics)
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._session_errors = 0

    def track(self, method: str, error: bool = False):
        """
        Context manager: records method call with timing.

        Usage:
            with metrics.track("check") as t:
                ...do work...
            # on exit, latency is recorded automatically
        """
        return _RPCCall(self, method)

    def record(self, method: str, latency_ms: float, error: bool = False):
        """Manually record a call result."""
        with self._lock:
            self._methods[method].record(latency_ms, error)
            if error:
                self._session_errors += 1

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    def summary(self) -> dict:
        """Return all metrics as a dict."""
        with self._lock:
            result = {
                "uptime_seconds": round(self.uptime_seconds, 1),
                "session_errors": self._session_errors,
                "methods": {},
            }
            for name, m in self._methods.items():
                result["methods"][name] = {
                    "count": m.count,
                    "errors": m.errors,
                    "error_rate": round(m.error_rate, 4),
                    "mean_ms": round(m.mean_ms, 3),
                    "p50_ms": round(m.p50_ms, 3),
                    "p95_ms": round(m.p95_ms, 3),
                    "p99_ms": round(m.p99_ms, 3),
                }
            return result

    def health_check(self) -> dict:
        """
        System health based on error rates and latency thresholds.

        Thresholds:
          - Error rate > 5%: DEGRADED
          - Mean latency > 2000ms: DEGRADED
          - Error rate > 20%: UNHEALTHY
          - p99 latency > 5000ms: DEGRADED
        """
        summary = self.summary()
        method_stats = summary["methods"]

        if not method_stats:
            return {"status": "INITIALIZING", "score": 0.0, "details": {}}

        issues = []
        score = 100.0

        for method, stats in method_stats.items():
            err_rate = stats["error_rate"]
            mean_ms = stats["mean_ms"]
            p99_ms = stats["p99_ms"]
            count = stats["count"]

            if count == 0:
                continue

            if err_rate > 0.2:
                issues.append(f"{method}: error_rate={err_rate:.0%} UNHEALTHY")
                score -= 40
            elif err_rate > 0.05:
                issues.append(f"{method}: error_rate={err_rate:.0%} DEGRADED")
                score -= 15

            if mean_ms > 5000:
                issues.append(f"{method}: mean={mean_ms:.0f}ms UNHEALTHY")
                score -= 20
            elif mean_ms > 2000:
                issues.append(f"{method}: mean={mean_ms:.0f}ms DEGRADED")
                score -= 10

            if p99_ms > 10000:
                issues.append(f"{method}: p99={p99_ms:.0f}ms DEGRADED")
                score -= 5

        score = max(0.0, min(100.0, score))
        if score >= 90 and not issues:
            status = "HEALTHY"
        elif score >= 60:
            status = "DEGRADED"
        else:
            status = "UNHEALTHY"

        return {
            "status": status,
            "score": round(score, 1),
            "uptime_seconds": round(self.uptime_seconds, 1),
            "total_calls": sum(m["count"] for m in method_stats.values()),
            "total_errors": sum(m["errors"] for m in method_stats.values()),
            "issues": issues[:10],
        }


class _RPCCall:
    """Context manager for RPC timing."""

    def __init__(self, metrics: RPCMetrics, method: str):
        self._metrics = metrics
        self._method = method
        self._t0: Optional[float] = None
        self._error = False

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency_ms = (time.perf_counter() - self._t0) * 1000
        error = exc_type is not None
        if error:
            self._error = True
        self._metrics.record(self._method, latency_ms, error)
        return False  # don't suppress exceptions


# ── Latency Breakdown ──────────────────────────────────────────────────────────
class LatencyBreakdown:
    """
    Measures sub-operation latency within a DC.check() or record() call.

    Usage:
        with LatencyBreakdown() as lb:
            lb.split("vector_search")
            results = vector_db.search(...)
            lb.split("kg_extract")
            entities = kg.extract(...)
        print(lb.summary())  # {"vector_search": 12.3, "kg_extract": 5.1, "total": 17.4}
    """

    def __init__(self):
        self._splits: list[tuple[str, float]] = []
        self._t0: Optional[float] = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        self._splits = []
        return self

    def __exit__(self, *args):
        return False

    def split(self, name: str):
        """Mark the end of a named sub-operation."""
        if self._t0 is None:
            return
        elapsed = (time.perf_counter() - self._t0) * 1000
        self._splits.append((name, elapsed))
        self._t0 = time.perf_counter()  # reset for next segment

    def summary(self) -> dict:
        """Return {name: ms, ...} dict with total appended."""
        result = {name: round(ms, 3) for name, ms in self._splits}
        result["_total_ms"] = round(sum(ms for _, ms in self._splits), 3)
        return result


# ── Global singleton ───────────────────────────────────────────────────────────
_metrics = RPCMetrics()


def get_metrics() -> RPCMetrics:
    """Get the global RPCMetrics singleton."""
    return _metrics
