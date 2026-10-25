"""CLI entry point for MiniOps."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from miniops.config import load_config
from miniops.runner import Runner
from miniops.reporter import Reporter
from miniops.backup.mysql_backup import MySQLBackup
from miniops.backup.restore import RestoreGuide
from miniops.scheduler import Scheduler
from miniops.alerter.webhook import WebhookAlerter
from miniops.alerter.email_alerter import EmailAlerter
from miniops.result import Alert


def setup_logging(log_file: str | None = None, verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=level, format=fmt, handlers=handlers)


def cmd_check(args, config):
    runner = Runner(config)
    reporter = Reporter()

    categories = args.only.split(",") if args.only else None
    results = runner.run(categories=categories)

    if args.format == "json":
        reporter.print_json(results)
    else:
        reporter.print_table(results)

    if args.log_file:
        reporter.write_log(results, args.log_file)

    alerts = runner.generate_alerts(results)
    if alerts and not args.no_alert:
        _send_alerts(config, alerts)

    failed = sum(1 for r in results if not r.success)
    return 1 if failed > 0 else 0


def cmd_alert(args, config):
    alert = Alert(
        level="warning",
        source="test",
        message="MiniOps test alert - if you receive this, the alert channel is working.",
    )
    alerters = _build_alerters(config)

    if not alerters:
        print("No alert channels configured. Edit config/default.yaml to set up webhooks or email.")
        return 1

    for alerter in alerters:
        name = type(alerter).__name__
        if not alerter.enabled:
            print(f"  [{name}] disabled, skipping (set enabled: true in config)")
            continue
        ok = alerter.send(alert)
        status = "sent" if ok else "failed"
        print(f"  [{name}] {status}")

    return 0


def cmd_backup(args, config):
    backup_cfg = config.get("backup", {}).get("mysql", {})
    if not backup_cfg:
        print("No backup configuration found.")
        return 1

    if args.list:
        backup = MySQLBackup(backup_cfg)
        backups = backup.list_backups()
        if not backups:
            print("No backups found.")
        else:
            print(f"{'File':<60} {'Size':>8}  {'Modified'}")
            print("-" * 90)
            for b in backups:
                print(f"{b['file']:<60} {b['size_mb']:>6.2f}MB  {b['modified']}")
        return 0

    backup = MySQLBackup(backup_cfg)
    result = backup.run()

    if result["success"]:
        print(f"Backup completed: {result['file']} ({result['size_mb']} MB)")
    else:
        print(f"Backup failed: {result['error']}", file=sys.stderr)
    return 0 if result["success"] else 1


def cmd_restore(args, config):
    backup_cfg = config.get("backup", {}).get("mysql", {})
    guide = RestoreGuide(backup_cfg)

    if args.guide or not args.execute:
        print(guide.generate(args.file))
        return 0

    if args.execute:
        if not args.file:
            print("Error: --file is required for --execute", file=sys.stderr)
            return 1
        print(f"Restoring from {args.file}...")
        result = guide.execute_restore(args.file)
        if result["success"]:
            print(f"Restore completed: {result['message']}")
        else:
            print(f"Restore failed: {result['error']}", file=sys.stderr)
        return 0 if result["success"] else 1


def cmd_daemon(args, config):
    scheduler = Scheduler(config)
    scheduler.start()
    return 0


def cmd_report(args, config):
    runner = Runner(config)
    reporter = Reporter()
    results = runner.run()

    if args.format == "json":
        reporter.print_json(results)
    else:
        reporter.print_table(results)

    if args.log_file:
        reporter.write_log(results, args.log_file)
    return 0


def _build_alerters(config):
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


def _send_alerts(config, alerts):
    alerters = _build_alerters(config)
    for alert in alerts:
        for alerter in alerters:
            try:
                alerter.send(alert)
            except Exception as e:
                logging.getLogger(__name__).error(
                    "Alerter %s failed: %s", type(alerter).__name__, e
                )


def main():
    parser = argparse.ArgumentParser(
        prog="miniops",
        description="MiniOps - SRE monitoring and operations toolkit",
    )
    parser.add_argument(
        "-c", "--config", default=None,
        help="Path to config YAML (default: config/default.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--log-file", default=None,
        help="Write JSON log to file",
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # check
    p_check = sub.add_parser("check", help="Run health checks")
    p_check.add_argument("--only", help="Comma-separated categories (http,mysql,redis,docker,system)")
    p_check.add_argument("--format", choices=["table", "json"], default="table")
    p_check.add_argument("--no-alert", action="store_true", help="Suppress alerting")

    # alert
    p_alert = sub.add_parser("alert", help="Send test alert")

    # backup
    p_backup = sub.add_parser("backup", help="Backup MySQL database")
    p_backup.add_argument("--list", action="store_true", help="List existing backups")

    # restore
    p_restore = sub.add_parser("restore", help="Restore database from backup")
    p_restore.add_argument("--file", help="Backup file path")
    p_restore.add_argument("--guide", action="store_true", help="Show restore guide")
    p_restore.add_argument("--execute", action="store_true", help="Execute restore (requires --file)")

    # daemon
    p_daemon = sub.add_parser("daemon", help="Run in daemon mode (periodic checks)")

    # report
    p_report = sub.add_parser("report", help="Generate status report")
    p_report.add_argument("--format", choices=["table", "json"], default="table")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    setup_logging(log_file=args.log_file, verbose=args.verbose)

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    commands = {
        "check": cmd_check,
        "alert": cmd_alert,
        "backup": cmd_backup,
        "restore": cmd_restore,
        "daemon": cmd_daemon,
        "report": cmd_report,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args, config)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
