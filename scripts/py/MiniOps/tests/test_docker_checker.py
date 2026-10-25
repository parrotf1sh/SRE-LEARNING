"""Tests for DockerChecker."""

from unittest.mock import patch, MagicMock
import subprocess
import pytest

from miniops.checker.docker_checker import DockerChecker


def _make_proc(returncode=0, stdout="", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestDockerChecker:
    @patch("miniops.checker.docker_checker.subprocess.run")
    def test_all_containers_up(self, mock_run):
        output = (
            "task-api-task-api-1\tUp 2 hours (healthy)\t0.0.0.0:80->80/tcp\n"
            "task-api-mysql-master-1\tUp 2 hours (healthy)\t3306/tcp\n"
            "task-api-redis-node-1-1\tUp 2 hours (healthy)\t6379/tcp\n"
        )
        mock_run.return_value = _make_proc(0, output)
        checker = DockerChecker(name_filter="task-api")
        results = checker.check()
        assert len(results) == 3
        assert all(r.success for r in results)

    @patch("miniops.checker.docker_checker.subprocess.run")
    def test_container_down(self, mock_run):
        output = (
            "task-api-task-api-1\tExited (1) 5 minutes ago\t\n"
            "task-api-mysql-master-1\tUp 2 hours (healthy)\t3306/tcp\n"
        )
        mock_run.return_value = _make_proc(0, output)
        checker = DockerChecker(name_filter="task-api")
        results = checker.check()
        assert len(results) == 2
        api_result = [r for r in results if "task-api-1" in r.name][0]
        assert api_result.success is False
        mysql_result = [r for r in results if "mysql" in r.name][0]
        assert mysql_result.success is True

    @patch("miniops.checker.docker_checker.subprocess.run")
    def test_no_containers_found(self, mock_run):
        mock_run.return_value = _make_proc(0, "")
        checker = DockerChecker(name_filter="nonexistent")
        results = checker.check()
        assert len(results) == 1
        assert results[0].success is False
        assert "No containers found" in results[0].message

    @patch("miniops.checker.docker_checker.subprocess.run")
    def test_docker_not_installed(self, mock_run):
        mock_run.side_effect = FileNotFoundError("docker not found")
        checker = DockerChecker()
        results = checker.check()
        assert results[0].success is False
        assert "not found" in results[0].message.lower()

    @patch("miniops.checker.docker_checker.subprocess.run")
    def test_docker_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker ps", timeout=15)
        checker = DockerChecker()
        results = checker.check()
        assert results[0].success is False
        assert "timeout" in results[0].message.lower()

    def test_parse_status(self):
        assert DockerChecker._parse_status("Up 2 hours") is True
        assert DockerChecker._parse_status("Up 5 minutes (healthy)") is True
        assert DockerChecker._parse_status("Exited (0) 1 hour ago") is False
        assert DockerChecker._parse_status("Restarting") is False
        assert DockerChecker._parse_status("Created") is False
