"""Tests for RedisChecker."""

from unittest.mock import patch, MagicMock
import subprocess
import pytest

from miniops.checker.redis_checker import RedisChecker


def _make_proc(returncode=0, stdout="", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestRedisChecker:
    @patch("miniops.checker.redis_checker.subprocess.run")
    def test_ping_success(self, mock_run):
        # First 6 calls: PING for each node, 7th: CLUSTER INFO
        ping_proc = _make_proc(0, "PONG\n")
        cluster_proc = _make_proc(0, "cluster_state:ok\ncluster_known_nodes:6\ncluster_size:3\n")
        mock_run.side_effect = [ping_proc] * 6 + [cluster_proc]

        targets = [
            {"container": f"redis-node-{i}-1", "port": 6378 + i}
            for i in range(1, 7)
        ]
        checker = RedisChecker(targets=targets)
        results = checker.check()

        ping_results = [r for r in results if "cluster" not in r.name]
        assert all(r.success for r in ping_results)
        assert len(ping_results) == 6

    @patch("miniops.checker.redis_checker.subprocess.run")
    def test_ping_failure(self, mock_run):
        mock_run.return_value = _make_proc(1, "", "Could not connect")
        targets = [{"container": "redis-node-1-1", "port": 6379}]
        checker = RedisChecker(targets=targets)
        results = checker.check()
        ping_result = [r for r in results if "cluster" not in r.name][0]
        assert ping_result.success is False

    @patch("miniops.checker.redis_checker.subprocess.run")
    def test_cluster_ok(self, mock_run):
        ping_proc = _make_proc(0, "PONG\n")
        cluster_output = "cluster_state:ok\ncluster_known_nodes:6\ncluster_size:3\n"
        cluster_proc = _make_proc(0, cluster_output)
        mock_run.side_effect = [ping_proc, cluster_proc]

        targets = [{"container": "redis-node-1-1", "port": 6379}]
        checker = RedisChecker(targets=targets)
        results = checker.check()
        cluster_result = [r for r in results if "cluster" in r.name][0]
        assert cluster_result.success is True
        assert cluster_result.details["cluster_state"] == "ok"

    @patch("miniops.checker.redis_checker.subprocess.run")
    def test_cluster_fail(self, mock_run):
        ping_proc = _make_proc(0, "PONG\n")
        cluster_output = "cluster_state:fail\ncluster_known_nodes:4\ncluster_size:2\n"
        cluster_proc = _make_proc(0, cluster_output)
        mock_run.side_effect = [ping_proc, cluster_proc]

        targets = [{"container": "redis-node-1-1", "port": 6379}]
        checker = RedisChecker(targets=targets)
        results = checker.check()
        cluster_result = [r for r in results if "cluster" in r.name][0]
        assert cluster_result.success is False
        assert cluster_result.details["cluster_state"] == "fail"

    @patch("miniops.checker.redis_checker.subprocess.run")
    def test_container_down(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker exec", timeout=10)
        targets = [{"container": "redis-node-1-1", "port": 6379}]
        checker = RedisChecker(targets=targets)
        results = checker.check()
        assert all(not r.success for r in results)
