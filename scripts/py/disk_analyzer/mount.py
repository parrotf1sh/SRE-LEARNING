"""Mount point information collection."""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not installed. Mount point info will be unavailable.")

from .utils import human_readable_size
from .filters import FilterManager
from .alert import AlertManager

logger = logging.getLogger(__name__)


@dataclass
class MountInfo:
    """Information about a mount point."""
    device: str
    mount_point: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float
    alert: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'device': self.device,
            'mount_point': self.mount_point,
            'fstype': self.fstype,
            'total': self.total,
            'used': self.used,
            'free': self.free,
            'percent': self.percent,
            'total_human': human_readable_size(self.total),
            'used_human': human_readable_size(self.used),
            'free_human': human_readable_size(self.free),
        }
        if self.alert:
            result['alert'] = self.alert.to_dict()
        return result


def get_mount_info(
    filter_manager: FilterManager = None,
    alert_manager: AlertManager = None
) -> List[MountInfo]:
    """Get information about all mount points."""
    if psutil is None:
        logger.error("psutil is required for mount point info")
        return []
    
    mount_infos = []
    partitions = psutil.disk_partitions(all=False)
    
    for partition in partitions:
        if filter_manager and filter_manager.should_exclude_mount(
            partition.mountpoint, partition.fstype
        ):
            continue
        
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            logger.warning(f"Permission denied: {partition.mountpoint}")
            continue
        except OSError as e:
            logger.warning(f"Error reading {partition.mountpoint}: {e}")
            continue
        
        mount_info = MountInfo(
            device=partition.device,
            mount_point=partition.mountpoint,
            fstype=partition.fstype,
            total=usage.total,
            used=usage.used,
            free=usage.free,
            percent=usage.percent
        )
        
        if alert_manager:
            alerts = alert_manager.check_mount(partition.mountpoint, usage.percent)
            if alerts:
                mount_info.alert = alerts[0]
        
        mount_infos.append(mount_info)
        logger.debug(
            f"Mount: {partition.mountpoint} - {usage.percent}% used "
            f"({human_readable_size(usage.used)}/{human_readable_size(usage.total)})"
        )
    
    return mount_infos


def sort_mount_info(
    mount_infos: List[MountInfo],
    sort_by: str = 'mount_point',
    reverse: bool = False
) -> List[MountInfo]:
    """Sort mount info list."""
    valid_keys = {'device', 'mount_point', 'fstype', 'total', 'used', 'free', 'percent'}
    
    if sort_by not in valid_keys:
        logger.warning(f"Invalid sort key '{sort_by}', using 'mount_point'")
        sort_by = 'mount_point'
    
    return sorted(
        mount_infos,
        key=lambda x: getattr(x, sort_by),
        reverse=reverse
    )
