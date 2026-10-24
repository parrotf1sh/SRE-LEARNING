#!/usr/bin/env python3
"""
health-checker: HTTP 健康检查工具

用法:
  # 命令行传入 URL
  python health_checker.py https://www.baidu.com https://www.google.com

  # 使用配置文件
  python health_checker.py -c config.yaml

  # 指定超时和重试
  python health_checker.py -c config.yaml --timeout 5 --max-retries 2

  # 串行模式
  python health_checker.py -c config.yaml --mode serial
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from checker import run_checks, generate_summary, CheckResult

LOG_FILE = "health_check.log"


def setup_logging(log_file: str = LOG_FILE):
    """配置日志：JSON 写文件 + 可读格式输出控制台"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JsonFormatter())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


class JsonFormatter(logging.Formatter):
    """JSON 格式日志"""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "result_data"):
            log_entry["data"] = record.result_data
        return json.dumps(log_entry, ensure_ascii=False)


def result_to_dict(result: CheckResult) -> dict:
    """将 CheckResult 转为可序列化的 dict"""
    return {
        "url": result.url,
        "success": result.success,
        "status_code": result.status_code,
        "elapsed_ms": result.elapsed_ms,
        "error": result.error,
        "retries": result.retries,
    }


def load_targets(config_path: str = None, urls: list[str] = None, default_timeout: int = 10) -> list[dict]:
    """从配置文件或命令行参数加载目标列表"""
    targets = []

    if config_path:
        path = Path(config_path)
        if not path.exists():
            logging.error(f"Config file not found: {config_path}")
            sys.exit(1)
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        for t in config.get("targets", []):
            if isinstance(t, str):
                targets.append({"url": t, "timeout": default_timeout})
            elif isinstance(t, dict) and "url" in t:
                targets.append({
                    "url": t["url"],
                    "timeout": t.get("timeout", default_timeout),
                })

    if urls:
        for url in urls:
            targets.append({"url": url, "timeout": default_timeout})

    if not targets:
        logging.error("No targets specified. Use -c config.yaml or provide URLs.")
        sys.exit(1)

    return targets


def parse_args():
    parser = argparse.ArgumentParser(description="HTTP Health Checker")
    parser.add_argument("urls", nargs="*", help="URLs to check")
    parser.add_argument("-c", "--config", help="Path to YAML config file")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry count (default: 3)")
    parser.add_argument("--mode", choices=["concurrent", "serial"], default="concurrent",
                        help="Check mode (default: concurrent)")
    parser.add_argument("--max-workers", type=int, default=5, help="Max concurrent workers (default: 5)")
    parser.add_argument("--log-file", default=LOG_FILE, help=f"Log file path (default: {LOG_FILE})")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.log_file)

    logger = logging.getLogger(__name__)
    targets = load_targets(args.config, args.urls, args.timeout)

    logger.info(f"Starting health check for {len(targets)} target(s) in {args.mode} mode")

    results = run_checks(
        targets=targets,
        mode=args.mode,
        max_workers=args.max_workers,
        default_timeout=args.timeout,
        max_retries=args.max_retries,
    )

    for r in results:
        logger.info(json.dumps(result_to_dict(r), ensure_ascii=False), extra={"result_data": result_to_dict(r)})

    summary = generate_summary(results)
    logger.info("Summary:", extra={"result_data": summary})

    print("\n" + "=" * 60)
    print("Health Check Summary")
    print("=" * 60)
    print(f"  Total targets : {summary['total']}")
    print(f"  Success       : {summary['success']}")
    print(f"  Failed        : {summary['failed']}")
    if summary["error_categories"]:
        print("  Error breakdown:")
        for category, count in summary["error_categories"].items():
            print(f"    {category}: {count}")
    print("=" * 60)
    print(f"Log written to: {args.log_file}")


if __name__ == "__main__":
    main()
