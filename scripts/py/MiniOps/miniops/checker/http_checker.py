"""HTTP endpoint health checker. Reuses patterns from health-checker."""

from __future__ import annotations

import time

import requests

from miniops.checker.base import BaseChecker
from miniops.result import CheckResult


class HTTPChecker(BaseChecker):
    category = "http"

    def __init__(self, targets: list[dict], default_timeout: int = 10):
        self.targets = targets
        self.default_timeout = default_timeout

    def check(self) -> list[CheckResult]:
        results = []
        for target in self.targets:
            url = target["url"]
            timeout = target.get("timeout", self.default_timeout)
            expected_status = target.get("expected_status", "healthy")
            results.append(self._check_one(url, timeout, expected_status))
        return results

    def _check_one(
        self, url: str, timeout: int, expected_status: str | None
    ) -> CheckResult:
        start = time.monotonic()
        try:
            resp = requests.get(url, timeout=timeout)
            elapsed = (time.monotonic() - start) * 1000

            if not (200 <= resp.status_code < 400):
                return CheckResult(
                    name=url,
                    category=self.category,
                    success=False,
                    message=f"HTTP {resp.status_code}",
                    latency_ms=elapsed,
                )

            if expected_status:
                try:
                    body = resp.json()
                    actual = body.get("status", "")
                    if actual != expected_status:
                        return CheckResult(
                            name=url,
                            category=self.category,
                            success=False,
                            message=f"status={actual} (expected {expected_status})",
                            latency_ms=elapsed,
                            details=body,
                        )
                except (ValueError, KeyError):
                    pass

            return CheckResult(
                name=url,
                category=self.category,
                success=True,
                message=f"HTTP {resp.status_code} OK",
                latency_ms=elapsed,
            )

        except requests.Timeout:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=url,
                category=self.category,
                success=False,
                message=f"Timeout after {timeout}s",
                latency_ms=elapsed,
            )
        except requests.ConnectionError as e:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=url,
                category=self.category,
                success=False,
                message=f"Connection refused: {e}",
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return CheckResult(
                name=url,
                category=self.category,
                success=False,
                message=f"Unexpected error: {e}",
                latency_ms=elapsed,
            )
