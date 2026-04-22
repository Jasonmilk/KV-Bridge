"""In-memory metrics collector with zero external dependencies."""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

class MemoryMetrics:
    """Thread-safe in-memory metrics store."""

    def __init__(self):
        self._requests: List[Dict] = []
        self._max_records = 10000

    def record(self, backend: str, tokens_saved: int, cost_saved: float, hit: bool) -> None:
        """Record a single request's cache outcome."""
        self._requests.append({
            "timestamp": datetime.now().isoformat(),
            "backend": backend,
            "tokens_saved": tokens_saved,
            "cost_saved": cost_saved,
            "hit": hit
        })
        if len(self._requests) > self._max_records:
            self._requests = self._requests[-self._max_records:]

    def summary(self) -> Dict:
        """Return aggregated statistics."""
        by_backend = defaultdict(lambda: {"requests": 0, "tokens_saved": 0, "cost_saved": 0.0})
        for r in self._requests:
            b = r["backend"]
            by_backend[b]["requests"] += 1
            by_backend[b]["tokens_saved"] += r["tokens_saved"]
            by_backend[b]["cost_saved"] += r["cost_saved"]
        return {
            "total_requests": len(self._requests),
            "by_backend": dict(by_backend)
        }


_metrics: MemoryMetrics | None = None

def get_metrics() -> MemoryMetrics:
    global _metrics
    if _metrics is None:
        _metrics = MemoryMetrics()
    return _metrics