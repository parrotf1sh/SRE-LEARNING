"""Filter and exclude logic for disk analyzer."""

import fnmatch
import logging
from typing import List, Set

logger = logging.getLogger(__name__)


class FilterManager:
    """Manage filters for mount points and directories."""
    
    def __init__(
        self,
        exclude_fstypes: Set[str] = None,
        exclude_dirs: List[str] = None,
        min_size: int = 0
    ):
        self.exclude_fstypes = exclude_fstypes or set()
        self.exclude_dirs = exclude_dirs or []
        self.min_size = min_size
        
        logger.debug(
            f"FilterManager initialized: fstypes={self.exclude_fstypes}, "
            f"dirs={self.exclude_dirs}, min_size={self.min_size}"
        )
    
    def should_exclude_mount(self, mount_point: str, fstype: str) -> bool:
        """Check if a mount point should be excluded."""
        if fstype in self.exclude_fstypes:
            logger.debug(f"Excluding mount {mount_point} (fstype={fstype})")
            return True
        return False
    
    def should_exclude_dir(self, dir_path: str) -> bool:
        """Check if a directory should be excluded."""
        for pattern in self.exclude_dirs:
            if fnmatch.fnmatch(dir_path, pattern):
                logger.debug(f"Excluding dir {dir_path} (pattern={pattern})")
                return True
            if fnmatch.fnmatch(dir_path.split('/')[-1], pattern):
                logger.debug(f"Excluding dir {dir_path} (name matches {pattern})")
                return True
        return False
    
    def should_exclude_by_size(self, size: int) -> bool:
        """Check if an item should be excluded by size."""
        return size < self.min_size
    
    @classmethod
    def from_args(cls, args) -> 'FilterManager':
        """Create FilterManager from parsed arguments."""
        exclude_fstypes = set()
        if hasattr(args, 'exclude_fstype') and args.exclude_fstype:
            exclude_fstypes = set(args.exclude_fstype.split(','))
        
        exclude_dirs = []
        if hasattr(args, 'exclude_dir') and args.exclude_dir:
            exclude_dirs = args.exclude_dir
        
        min_size = 0
        if hasattr(args, 'min_size') and args.min_size:
            from .utils import parse_size
            min_size = parse_size(args.min_size)
        
        return cls(
            exclude_fstypes=exclude_fstypes,
            exclude_dirs=exclude_dirs,
            min_size=min_size
        )
