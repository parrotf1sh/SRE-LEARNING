"""Tests for Runner orchestration."""

from unittest.mock import patch, MagicMock
import pytest

from miniops.runner import Runner
from miniops.result import CheckResult, Alert


def _make_config():
    return {
        "targets": {
            "http": [{"url": "http://localhost:80/health", "timeout": 5}],
            "mysql": [{"container": "mysql-master", "check_replication": False}],
            "redis": [{"container": "redis-node-1-1", "port": 6379}],
            "docker": {"enabled": True, "name_filter": "task-api"},
            "system": {"enabled": True, "disk_warn": 85, "disk_crit": 95,
                        "mem_warn": 85, "mem_crit": 95},
        },
        "defaults": {"timeout": 10},
    }


class TestRunner:
    def test_build_checkers(self):
        config = _make_config()
        runner = Runner(config)
        categories = {c.category for c in runner.checkers}
        assert "http" in categories
        assert "mysql" in categories
        assert "redis" in categories
        assert "docker" in categories
        assert "system" in categories

    def test_build_checkers_disabled(self):
        config = _make_config()
        config["targets"]["docker"]["enabled"] = False
        config["targets"]["system"]["enabled"] = False
        runner = Runner(config)
        categories = {c.category for c in runner.checkers}
        assert "docker" not in categories
        assert "system" not in categories

    @patch("miniops.checker.http_checker.HTTPChecker.check")
    @patch("miniops.checker.mysql_checker.MySQLChecker.check")
    @patch("miniops.checker.redis_checker.RedisChecker.check")
    @patch("miniops.checker.docker_checker.DockerChecker.check")
    @patch("miniops.checker.system_checker.SystemChecker.check")
    def test_run_all(self, mock_sys, mock_docker, mock_redis, mock_mysql, mock_http):
        mock_http.return_value = [CheckResult("http", "http", True, "OK")]
        mock_mysql.return_value = [CheckResult("mysql", "mysql", True, "OK")]
        mock_redis.return_value = [CheckResult("redis", "redis", True, "OK")]
        mock_docker.return_value = [CheckResult("docker", "docker", True, "Up")]
        mock_sys.return_value = [CheckResult("disk", "system", True, "50%")]

        runner = Runner(_make_config())
        results = runner.run()
        assert len(results) == 5
        assert all(r.success for r in results)

    @patch("miniops.checker.http_checker.HTTPChecker.check")
    @patch("miniops.checker.mysql_checker.MySQLChecker.check")
    @patch("miniops.checker.redis_checker.RedisChecker.check")
    @patch("miniops.checker.docker_checker.DockerChecker.check")
    @patch("miniops.checker.system_checker.SystemChecker.check")
    def test_run_with_failure(self, mock_sys, mock_docker, mock_redis, mock_mysql, mock_http):
        mock_http.return_value = [CheckResult("http", "http", False, "Connection refused")]
        mock_mysql.return_value = [CheckResult("mysql", "mysql", True, "OK")]
        mock_redis.return_value = [CheckResult("redis", "redis", True, "OK")]
        mock_docker.return_value = [CheckResult("docker", "docker", True, "Up")]
        mock_sys.return_value = [CheckResult("disk", "system", True, "50%")]

        runner = Runner(_make_config())
        results = runner.run()
        failed = [r for r in results if not r.success]
        assert len(failed) == 1
        assert failed[0].category == "http"

    @patch("miniops.checker.http_checker.HTTPChecker.check")
    def test_run_filtered(self, mock_http):
        mock_http.return_value = [CheckResult("http", "http", True, "OK")]
        runner = Runner(_make_config())
        results = runner.run(categories=["http"])
        assert len(results) == 1

    def test_generate_alerts_critical(self):
        results = [
            CheckResult("mysql-master", "mysql", False, "ping failed"),
            CheckResult("http", "http", True, "OK"),
        ]
        runner = Runner(_make_config())
        alerts = runner.generate_alerts(results)
        assert len(alerts) == 1
        assert alerts[0].level == "critical"
        assert alerts[0].source == "mysql-master"

    def test_generate_alerts_warning(self):
        results = [
            CheckResult("disk-/", "system", False, "87% used",
                        details={"level": "warning"}),
        ]
        runner = Runner(_make_config())
        alerts = runner.generate_alerts(results)
        assert len(alerts) == 1
        assert alerts[0].level == "warning"

    def test_no_alerts_on_success(self):
        results = [
            CheckResult("mysql", "mysql", True, "OK"),
            CheckResult("redis", "redis", True, "OK"),
        ]
        runner = Runner(_make_config())
        alerts = runner.generate_alerts(results)
        assert len(alerts) == 0
