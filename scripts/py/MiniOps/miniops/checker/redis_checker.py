"""Redis Cluster health checker via docker exec."""

from __future__ import annotations

import subprocess
import time

from miniops.checker.base import BaseChecker
from miniops.result import CheckResult


class RedisChecker(BaseChecker):
    category = "redis"

    def __init__(self, targets: list[dict]):
        self.targets = targets

    def check(self) -> list[CheckResult]:
        results = []
        for target in self.targets:
            container = target["container"]
            port = target["port"]
            results.append(self._check_ping(container, port))

        cluster_result = self._check_cluster_state()
        if cluster_result:
            results.append(cluster_result)
        return results

    def _check_ping(self, container: str, port: int) -> CheckResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["docker", "exec", container, "redis-cli", "-p", str(port), "ping"],
                capture_output=True, text=True, timeout=10,
            )
            elapsed = (time.monotonic() - start) * 1000

            if proc.returncode == 0 and "PONG" in proc.stdout:
                return CheckResult(
                    name=f"{container}:{port}",
                    category=self.category,
                    success=True,
                    message="Redis PING OK",
                    latency_ms=elapsed,
                )
            return CheckResult(
                name=f"{container}:{port}",
                category=self.category,
                success=False,
                message=f"Redis PING failed: {proc.stdout.strip() or proc.stderr.strip()}",
                latency_ms=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=f"{container}:{port}",
                category=self.category, success=False,
                message="Redis PING timeout", latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=f"{container}:{port}",
                category=self.category, success=False,
                message=f"Redis PING error: {e}", latency_ms=elapsed,
            )

    def _check_cluster_state(self) -> CheckResult | None:
        if not self.targets:
            return None

        first = self.targets[0]
        container = first["container"]
        port = first["port"]
        start = time.monotonic()

        try:
            proc = subprocess.run(
                ["docker", "exec", container, "redis-cli", "-p", str(port),
                 "cluster", "info"],
                capture_output=True, text=True, timeout=10,
            )
            elapsed = (time.monotonic() - start) * 1000

            if proc.returncode != 0:
                return CheckResult(
                    name="redis-cluster",
                    category=self.category,
                    success=False,
                    message=f"CLUSTER INFO failed: {proc.stderr.strip()}",
                    latency_ms=elapsed,
                )

            output = proc.stdout
            state = "unknown"
            known_nodes = 0
            cluster_size = 0

            for line in output.splitlines():
                if line.startswith("cluster_state:"):
                    state = line.split(":")[1].strip()
                elif line.startswith("cluster_known_nodes:"):
                    known_nodes = int(line.split(":")[1].strip())
                elif line.startswith("cluster_size:"):
                    cluster_size = int(line.split(":")[1].strip())

            details = {
                "cluster_state": state,
                "cluster_known_nodes": known_nodes,
                "cluster_size": cluster_size,
            }

            if state == "ok":
                return CheckResult(
                    name="redis-cluster",
                    category=self.category,
                    success=True,
                    message=f"Cluster OK ({known_nodes} nodes, {cluster_size} masters)",
                    latency_ms=elapsed,
                    details=details,
                )
            return CheckResult(
                name="redis-cluster",
                category=self.category,
                success=False,
                message=f"Cluster state: {state}",
                latency_ms=elapsed,
                details=details,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name="redis-cluster",
                category=self.category, success=False,
                message="CLUSTER INFO timeout", latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name="redis-cluster",
                category=self.category, success=False,
                message=f"CLUSTER INFO error: {e}", latency_ms=elapsed,
            )
