"""Directory scanning logic."""

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .utils import human_readable_size
from .filters import FilterManager

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a file or directory."""
    path: str
    size: int
    is_dir: bool
    name: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'path': self.path,
            'size': self.size,
            'size_human': human_readable_size(self.size),
            'is_dir': self.is_dir,
            'name': self.name
        }


def get_dir_size(path: str, filter_manager: FilterManager = None) -> int:
    """Recursively calculate directory size."""
    total_size = 0
    
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat(follow_symlinks=False).st_size
                    elif entry.is_dir(follow_symlinks=False):
                        if filter_manager and filter_manager.should_exclude_dir(entry.path):
                            continue
                        total_size += get_dir_size(entry.path, filter_manager)
                except (PermissionError, OSError) as e:
                    logger.debug(f"Cannot access {entry.path}: {e}")
                    continue
    except (PermissionError, OSError) as e:
        logger.debug(f"Cannot scan {path}: {e}")
    
    return total_size


def scan_directory(
    path: str,
    depth: int = 1,
    filter_manager: FilterManager = None,
    include_files: bool = False
) -> List[FileInfo]:
    """Scan a directory and return file/directory information."""
    path = os.path.abspath(path)
    
    if not os.path.exists(path):
        logger.error(f"Path does not exist: {path}")
        return []
    
    if not os.path.isdir(path):
        logger.error(f"Path is not a directory: {path}")
        return []
    
    results = []
    _scan_recursive(path, depth, 0, results, filter_manager, include_files)
    
    return results


def _scan_recursive(
    path: str,
    max_depth: int,
    current_depth: int,
    results: List[FileInfo],
    filter_manager: FilterManager = None,
    include_files: bool = False
):
    """Recursively scan directory."""
    if current_depth >= max_depth:
        return
    
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_file(follow_symlinks=False):
                        if not include_files:
                            continue
                        
                        size = entry.stat(follow_symlinks=False).st_size
                        
                        if filter_manager and filter_manager.should_exclude_by_size(size):
                            continue
                        
                        file_info = FileInfo(
                            path=entry.path,
                            size=size,
                            is_dir=False,
                            name=entry.name
                        )
                        results.append(file_info)
                        logger.debug(f"File: {entry.path} - {human_readable_size(size)}")
                    
                    elif entry.is_dir(follow_symlinks=False):
                        if filter_manager and filter_manager.should_exclude_dir(entry.path):
                            continue
                        
                        size = get_dir_size(entry.path, filter_manager)
                        
                        if filter_manager and filter_manager.should_exclude_by_size(size):
                            continue
                        
                        dir_info = FileInfo(
                            path=entry.path,
                            size=size,
                            is_dir=True,
                            name=entry.name
                        )
                        results.append(dir_info)
                        logger.debug(f"Dir: {entry.path} - {human_readable_size(size)}")
                        
                        _scan_recursive(
                            entry.path,
                            max_depth,
                            current_depth + 1,
                            results,
                            filter_manager,
                            include_files
                        )
                
                except (PermissionError, OSError) as e:
                    logger.debug(f"Cannot access {entry.path}: {e}")
                    continue
    
    except (PermissionError, OSError) as e:
        logger.debug(f"Cannot scan {path}: {e}")


def sort_file_info(
    file_infos: List[FileInfo],
    sort_by: str = 'size',
    reverse: bool = True
) -> List[FileInfo]:
    """Sort file info list."""
    valid_keys = {'path', 'size', 'is_dir', 'name'}
    
    if sort_by not in valid_keys:
        logger.warning(f"Invalid sort key '{sort_by}', using 'size'")
        sort_by = 'size'
    
    return sorted(
        file_infos,
        key=lambda x: getattr(x, sort_by),
        reverse=reverse
    )


def get_top_n(file_infos: List[FileInfo], n: int = 10) -> List[FileInfo]:
    """Get top N largest files/directories."""
    sorted_infos = sort_file_info(file_infos, sort_by='size', reverse=True)
    return sorted_infos[:n]
