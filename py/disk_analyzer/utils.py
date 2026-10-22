"""Utility functions for disk analyzer."""

from typing import Union


def human_readable_size(size_bytes: Union[int, float]) -> str:
    """Convert bytes to human readable format."""
    if size_bytes < 0:
        return "N/A"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def parse_size(size_str: str) -> int:
    """Parse human readable size string to bytes."""
    size_str = size_str.strip().upper()
    
    units = {
        'B': 1,
        'K': 1024,
        'KB': 1024,
        'M': 1024 ** 2,
        'MB': 1024 ** 2,
        'G': 1024 ** 3,
        'GB': 1024 ** 3,
        'T': 1024 ** 4,
        'TB': 1024 ** 4,
    }
    
    for unit, multiplier in sorted(units.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(unit):
            number = size_str[:-len(unit)].strip()
            return int(float(number) * multiplier)
    
    return int(size_str)


def format_percentage(percentage: float) -> str:
    """Format percentage with color indicator."""
    return f"{percentage:.1f}%"


def truncate_path(path: str, max_length: int = 50) -> str:
    """Truncate long paths for display."""
    if len(path) <= max_length:
        return path
    return "..." + path[-(max_length - 3):]
