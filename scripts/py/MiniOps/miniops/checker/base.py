"""Base class for all health checkers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from miniops.result import CheckResult


class BaseChecker(ABC):
    """All checkers implement this interface."""

    category: str = "base"

    @abstractmethod
    def check(self) -> list[CheckResult]:
        ...

    def check_with_retry(self, max_retries: int = 0) -> list[CheckResult]:
        import time

        for attempt in range(max_retries + 1):
            results = self.check()
            if all(r.success for r in results) or attempt == max_retries:
                return results
            time.sleep(2**attempt)
        return results
