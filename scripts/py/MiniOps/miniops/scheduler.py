"""Daemon scheduler for periodic health checks."""

from __future__ import annotations

import logging
import signal
import threading
import time

from miniops.runner import Runner
from miniops.reporter import Reporter
from miniops.alerter.webhook import WebhookAlerter
from miniops.alerter.email_alerter import EmailAlerter

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Runs health checks at a fixed interval.

    Usage:
        scheduler = Scheduler(config)
        scheduler.start()  # blocks until SIGINT/SIGTERM
    """

    def __init__(self, config: dict):
        self.config = config
        sched_cfg = config.get("scheduler", {})
        self.interval = sched_cfg.get("interval_seconds", 300)
        self.log_file = sched_cfg.get("log_file", "miniops.log")
        self.runner = Runner(config)
        self.reporter = Reporter()
        self.alerters = self._build_alerters(config)
        self._stop_event = threading.Event()

    def _build_alerters(self, config: dict) -> list:
        alerters = []
        for ch in config.get("alerting", {}).get("channels", []):
            if ch.get("type") == "webhook":
                alerters.append(WebhookAlerter(
                    url=ch.get("url", ""),
                    platform=ch.get("platform", "generic"),
                    enabled=ch.get("enabled", False),
                    trigger_on=ch.get("trigger_on", ["critical"]),
                ))
            elif ch.get("type") == "email":
                alerters.append(EmailAlerter(
                    smtp_host=ch.get("smtp_host", ""),
                    smtp_port=ch.get("smtp_port", 465),
                    username=ch.get("username", ""),
                    password=ch.get("password", ""),
                    recipients=ch.get("recipients", []),
                    use_tls=ch.get("use_tls", True),
                    enabled=ch.get("enabled", False),
                    trigger_on=ch.get("trigger_on", ["critical"]),
                ))
        return alerters

    def start(self):
        """Start the daemon loop. Blocks until interrupted."""
        logger.info("MiniOps daemon starting (interval=%ds)", self.interval)

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        self._run_once()

        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.interval)
            if not self._stop_event.is_set():
                self._run_once()

        logger.info("MiniOps daemon stopped")

    def stop(self):
        self._stop_event.set()

    def _handle_signal(self, signum, frame):
        logger.info("Received signal %d, stopping...", signum)
        self.stop()

    def _run_once(self):
        logger.info("Running scheduled health check...")
        results = self.runner.run()
        alerts = self.runner.generate_alerts(results)

        self.reporter.print_table(results)

        try:
            self.reporter.write_log(results, self.log_file)
        except Exception as e:
            logger.error("Failed to write log: %s", e)

        for alert in alerts:
            logger.warning("ALERT [%s] %s: %s", alert.level, alert.source, alert.message)
            for alerter in self.alerters:
                try:
                    alerter.send(alert)
                except Exception as e:
                    logger.error("Alerter %s failed: %s", type(alerter).__name__, e)
