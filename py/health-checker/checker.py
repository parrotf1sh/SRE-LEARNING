"""
health-checker: HTTP 健康检查核心模块
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """单次健康检查结果"""
    url: str
    success: bool
    status_code: Optional[int] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None
    retries: int = 0


def check_url(url: str, timeout: int = 10) -> CheckResult:
    """对单个 URL 执行一次 HTTP 健康检查"""
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout)
        elapsed_ms = (time.monotonic() - start) * 1000
        success = 200 <= resp.status_code < 400
        return CheckResult(
            url=url,
            success=success,
            status_code=resp.status_code,
            elapsed_ms=round(elapsed_ms, 2),
            error=None if success else f"HTTP {resp.status_code}",
        )
    except requests.exceptions.Timeout:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            url=url, success=False,
            elapsed_ms=round(elapsed_ms, 2),
            error="Timeout",
        )
    except requests.exceptions.ConnectionError as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            url=url, success=False,
            elapsed_ms=round(elapsed_ms, 2),
            error=f"ConnectionError: {e}",
        )
    except Exception as e:
        elapsed_ms = (time.monotonic() - start) * 1000
        return CheckResult(
            url=url, success=False,
            elapsed_ms=round(elapsed_ms, 2),
            error=f"{type(e).__name__}: {e}",
        )


def check_with_retry(url: str, timeout: int = 10, max_retries: int = 3) -> CheckResult:
    """带重试的健康检查，失败时指数退避重试"""
    last_result = None
    for attempt in range(max_retries + 1):
        result = check_url(url, timeout)
        result.retries = attempt
        if result.success:
            return result
        last_result = result
        if attempt < max_retries:
            backoff = 2 ** attempt
            logger.debug(f"Retry {attempt + 1}/{max_retries} for {url} after {backoff}s")
            time.sleep(backoff)
    return last_result


def run_checks(
    targets: list[dict],
    mode: str = "concurrent",
    max_workers: int = 5,
    default_timeout: int = 10,
    max_retries: int = 3,
) -> list[CheckResult]:
    """
    对所有目标执行健康检查

    targets: [{"url": "...", "timeout": 10}, ...]
    mode: "concurrent" 或 "serial"
    """
    results = []

    if mode == "concurrent":
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_target = {}
            for target in targets:
                timeout = target.get("timeout", default_timeout)
                future = pool.submit(check_with_retry, target["url"], timeout, max_retries)
                future_to_target[future] = target["url"]

            for future in as_completed(future_to_target):
                url = future_to_target[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(CheckResult(url=url, success=False, error=str(e)))
    else:
        for target in targets:
            timeout = target.get("timeout", default_timeout)
            try:
                result = check_with_retry(target["url"], timeout, max_retries)
                results.append(result)
            except Exception as e:
                results.append(CheckResult(url=target["url"], success=False, error=str(e)))

    return results


def generate_summary(results: list[CheckResult]) -> dict:
    """生成检查统计摘要"""
    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success

    error_categories = {}
    for r in results:
        if not r.success and r.error:
            category = r.error.split(":")[0] if ":" in r.error else r.error
            error_categories[category] = error_categories.get(category, 0) + 1

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "error_categories": error_categories,
    }
