"""MySQL health checker via docker exec."""

import subprocess
import time

from miniops.checker.base import BaseChecker
from miniops.result import CheckResult


class MySQLChecker(BaseChecker):
    category = "mysql"

    def __init__(self, targets: list[dict]):
        self.targets = targets

    def check(self) -> list[CheckResult]:
        results = []
        for target in self.targets:
            container = target["container"]
            password = target.get("password", "root_password")
            results.append(self._check_ping(container, password))
            if target.get("check_replication"):
                results.append(self._check_replication(container, password))
        return results

    def _check_ping(self, container: str, password: str) -> CheckResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["docker", "exec", container, "mysqladmin", "ping",
                 "-uroot", f"-p{password}"],
                capture_output=True, text=True, timeout=10,
            )
            elapsed = (time.monotonic() - start) * 1000

            if proc.returncode == 0 and "alive" in proc.stdout.lower():
                return CheckResult(
                    name=container,
                    category=self.category,
                    success=True,
                    message="MySQL ping OK",
                    latency_ms=elapsed,
                )
            return CheckResult(
                name=container,
                category=self.category,
                success=False,
                message=f"MySQL ping failed: {proc.stdout.strip() or proc.stderr.strip()}",
                latency_ms=elapsed,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=container, category=self.category, success=False,
                message="MySQL ping timeout", latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=container, category=self.category, success=False,
                message=f"MySQL ping error: {e}", latency_ms=elapsed,
            )

    def _check_replication(self, container: str, password: str) -> CheckResult:
        start = time.monotonic()
        try:
            proc = subprocess.run(
                ["docker", "exec", container, "mysql",
                 "-uroot", f"-p{password}", "-e",
                 "SHOW SLAVE STATUS\\G"],
                capture_output=True, text=True, timeout=10,
            )
            elapsed = (time.monotonic() - start) * 1000

            if proc.returncode != 0:
                return CheckResult(
                    name=f"{container}-replication",
                    category=self.category,
                    success=False,
                    message=f"Cannot check replication: {proc.stderr.strip()}",
                    latency_ms=elapsed,
                )

            output = proc.stdout
            io_running = "Slave_IO_Running: Yes" in output
            sql_running = "Slave_SQL_Running: Yes" in output

            seconds_behind = None
            for line in output.splitlines():
                if "Seconds_Behind_Master:" in line:
                    val = line.split(":")[1].strip()
                    seconds_behind = None if val == "NULL" else int(val)

            details = {
                "io_running": io_running,
                "sql_running": sql_running,
                "seconds_behind_master": seconds_behind,
            }

            if io_running and sql_running:
                return CheckResult(
                    name=f"{container}-replication",
                    category=self.category,
                    success=True,
                    message="Replication OK",
                    latency_ms=elapsed,
                    details=details,
                )
            return CheckResult(
                name=f"{container}-replication",
                category=self.category,
                success=False,
                message=f"Replication broken: IO={io_running}, SQL={sql_running}",
                latency_ms=elapsed,
                details=details,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=f"{container}-replication",
                category=self.category, success=False,
                message="Replication check timeout", latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=f"{container}-replication",
                category=self.category, success=False,
                message=f"Replication check error: {e}", latency_ms=elapsed,
            )
