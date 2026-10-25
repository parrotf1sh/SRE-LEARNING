"""Base class for alerters."""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from miniops.result import Alert

logger = logging.getLogger(__name__)


class BaseAlerter(ABC):
    """All alert channels implement this interface."""

    def __init__(self, enabled: bool = False, trigger_on: list[str] | None = None):
        self.enabled = enabled
        self.trigger_on = trigger_on or ["critical"]

    @abstractmethod
    def send(self, alert: Alert) -> bool:
        ...

    def should_send(self, alert: Alert) -> bool:
        if not self.enabled:
            return False
        return alert.level in self.trigger_on
