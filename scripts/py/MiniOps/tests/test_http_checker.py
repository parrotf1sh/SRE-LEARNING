"""Tests for HTTPChecker."""

from unittest.mock import patch, MagicMock
import pytest

from miniops.checker.http_checker import HTTPChecker


class TestHTTPChecker:
    def _make_response(self, status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        return resp

    @patch("miniops.checker.http_checker.requests.get")
    def test_healthy_endpoint(self, mock_get):
        mock_get.return_value = self._make_response(200, {"status": "healthy"})
        checker = HTTPChecker(targets=[{"url": "http://localhost:80/health", "timeout": 5}])
        results = checker.check()
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].category == "http"

    @patch("miniops.checker.http_checker.requests.get")
    def test_unhealthy_status(self, mock_get):
        mock_get.return_value = self._make_response(200, {"status": "unhealthy"})
        checker = HTTPChecker(targets=[{"url": "http://localhost:80/health",
                                        "timeout": 5, "expected_status": "healthy"}])
        results = checker.check()
        assert len(results) == 1
        assert results[0].success is False

    @patch("miniops.checker.http_checker.requests.get")
    def test_http_500(self, mock_get):
        mock_get.return_value = self._make_response(500)
        checker = HTTPChecker(targets=[{"url": "http://localhost:80/health", "timeout": 5}])
        results = checker.check()
        assert results[0].success is False
        assert "500" in results[0].message

    @patch("miniops.checker.http_checker.requests.get")
    def test_connection_refused(self, mock_get):
        import requests as req
        mock_get.side_effect = req.ConnectionError("Connection refused")
        checker = HTTPChecker(targets=[{"url": "http://localhost:80/health", "timeout": 5}])
        results = checker.check()
        assert results[0].success is False
        assert "Connection refused" in results[0].message

    @patch("miniops.checker.http_checker.requests.get")
    def test_timeout(self, mock_get):
        import requests as req
        mock_get.side_effect = req.Timeout("timed out")
        checker = HTTPChecker(targets=[{"url": "http://localhost:80/health", "timeout": 5}])
        results = checker.check()
        assert results[0].success is False
        assert "Timeout" in results[0].message

    @patch("miniops.checker.http_checker.requests.get")
    def test_multiple_targets(self, mock_get):
        mock_get.return_value = self._make_response(200, {"status": "healthy"})
        targets = [
            {"url": "http://host1/health", "timeout": 5},
            {"url": "http://host2/health", "timeout": 5},
            {"url": "http://host3/health", "timeout": 5},
        ]
        checker = HTTPChecker(targets=targets)
        results = checker.check()
        assert len(results) == 3
        assert all(r.success for r in results)

    @patch("miniops.checker.http_checker.requests.get")
    def test_latency_recorded(self, mock_get):
        mock_get.return_value = self._make_response(200, {"status": "healthy"})
        checker = HTTPChecker(targets=[{"url": "http://localhost/health", "timeout": 5}])
        results = checker.check()
        assert results[0].latency_ms >= 0
