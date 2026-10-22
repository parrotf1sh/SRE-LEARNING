#!/usr/bin/env python3
"""Disk Analyzer - A comprehensive disk space analysis tool for SRE."""

import argparse
import logging
import sys
import os

from .config import Config
from .filters import FilterManager
from .alert import AlertManager
from .mount import get_mount_info, sort_mount_info
from .scanner import scan_directory, sort_file_info, get_top_n
from .formatter import (
    format_mount_table, format_scan_table,
    format_mount_json, format_scan_json,
    format_mount_csv, format_scan_csv,
    write_output
)
from .scheduler import Scheduler
from .utils import parse_size

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_file: str = None):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(level=level, format=format_str, handlers=handlers)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='disk_analyzer',
        description='Disk space analysis tool for SRE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s mount                          Show mount point overview
  %(prog)s mount --format json            Output as JSON
  %(prog)s mount --threshold 90           Set alert threshold to 90%%
  %(prog)s scan /var                      Scan /var directory
  %(prog)s scan . --depth 2 --top 10      Scan current dir, top 10 largest
  %(prog)s scan /data --exclude-dir .git  Exclude .git directory
  %(prog)s mount --interval 3600          Run every hour
        """
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--log-file', help='Log to file')
    parser.add_argument('--config', help='Config file path (JSON)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    mount_parser = subparsers.add_parser('mount', help='Show mount point overview')
    mount_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table', help='Output format')
    mount_parser.add_argument('--sort', choices=['mount_point', 'percent', 'used', 'total', 'free'], default='mount_point', help='Sort by field')
    mount_parser.add_argument('--reverse', action='store_true', help='Reverse sort order')
    mount_parser.add_argument('--threshold', type=float, help='Warning threshold percentage (default: 80)')
    mount_parser.add_argument('--critical-threshold', type=float, help='Critical threshold percentage (default: threshold + 10)')
    mount_parser.add_argument('--exclude-fstype', help='Exclude filesystem types (comma-separated)')
    mount_parser.add_argument('--output', help='Output file path')
    mount_parser.add_argument('--output-dir', help='Output directory (auto-generates filename)')
    mount_parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    mount_parser.add_argument('--interval', type=int, help='Run at interval (seconds)')
    
    scan_parser = subparsers.add_parser('scan', help='Scan directory for disk usage')
    scan_parser.add_argument('path', help='Directory path to scan')
    scan_parser.add_argument('--depth', type=int, default=1, help='Scan depth (default: 1)')
    scan_parser.add_argument('--top', type=int, help='Show top N largest items')
    scan_parser.add_argument('--include-files', action='store_true', help='Include files in results')
    scan_parser.add_argument('--format', choices=['table', 'json', 'csv'], default='table', help='Output format')
    scan_parser.add_argument('--sort', choices=['size', 'name', 'path'], default='size', help='Sort by field')
    scan_parser.add_argument('--reverse', action='store_true', help='Reverse sort order')
    scan_parser.add_argument('--exclude-dir', action='append', help='Exclude directories (can be specified multiple times)')
    scan_parser.add_argument('--min-size', help='Minimum size to display (e.g., 1M, 100K)')
    scan_parser.add_argument('--output', help='Output file path')
    scan_parser.add_argument('--output-dir', help='Output directory (auto-generates filename)')
    scan_parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    scan_parser.add_argument('--interval', type=int, help='Run at interval (seconds)')
    
    return parser


def run_mount_command(args, config: Config):
    """Execute mount command."""
    filter_manager = FilterManager.from_args(args)
    if not args.exclude_fstype and config.get('filter', 'exclude_fstypes'):
        filter_manager.exclude_fstypes = set(config.get('filter', 'exclude_fstypes'))
    
    alert_manager = AlertManager.from_args(args)
    
    mount_infos = get_mount_info(filter_manager, alert_manager)
    mount_infos = sort_mount_info(mount_infos, sort_by=args.sort, reverse=args.reverse)
    
    use_color = not args.no_color and sys.stdout.isatty()
    
    if args.format == 'table':
        content = format_mount_table(mount_infos, use_color=use_color)
    elif args.format == 'json':
        content = format_mount_json(mount_infos)
    elif args.format == 'csv':
        content = format_mount_csv(mount_infos)
    else:
        content = format_mount_table(mount_infos, use_color=use_color)
    
    output_path = write_output(content, args.output, args.output_dir, args.format)
    
    if output_path:
        print(f"Report written to: {output_path}", file=sys.stderr)
    
    if alert_manager.has_alerts():
        print("\nAlerts:", file=sys.stderr)
        for alert in alert_manager.get_alerts():
            print(f"  {alert.message}", file=sys.stderr)
        return 1
    
    return 0


def run_scan_command(args, config: Config):
    """Execute scan command."""
    filter_manager = FilterManager.from_args(args)
    
    file_infos = scan_directory(
        args.path,
        depth=args.depth,
        filter_manager=filter_manager,
        include_files=args.include_files
    )
    
    if args.top:
        file_infos = get_top_n(file_infos, args.top)
    else:
        reverse = not args.reverse if args.sort == 'size' else args.reverse
        file_infos = sort_file_info(file_infos, sort_by=args.sort, reverse=reverse)
    
    use_color = not args.no_color and sys.stdout.isatty()
    
    if args.format == 'table':
        content = format_scan_table(file_infos, use_color=use_color)
    elif args.format == 'json':
        content = format_scan_json(file_infos)
    elif args.format == 'csv':
        content = format_scan_csv(file_infos)
    else:
        content = format_scan_table(file_infos, use_color=use_color)
    
    output_path = write_output(content, args.output, args.output_dir, args.format)
    
    if output_path:
        print(f"Report written to: {output_path}", file=sys.stderr)
    
    return 0


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    setup_logging(args.verbose, args.log_file)
    
    config = Config()
    if args.config:
        config = Config.load_from_file(args.config)
    config.apply_to_args(args)
    
    if args.interval:
        scheduler = Scheduler(args.interval)
        
        if args.command == 'mount':
            task = lambda: run_mount_command(args, config)
        elif args.command == 'scan':
            task = lambda: run_scan_command(args, config)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
        
        scheduler.start(task)
        return 0
    else:
        if args.command == 'mount':
            return run_mount_command(args, config)
        elif args.command == 'scan':
            return run_scan_command(args, config)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1


if __name__ == '__main__':
    sys.exit(main())
