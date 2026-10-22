"""Alert logic for disk analyzer."""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Represents a disk usage alert."""
    level: str  # 'WARNING', 'CRITICAL'
    mount_point: str
    usage_percent: float
    threshold: float
    message: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'level': self.level,
            'mount_point': self.mount_point,
            'usage_percent': self.usage_percent,
            'threshold': self.threshold,
            'message': self.message
        }


class AlertManager:
    """Manage disk usage alerts."""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 90.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.alerts: List[Alert] = []
        
        logger.debug(
            f"AlertManager initialized: warning={self.warning_threshold}%, "
            f"critical={self.critical_threshold}%"
        )
    
    def check_mount(self, mount_point: str, usage_percent: float) -> List[Alert]:
        """Check a mount point and generate alerts if needed."""
        new_alerts = []
        
        if usage_percent >= self.critical_threshold:
            alert = Alert(
                level='CRITICAL',
                mount_point=mount_point,
                usage_percent=usage_percent,
                threshold=self.critical_threshold,
                message=f"CRITICAL: {mount_point} is {usage_percent:.1f}% full (threshold: {self.critical_threshold}%)"
            )
            new_alerts.append(alert)
            logger.critical(alert.message)
        elif usage_percent >= self.warning_threshold:
            alert = Alert(
                level='WARNING',
                mount_point=mount_point,
                usage_percent=usage_percent,
                threshold=self.warning_threshold,
                message=f"WARNING: {mount_point} is {usage_percent:.1f}% full (threshold: {self.warning_threshold}%)"
            )
            new_alerts.append(alert)
            logger.warning(alert.message)
        
        self.alerts.extend(new_alerts)
        return new_alerts
    
    def get_alerts(self) -> List[Alert]:
        """Get all generated alerts."""
        return self.alerts
    
    def has_alerts(self) -> bool:
        """Check if there are any alerts."""
        return len(self.alerts) > 0
    
    def clear(self):
        """Clear all alerts."""
        self.alerts.clear()
    
    def get_alert_for_mount(self, mount_point: str) -> Alert:
        """Get alert for a specific mount point, if any."""
        for alert in self.alerts:
            if alert.mount_point == mount_point:
                return alert
        return None
    
    @classmethod
    def from_args(cls, args) -> 'AlertManager':
        """Create AlertManager from parsed arguments."""
        warning_threshold = getattr(args, 'threshold', 80.0)
        critical_threshold = getattr(args, 'critical_threshold', None)
        
        if critical_threshold is None:
            critical_threshold = min(warning_threshold + 10, 100.0)
        
        return cls(
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold
        )
