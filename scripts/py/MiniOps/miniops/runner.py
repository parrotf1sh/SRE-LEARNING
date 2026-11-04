"""Orchestrator: runs all checkers and collects results."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from miniops.checker.base import BaseChecker
from miniops.checker.http_checker import HTTPChecker
from miniops.checker.mysql_checker import MySQLChecker
from miniops.checker.redis_checker import RedisChecker
from miniops.checker.docker_checker import DockerChecker
from miniops.checker.system_checker import SystemChecker
from miniops.result import CheckResult, Alert

logger = logging.getLogger(__name__)


class Runner:
    """Runs all configured checkers and produces results + alerts."""

    def __init__(self, config: dict):
        self.config = config
        self.checkers = self._build_checkers(config)

    def _build_checkers(self, config: dict) -> list[BaseChecker]:
        checkers = []
        targets = config.get("targets", {})

        if targets.get("http"):
            checkers.append(HTTPChecker(
                targets=targets["http"],
                default_timeout=config.get("defaults", {}).get("timeout", 10),
            ))

        if targets.get("mysql"):
            checkers.append(MySQLChecker(targets=targets["mysql"]))

        if targets.get("redis"):
            checkers.append(RedisChecker(targets=targets["redis"]))

        docker_cfg = targets.get("docker", {})
        if docker_cfg.get("enabled", True):
            checkers.append(DockerChecker(
                name_filter=docker_cfg.get("name_filter", "task-api"),
            ))

        if targets.get("system", {}).get("enabled", True):
            thresholds = targets.get("system", {})
            checkers.append(SystemChecker(thresholds=thresholds))

        return checkers

    def run(self, categories: list[str] | None = None,
            max_workers: int = 5) -> list[CheckResult]:
        """Run all (or filtered) checkers concurrently."""
        checkers = self.checkers
        if categories:
            checkers = [c for c in checkers if c.category in categories]

        all_results = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(c.check): c for c in checkers}
            for future in as_completed(futures):
                checker = futures[future]
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    logger.error("Checker %s crashed: %s", checker.category, e)
                    all_results.append(CheckResult(
                        name=checker.category,
                        category=checker.category,
                        success=False,
                        message=f"Checker crashed: {e}",
                    ))

        return all_results

    def generate_alerts(self, results: list[CheckResult]) -> list[Alert]:
        """Convert failed checks into alerts."""
        alerts = []
        for r in results:
            if r.success:
                continue

            level = "warning"
            if r.category in ("mysql", "redis", "docker"):
                level = "critical"
            elif r.category == "http":
                level = "critical"
            elif r.category == "system":
                if r.details.get("level") == "critical":
                    level = "critical"

            alerts.append(Alert(
                level=level,
                source=r.name,
                message=r.message,
                details=r.details,
            ))
        return alerts
