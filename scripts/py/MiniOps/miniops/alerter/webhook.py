"""Webhook alerter for 企业微信/钉钉/飞书 etc."""

from __future__ import annotations

import json
import logging

import requests

from miniops.alerter.base import BaseAlerter
from miniops.result import Alert

logger = logging.getLogger(__name__)


class WebhookAlerter(BaseAlerter):
    """
    Sends alerts via HTTP webhook.

    Supported platforms (set `platform` in config):
    - wecom: 企业微信机器人
    - dingtalk: 钉钉机器人
    - feishu: 飞书机器人
    - generic: 通用 JSON POST

    NOTE: This alerter is DISABLED by default. To enable:
    1. Set WEBHOOK_URL environment variable or configure url in config/default.yaml
    2. Set enabled: true in config
    """

    def __init__(self, url: str, platform: str = "generic",
                 enabled: bool = False, trigger_on: list[str] | None = None):
        super().__init__(enabled=enabled, trigger_on=trigger_on)
        self.url = url
        self.platform = platform

    def send(self, alert: Alert) -> bool:
        if not self.should_send(alert):
            logger.debug("Webhook alerter disabled or level not in trigger_on, skipping")
            return False

        if not self.url:
            logger.warning("Webhook URL not configured, skipping alert")
            return False

        payload = self._build_payload(alert)

        try:
            resp = requests.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if resp.status_code < 300:
                logger.info("Webhook alert sent: %s", alert.message)
                return True
            logger.error("Webhook failed: HTTP %d - %s", resp.status_code, resp.text)
            return False
        except requests.RequestException as e:
            logger.error("Webhook request error: %s", e)
            return False

    def _build_payload(self, alert: Alert) -> dict:
        """
        Build platform-specific payload.

        For production use, customize the payload format per your webhook provider:
        - 企业微信: {"msgtype": "markdown", "markdown": {"content": "..."}}
        - 钉钉: {"msgtype": "markdown", "markdown": {"title": "...", "text": "..."}}
        - 飞书: {"msg_type": "interactive", "card": {...}}
        - generic: {"level": "...", "source": "...", "message": "..."}
        """
        text = self._format_alert_text(alert)

        if self.platform == "wecom":
            return {
                "msgtype": "markdown",
                "markdown": {"content": text},
            }
        elif self.platform == "dingtalk":
            return {
                "msgtype": "markdown",
                "markdown": {"title": f"[MiniOps {alert.level.upper()}]", "text": text},
            }
        elif self.platform == "feishu":
            return {
                "msg_type": "text",
                "content": {"text": text},
            }
        else:
            return alert.to_dict()

    @staticmethod
    def _format_alert_text(alert: Alert) -> str:
        return (
            f"**[MiniOps {alert.level.upper()}]**\n"
            f"- Source: {alert.source}\n"
            f"- Message: {alert.message}\n"
            f"- Time: {alert.timestamp}"
        )
