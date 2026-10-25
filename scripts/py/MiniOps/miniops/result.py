"""Data structures for check results and alerts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CheckResult:
    name: str
    category: str
    success: bool
    message: str
    latency_ms: float = 0.0
    details: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "success": self.success,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class Alert:
    level: str  # "warning" | "critical"
    source: str
    message: str
    details: dict = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "source": self.source,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }
