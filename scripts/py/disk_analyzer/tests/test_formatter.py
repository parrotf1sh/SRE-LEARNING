"""Tests for formatter module."""

import unittest
import json
import csv
import io

from disk_analyzer.formatter import (
    format_mount_table, format_scan_table,
    format_mount_json, format_scan_json,
    format_mount_csv, format_scan_csv
)
from disk_analyzer.mount import MountInfo
from disk_analyzer.scanner import FileInfo


class TestFormatMountTable(unittest.TestCase):
    """Test format_mount_table function."""
    
    def test_format_empty(self):
        """Test formatting empty list."""
        result = format_mount_table([], use_color=False)
        self.assertEqual(result, "No mount points found.")
    
    def test_format_single_mount(self):
        """Test formatting single mount."""
        infos = [
            MountInfo('/dev/sda1', '/', 'ext4', 100*1024**3, 50*1024**3, 50*1024**3, 50.0)
        ]
        
        result = format_mount_table(infos, use_color=False)
        
        self.assertIn('/dev/sda1', result)
        self.assertIn('/', result)
        self.assertIn('ext4', result)
        self.assertIn('50.0%', result)


class TestFormatScanTable(unittest.TestCase):
    """Test format_scan_table function."""
    
    def test_format_empty(self):
        """Test formatting empty list."""
        result = format_scan_table([], use_color=False)
        self.assertEqual(result, "No files/directories found.")
    
    def test_format_single_item(self):
        """Test formatting single item."""
        infos = [FileInfo('/path/to/dir', 1024, True, 'dir')]
        
        result = format_scan_table(infos, use_color=False)
        
        self.assertIn('1.00 KB', result)
        self.assertIn('DIR', result)
        self.assertIn('dir', result)


class TestFormatMountJson(unittest.TestCase):
    """Test format_mount_json function."""
    
    def test_format_json(self):
        """Test JSON formatting."""
        infos = [
            MountInfo('/dev/sda1', '/', 'ext4', 100*1024**3, 50*1024**3, 50*1024**3, 50.0)
        ]
        
        result = format_mount_json(infos)
        data = json.loads(result)
        
        self.assertIn('timestamp', data)
        self.assertIn('mount_points', data)
        self.assertEqual(len(data['mount_points']), 1)
        self.assertEqual(data['mount_points'][0]['mount_point'], '/')


class TestFormatScanJson(unittest.TestCase):
    """Test format_scan_json function."""
    
    def test_format_json(self):
        """Test JSON formatting."""
        infos = [FileInfo('/path/to/dir', 1024, True, 'dir')]
        
        result = format_scan_json(infos)
        data = json.loads(result)
        
        self.assertIn('timestamp', data)
        self.assertIn('items', data)
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['name'], 'dir')


class TestFormatMountCsv(unittest.TestCase):
    """Test format_mount_csv function."""
    
    def test_format_csv(self):
        """Test CSV formatting."""
        infos = [
            MountInfo('/dev/sda1', '/', 'ext4', 100*1024**3, 50*1024**3, 50*1024**3, 50.0)
        ]
        
        result = format_mount_csv(infos)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['mount_point'], '/')
        self.assertEqual(rows[0]['fstype'], 'ext4')


class TestFormatScanCsv(unittest.TestCase):
    """Test format_scan_csv function."""
    
    def test_format_csv(self):
        """Test CSV formatting."""
        infos = [FileInfo('/path/to/dir', 1024, True, 'dir')]
        
        result = format_scan_csv(infos)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'dir')
        self.assertEqual(rows[0]['size'], '1024')


if __name__ == '__main__':
    unittest.main()
