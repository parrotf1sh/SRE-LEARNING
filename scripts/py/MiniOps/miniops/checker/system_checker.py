"""System resource checker (disk + memory)."""

from __future__ import annotations

import shutil

from miniops.checker.base import BaseChecker
from miniops.result import CheckResult


class SystemChecker(BaseChecker):
    category = "system"

    def __init__(self, thresholds: dict | None = None):
        self.thresholds = thresholds or {"disk_warn": 85, "disk_crit": 95,
                                         "mem_warn": 85, "mem_crit": 95}

    def check(self) -> list[CheckResult]:
        results = []
        results.extend(self._check_disk())
        results.extend(self._check_memory())
        return results

    def _check_disk(self) -> list[CheckResult]:
        results = []
        for path in ["/", "/home"]:
            try:
                usage = shutil.disk_usage(path)
                pct = usage.used / usage.total * 100
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)

                level = self._level(pct, "disk")
                success = level != "critical"
                msg = f"{pct:.1f}% used ({used_gb:.1f}/{total_gb:.1f} GB)"

                results.append(CheckResult(
                    name=f"disk-{path}",
                    category=self.category,
                    success=success,
                    message=msg,
                    details={
                        "path": path, "total_gb": round(total_gb, 2),
                        "used_gb": round(used_gb, 2), "free_gb": round(free_gb, 2),
                        "percent": round(pct, 1), "level": level,
                    },
                ))
            except Exception as e:
                results.append(CheckResult(
                    name=f"disk-{path}",
                    category=self.category,
                    success=False,
                    message=f"Cannot check disk {path}: {e}",
                ))
        return results

    def _check_memory(self) -> list[CheckResult]:
        try:
            import psutil
            mem = psutil.virtual_memory()
            pct = mem.percent
            total_gb = mem.total / (1024**3)
            used_gb = mem.used / (1024**3)
            available_gb = mem.available / (1024**3)

            level = self._level(pct, "mem")
            success = level != "critical"
            msg = f"{pct:.1f}% used ({used_gb:.1f}/{total_gb:.1f} GB)"

            return [CheckResult(
                name="memory",
                category=self.category,
                success=success,
                message=msg,
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "percent": pct, "level": level,
                },
            )]
        except ImportError:
            return [self._check_memory_fallback()]
        except Exception as e:
            return [CheckResult(
                name="memory", category=self.category, success=False,
                message=f"Memory check error: {e}",
            )]

    def _check_memory_fallback(self) -> CheckResult:
        """Fallback when psutil is not installed: parse /proc/meminfo."""
        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
            info = {}
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    info[key] = int(val) * 1024  # kB -> bytes

            total = info.get("MemTotal", 0)
            available = info.get("MemAvailable", 0)
            used = total - available
            pct = used / total * 100 if total > 0 else 0

            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            available_gb = available / (1024**3)

            level = self._level(pct, "mem")
            return CheckResult(
                name="memory",
                category=self.category,
                success=level != "critical",
                message=f"{pct:.1f}% used ({used_gb:.1f}/{total_gb:.1f} GB)",
                details={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "percent": round(pct, 1), "level": level,
                },
            )
        except Exception as e:
            return CheckResult(
                name="memory", category=self.category, success=False,
                message=f"Cannot read /proc/meminfo: {e}",
            )

    def _level(self, pct: float, prefix: str) -> str:
        crit_key = f"{prefix}_crit"
        warn_key = f"{prefix}_warn"
        if pct >= self.thresholds.get(crit_key, 95):
            return "critical"
        if pct >= self.thresholds.get(warn_key, 85):
            return "warning"
        return "ok"
