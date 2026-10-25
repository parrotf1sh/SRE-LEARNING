"""Terminal and JSON output reporter."""

import json
import logging
import sys
from datetime import datetime, timezone

from miniops.result import CheckResult

logger = logging.getLogger(__name__)

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class Reporter:
    """Formats check results for terminal and log output."""

    def __init__(self, use_color: bool = True):
        self.use_color = use_color and sys.stdout.isatty()

    def print_table(self, results: list[CheckResult]):
        if not results:
            print("No check results.")
            return

        print()
        print(self._bold("MiniOps Health Check Report"))
        print(self._cyan(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"))
        print("-" * 72)

        header = f"  {'CATEGORY':<12} {'NAME':<35} {'STATUS':<8} {'LATENCY':>10}  MESSAGE"
        print(self._bold(header))
        print("-" * 72)

        for r in sorted(results, key=lambda x: (x.category, x.name)):
            status = self._green("OK") if r.success else self._red("FAIL")
            latency = f"{r.latency_ms:.1f}ms"
            name = r.name[:34] if len(r.name) > 34 else r.name
            msg = r.message[:40] if len(r.message) > 40 else r.message
            print(f"  {r.category:<12} {name:<35} {status:<8} {latency:>10}  {msg}")

        print("-" * 72)

        total = len(results)
        ok = sum(1 for r in results if r.success)
        fail = total - ok
        summary = f"  Total: {total}  |  "
        summary += self._green(f"OK: {ok}") + "  |  "
        if fail > 0:
            summary += self._red(f"FAIL: {fail}")
        else:
            summary += f"FAIL: {fail}"
        print(summary)
        print()

    def print_json(self, results: list[CheckResult]):
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(results),
            "success": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))

    def write_log(self, results: list[CheckResult], log_file: str):
        with open(log_file, "a") as f:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total": len(results),
                "success": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
                "results": [r.to_dict() for r in results],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info("Log written to %s", log_file)

    def _color(self, text: str, color: str) -> str:
        if self.use_color:
            return f"{color}{text}{RESET}"
        return text

    def _green(self, text: str) -> str:
        return self._color(text, GREEN)

    def _red(self, text: str) -> str:
        return self._color(text, RED)

    def _yellow(self, text: str) -> str:
        return self._color(text, YELLOW)

    def _cyan(self, text: str) -> str:
        return self._color(text, CYAN)

    def _bold(self, text: str) -> str:
        return self._color(text, BOLD)
