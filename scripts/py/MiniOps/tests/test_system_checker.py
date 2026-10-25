"""Tests for SystemChecker."""

from unittest.mock import patch, MagicMock
import sys
import pytest

from miniops.checker.system_checker import SystemChecker


class TestSystemChecker:
    def test_disk_check(self):
        checker = SystemChecker()
        results = checker.check()
        disk_results = [r for r in results if r.name.startswith("disk-")]
        assert len(disk_results) >= 1
        root_result = [r for r in disk_results if r.name == "disk-/"][0]
        assert root_result.category == "system"
        assert root_result.success is True
        assert "percent" in root_result.details

    def test_memory_check(self):
        checker = SystemChecker()
        results = checker.check()
        mem_results = [r for r in results if r.name == "memory"]
        assert len(mem_results) == 1
        assert mem_results[0].category == "system"

    def test_threshold_warning(self):
        checker = SystemChecker(thresholds={"disk_warn": 0, "disk_crit": 99,
                                             "mem_warn": 0, "mem_crit": 99})
        results = checker.check()
        disk_results = [r for r in results if r.name.startswith("disk-") and r.success]
        for r in disk_results:
            assert r.details.get("level") == "warning"

    def test_threshold_critical(self):
        checker = SystemChecker(thresholds={"disk_warn": 0, "disk_crit": 0,
                                             "mem_warn": 0, "mem_crit": 0})
        results = checker.check()
        disk_results = [r for r in results if r.name.startswith("disk-") and r.details]
        for r in disk_results:
            assert r.details.get("level") == "critical"
            assert r.success is False

    def test_memory_with_psutil(self):
        mock_psutil = MagicMock()
        mem = MagicMock()
        mem.percent = 45.2
        mem.total = 16 * 1024**3
        mem.used = 7 * 1024**3
        mem.available = 9 * 1024**3
        mock_psutil.virtual_memory.return_value = mem

        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            checker = SystemChecker()
            results = checker._check_memory()
            assert len(results) == 1
            assert results[0].success is True
            assert results[0].details["percent"] == 45.2

    def test_level_ok(self):
        checker = SystemChecker(thresholds={"disk_warn": 85, "disk_crit": 95})
        assert checker._level(50, "disk") == "ok"

    def test_level_warning(self):
        checker = SystemChecker(thresholds={"disk_warn": 85, "disk_crit": 95})
        assert checker._level(90, "disk") == "warning"

    def test_level_critical(self):
        checker = SystemChecker(thresholds={"disk_warn": 85, "disk_crit": 95})
        assert checker._level(96, "disk") == "critical"
