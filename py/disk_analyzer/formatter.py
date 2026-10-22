"""Output formatting for disk analyzer."""

import csv
import json
import logging
import os
import sys
from typing import List, Dict, Any, Union, Optional
from datetime import datetime

from .mount import MountInfo
from .scanner import FileInfo
from .utils import human_readable_size

logger = logging.getLogger(__name__)


class TerminalColors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable colors."""
        cls.RED = ''
        cls.YELLOW = ''
        cls.GREEN = ''
        cls.BLUE = ''
        cls.BOLD = ''
        cls.END = ''


def format_mount_table(mount_infos: List[MountInfo], use_color: bool = True) -> str:
    """Format mount info as a terminal table."""
    if not mount_infos:
        return "No mount points found."
    
    if not use_color:
        TerminalColors.disable()
    
    headers = ['Filesystem', 'Type', 'Size', 'Used', 'Avail', 'Use%', 'Mount']
    rows = []
    
    for info in mount_infos:
        use_pct = f"{info.percent:.1f}%"
        
        if info.alert:
            if info.alert.level == 'CRITICAL':
                use_pct = f"{TerminalColors.RED}{TerminalColors.BOLD}{use_pct}{TerminalColors.END}"
            elif info.alert.level == 'WARNING':
                use_pct = f"{TerminalColors.YELLOW}{use_pct}{TerminalColors.END}"
        
        rows.append([
            info.device,
            info.fstype,
            human_readable_size(info.total),
            human_readable_size(info.used),
            human_readable_size(info.free),
            use_pct,
            info.mount_point
        ])
    
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            cell_len = len(str(cell).replace(TerminalColors.RED, '').replace(
                TerminalColors.YELLOW, '').replace(
                TerminalColors.BOLD, '').replace(
                TerminalColors.END, ''))
            col_widths[i] = max(col_widths[i], cell_len)
    
    def format_row(row):
        formatted = []
        for i, cell in enumerate(row):
            clean_cell = str(cell).replace(TerminalColors.RED, '').replace(
                TerminalColors.YELLOW, '').replace(
                TerminalColors.BOLD, '').replace(
                TerminalColors.END, '')
            padding = col_widths[i] - len(clean_cell)
            formatted.append(str(cell) + ' ' * padding)
        return '  '.join(formatted)
    
    output = []
    header_line = format_row(headers)
    output.append(f"{TerminalColors.BOLD}{header_line}{TerminalColors.END}")
    output.append('-' * len(header_line.replace(TerminalColors.BOLD, '').replace(TerminalColors.END, '')))
    
    for row in rows:
        output.append(format_row(row))
    
    return '\n'.join(output)


def format_scan_table(file_infos: List[FileInfo], use_color: bool = True) -> str:
    """Format scan results as a terminal table."""
    if not file_infos:
        return "No files/directories found."
    
    if not use_color:
        TerminalColors.disable()
    
    headers = ['Size', 'Type', 'Name', 'Path']
    rows = []
    
    for info in file_infos:
        type_str = 'DIR' if info.is_dir else 'FILE'
        rows.append([
            human_readable_size(info.size),
            type_str,
            info.name,
            info.path
        ])
    
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    def format_row(row):
        formatted = []
        for i, cell in enumerate(row):
            padding = col_widths[i] - len(str(cell))
            formatted.append(str(cell) + ' ' * padding)
        return '  '.join(formatted)
    
    output = []
    header_line = format_row(headers)
    output.append(f"{TerminalColors.BOLD}{header_line}{TerminalColors.END}")
    output.append('-' * len(header_line))
    
    for row in rows:
        output.append(format_row(row))
    
    return '\n'.join(output)


def format_mount_json(mount_infos: List[MountInfo]) -> str:
    """Format mount info as JSON."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'mount_points': [info.to_dict() for info in mount_infos]
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_scan_json(file_infos: List[FileInfo]) -> str:
    """Format scan results as JSON."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'items': [info.to_dict() for info in file_infos]
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_mount_csv(mount_infos: List[MountInfo]) -> str:
    """Format mount info as CSV."""
    import io
    output = io.StringIO()
    
    headers = ['device', 'mount_point', 'fstype', 'total', 'used', 'free', 'percent', 'alert']
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    
    for info in mount_infos:
        row = {
            'device': info.device,
            'mount_point': info.mount_point,
            'fstype': info.fstype,
            'total': info.total,
            'used': info.used,
            'free': info.free,
            'percent': f"{info.percent:.1f}",
            'alert': info.alert.level if info.alert else ''
        }
        writer.writerow(row)
    
    return output.getvalue()


def format_scan_csv(file_infos: List[FileInfo]) -> str:
    """Format scan results as CSV."""
    import io
    output = io.StringIO()
    
    headers = ['path', 'name', 'size', 'is_dir']
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    
    for info in file_infos:
        row = {
            'path': info.path,
            'name': info.name,
            'size': info.size,
            'is_dir': info.is_dir
        }
        writer.writerow(row)
    
    return output.getvalue()


def write_output(
    content: str,
    output_file: Optional[str] = None,
    output_dir: Optional[str] = None,
    format_type: str = 'table'
) -> str:
    """Write output to file or stdout."""
    if output_file:
        file_path = output_file
    elif output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(output_dir, f"disk_report_{timestamp}.{format_type}")
    else:
        print(content)
        return None
    
    os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Output written to: {file_path}")
    return file_path
