"""
health-checker 测试模块

覆盖场景:
- 正常响应 (200)
- 超时
- 连接失败
- 重试后成功
- 重试耗尽仍失败
- 混合场景 (5 个目标，包含成功/失败/异常)
- 程序不因单个目标失败而崩溃
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

from checker import check_url, check_with_retry, run_checks, generate_summary, CheckResult


class TestCheckUrl:
    """check_url 单元测试"""

    @patch("checker.requests.get")
    def test_normal_response_200(self, mock_get):
        """正常响应 200，应返回成功"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = check_url("https://example.com", timeout=5)

        assert result.success is True
        assert result.status_code == 200
        assert result.elapsed_ms is not None
        assert result.error is None

    @patch("checker.requests.get")
    def test_normal_response_301(self, mock_get):
        """301 重定向也算成功（2xx/3xx 均视为成功）"""
        mock_resp = MagicMock()
        mock_resp.status_code = 301
        mock_get.return_value = mock_resp

        result = check_url("https://example.com", timeout=5)
        assert result.success is True
        assert result.status_code == 301

    @patch("checker.requests.get")
    def test_http_500(self, mock_get):
        """500 服务端错误，应返回失败"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        result = check_url("https://example.com", timeout=5)

        assert result.success is False
        assert result.status_code == 500
        assert "HTTP 500" in result.error

    @patch("checker.requests.get")
    def test_timeout(self, mock_get):
        """请求超时，应返回失败并标记 Timeout"""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = check_url("https://slow.example.com", timeout=1)

        assert result.success is False
        assert result.error == "Timeout"
        assert result.elapsed_ms is not None

    @patch("checker.requests.get")
    def test_connection_error(self, mock_get):
        """连接失败，应返回失败并标记 ConnectionError"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = check_url("https://down.example.com", timeout=5)

        assert result.success is False
        assert "ConnectionError" in result.error

    @patch("checker.requests.get")
    def test_elapsed_time_recorded(self, mock_get):
        """无论成功失败，都应记录耗时"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = check_url("https://example.com", timeout=5)
        assert result.elapsed_ms >= 0


class TestCheckWithRetry:
    """check_with_retry 重试逻辑测试"""

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_retry_then_success(self, mock_get, mock_sleep):
        """前两次失败，第三次成功，应返回成功"""
        fail_result = CheckResult(url="https://example.com", success=False, error="Timeout")
        success_result = CheckResult(url="https://example.com", success=True, status_code=200, elapsed_ms=100.0)

        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            MagicMock(status_code=200),
        ]

        result = check_with_retry("https://example.com", timeout=5, max_retries=3)

        assert result.success is True
        assert result.retries == 2
        assert mock_sleep.call_count == 2

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_retry_exhausted(self, mock_get, mock_sleep):
        """重试耗尽仍失败，应返回最后一次失败结果"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = check_with_retry("https://down.example.com", timeout=5, max_retries=2)

        assert result.success is False
        assert result.retries == 2
        assert "ConnectionError" in result.error

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_exponential_backoff(self, mock_get, mock_sleep):
        """验证指数退避间隔：1s, 2s, 4s"""
        mock_get.side_effect = requests.exceptions.Timeout()

        check_with_retry("https://example.com", timeout=5, max_retries=3)

        assert mock_sleep.call_count == 3
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("checker.requests.get")
    def test_no_retry_on_success(self, mock_get):
        """首次成功则不重试"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = check_with_retry("https://example.com", timeout=5, max_retries=3)

        assert result.success is True
        assert result.retries == 0
        assert mock_get.call_count == 1


class TestRunChecks:
    """run_checks 集成测试"""

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_mixed_scenario_no_crash(self, mock_get, mock_sleep):
        """
        验收标准：5 个目标，包含正常/超时/连接失败，程序不崩溃
        """
        def side_effect(url, **kwargs):
            if "ok1" in url or "ok2" in url:
                resp = MagicMock()
                resp.status_code = 200
                return resp
            elif "timeout" in url:
                raise requests.exceptions.Timeout("timed out")
            elif "down" in url:
                raise requests.exceptions.ConnectionError("refused")
            else:
                resp = MagicMock()
                resp.status_code = 500
                return resp

        mock_get.side_effect = side_effect

        targets = [
            {"url": "https://ok1.example.com", "timeout": 5},
            {"url": "https://ok2.example.com", "timeout": 5},
            {"url": "https://timeout.example.com", "timeout": 5},
            {"url": "https://down.example.com", "timeout": 5},
            {"url": "https://error.example.com", "timeout": 5},
        ]

        results = run_checks(targets, mode="concurrent", max_workers=3, max_retries=0)

        assert len(results) == 5
        success_count = sum(1 for r in results if r.success)
        failed_count = sum(1 for r in results if not r.success)
        assert success_count == 2
        assert failed_count == 3

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_serial_mode(self, mock_get, mock_sleep):
        """串行模式应正常工作"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        targets = [
            {"url": "https://a.example.com", "timeout": 5},
            {"url": "https://b.example.com", "timeout": 5},
        ]

        results = run_checks(targets, mode="serial", max_retries=0)

        assert len(results) == 2
        assert all(r.success for r in results)

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_concurrent_mode(self, mock_get, mock_sleep):
        """并发模式应正常工作"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        targets = [{"url": f"https://t{i}.example.com", "timeout": 5} for i in range(5)]

        results = run_checks(targets, mode="concurrent", max_workers=5, max_retries=0)

        assert len(results) == 5
        assert all(r.success for r in results)

    @patch("checker.requests.get")
    def test_empty_targets(self, mock_get):
        """空目标列表应返回空结果"""
        results = run_checks([], mode="concurrent")
        assert results == []
        mock_get.assert_not_called()


class TestGenerateSummary:
    """generate_summary 统计测试"""

    def test_all_success(self):
        results = [
            CheckResult(url="https://a.com", success=True, status_code=200, elapsed_ms=50),
            CheckResult(url="https://b.com", success=True, status_code=200, elapsed_ms=100),
        ]
        summary = generate_summary(results)

        assert summary["total"] == 2
        assert summary["success"] == 2
        assert summary["failed"] == 0
        assert summary["error_categories"] == {}

    def test_mixed_results(self):
        results = [
            CheckResult(url="https://ok.com", success=True, status_code=200, elapsed_ms=50),
            CheckResult(url="https://timeout.com", success=False, error="Timeout", elapsed_ms=10000),
            CheckResult(url="https://down.com", success=False, error="ConnectionError: refused", elapsed_ms=100),
            CheckResult(url="https://err.com", success=False, error="Timeout", elapsed_ms=10000),
        ]
        summary = generate_summary(results)

        assert summary["total"] == 4
        assert summary["success"] == 1
        assert summary["failed"] == 3
        assert summary["error_categories"]["Timeout"] == 2
        assert summary["error_categories"]["ConnectionError"] == 1

    def test_empty_results(self):
        summary = generate_summary([])
        assert summary["total"] == 0
        assert summary["success"] == 0
        assert summary["failed"] == 0


class TestAcceptanceCriteria:
    """
    验收标准测试：
    - 对 5 个测试地址执行健康检查
    - 针对正常响应、超时、连接失败编写测试
    - 程序不得因一个目标失败而整体崩溃
    """

    @patch("checker.time.sleep")
    @patch("checker.requests.get")
    def test_five_targets_acceptance(self, mock_get, mock_sleep):
        """完整的验收场景：5 个目标，混合成功/失败/异常"""

        call_count = {"n": 0}

        def side_effect(url, **kwargs):
            call_count["n"] += 1
            if "healthy" in url:
                resp = MagicMock()
                resp.status_code = 200
                return resp
            elif "slow" in url:
                raise requests.exceptions.Timeout("timed out")
            elif "refused" in url:
                raise requests.exceptions.ConnectionError("Connection refused")
            elif "server-error" in url:
                resp = MagicMock()
                resp.status_code = 503
                return resp
            else:
                resp = MagicMock()
                resp.status_code = 200
                return resp

        mock_get.side_effect = side_effect

        targets = [
            {"url": "https://healthy.example.com", "timeout": 5},
            {"url": "https://also-healthy.example.com", "timeout": 5},
            {"url": "https://slow.example.com", "timeout": 2},
            {"url": "https://refused.example.com", "timeout": 5},
            {"url": "https://server-error.example.com", "timeout": 5},
        ]

        results = run_checks(targets, mode="concurrent", max_workers=5, max_retries=0)

        assert len(results) == 5, "应返回 5 个结果"

        healthy_results = [r for r in results if "healthy" in r.url]
        assert all(r.success for r in healthy_results), "healthy 目标应成功"

        timeout_result = [r for r in results if "slow" in r.url][0]
        assert not timeout_result.success, "slow 目标应失败"
        assert timeout_result.error == "Timeout"

        conn_result = [r for r in results if "refused" in r.url][0]
        assert not conn_result.success, "refused 目标应失败"
        assert "ConnectionError" in conn_result.error

        server_result = [r for r in results if "server-error" in r.url][0]
        assert not server_result.success, "server-error 目标应失败"

        summary = generate_summary(results)
        assert summary["total"] == 5
        assert summary["success"] == 2
        assert summary["failed"] == 3
