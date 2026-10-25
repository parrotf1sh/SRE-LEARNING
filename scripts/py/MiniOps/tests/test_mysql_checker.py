"""Tests for MySQLChecker."""

from unittest.mock import patch, MagicMock
import subprocess
import pytest

from miniops.checker.mysql_checker import MySQLChecker


def _make_proc(returncode=0, stdout="", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestMySQLChecker:
    @patch("miniops.checker.mysql_checker.subprocess.run")
    def test_ping_success(self, mock_run):
        mock_run.return_value = _make_proc(0, "mysqld is alive\n")
        checker = MySQLChecker(targets=[{"container": "mysql-master", "check_replication": False}])
        results = checker.check()
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].category == "mysql"

    @patch("miniops.checker.mysql_checker.subprocess.run")
    def test_ping_failure(self, mock_run):
        mock_run.return_value = _make_proc(1, "", "connection refused")
        checker = MySQLChecker(targets=[{"container": "mysql-master", "check_replication": False}])
        results = checker.check()
        assert results[0].success is False

    @patch("miniops.checker.mysql_checker.subprocess.run")
    def test_replication_healthy(self, mock_run):
        # First call: ping, Second call: SHOW SLAVE STATUS
        ping_proc = _make_proc(0, "mysqld is alive\n")
        repl_output = (
            "*************************** 1. row ***************************\n"
            "             Slave_IO_State: Waiting for master\n"
            "                Master_Host: mysql-master\n"
            "            Slave_IO_Running: Yes\n"
            "           Slave_SQL_Running: Yes\n"
            "       Seconds_Behind_Master: 0\n"
        )
        repl_proc = _make_proc(0, repl_output)
        mock_run.side_effect = [ping_proc, repl_proc]

        checker = MySQLChecker(targets=[{"container": "mysql-master", "check_replication": True}])
        results = checker.check()
        assert len(results) == 2
        assert results[0].success is True  # ping
        assert results[1].success is True  # replication
        assert results[1].details["seconds_behind_master"] == 0

    @patch("miniops.checker.mysql_checker.subprocess.run")
    def test_replication_broken(self, mock_run):
        ping_proc = _make_proc(0, "mysqld is alive\n")
        repl_output = (
            "            Slave_IO_Running: Yes\n"
            "           Slave_SQL_Running: No\n"
            "       Seconds_Behind_Master: NULL\n"
        )
        repl_proc = _make_proc(0, repl_output)
        mock_run.side_effect = [ping_proc, repl_proc]

        checker = MySQLChecker(targets=[{"container": "mysql-master", "check_replication": True}])
        results = checker.check()
        repl_result = [r for r in results if "replication" in r.name][0]
        assert repl_result.success is False

    @patch("miniops.checker.mysql_checker.subprocess.run")
    def test_container_not_running(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker exec", timeout=10)
        checker = MySQLChecker(targets=[{"container": "mysql-master", "check_replication": False}])
        results = checker.check()
        assert results[0].success is False
        assert "timeout" in results[0].message.lower()

    @patch("miniops.checker.mysql_checker.subprocess.run")
    def test_multiple_targets(self, mock_run):
        mock_run.return_value = _make_proc(0, "mysqld is alive\n")
        targets = [
            {"container": "mysql-master", "check_replication": False},
            {"container": "mysql-slave", "check_replication": False},
        ]
        checker = MySQLChecker(targets=targets)
        results = checker.check()
        assert len(results) == 2
