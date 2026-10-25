"""Docker container health checker."""

import json
import subprocess
import time

from miniops.checker.base import BaseChecker
from miniops.result import CheckResult


class DockerChecker(BaseChecker):
    category = "docker"

    def __init__(self, name_filter: str = "task-api"):
        self.name_filter = name_filter

    def check(self) -> list[CheckResult]:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.name_filter}",
                 "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True, text=True, timeout=15,
            )
            elapsed = (time.monotonic() - start) * 1000

            if proc.returncode != 0:
                return [CheckResult(
                    name="docker",
                    category=self.category,
                    success=False,
                    message=f"docker ps failed: {proc.stderr.strip()}",
                    latency_ms=elapsed,
                )]

            results = []
            for line in proc.stdout.strip().splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                name = parts[0]
                status = parts[1] if len(parts) > 1 else "unknown"

                is_up = self._parse_status(status)
                results.append(CheckResult(
                    name=name,
                    category=self.category,
                    success=is_up,
                    message=status,
                    latency_ms=elapsed,
                    details={"raw_status": status},
                ))

            if not results:
                results.append(CheckResult(
                    name=f"docker-filter-{self.name_filter}",
                    category=self.category,
                    success=False,
                    message=f"No containers found matching '{self.name_filter}'",
                    latency_ms=elapsed,
                ))

            return results

        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            return [CheckResult(
                name="docker",
                category=self.category, success=False,
                message="docker ps timeout", latency_ms=elapsed,
            )]
        except FileNotFoundError:
            elapsed = (time.monotonic() - start) * 1000
            return [CheckResult(
                name="docker",
                category=self.category, success=False,
                message="docker command not found", latency_ms=elapsed,
            )]
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return [CheckResult(
                name="docker",
                category=self.category, success=False,
                message=f"docker check error: {e}", latency_ms=elapsed,
            )]

    @staticmethod
    def _parse_status(status: str) -> bool:
        lower = status.lower()
        if lower.startswith("up"):
            return True
        return False
