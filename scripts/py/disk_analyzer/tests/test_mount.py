"""Tests for mount module."""

import unittest
from unittest.mock import patch, MagicMock

from disk_analyzer.mount import get_mount_info, sort_mount_info, MountInfo
from disk_analyzer.filters import FilterManager
from disk_analyzer.alert import AlertManager


class TestMountInfo(unittest.TestCase):
    """Test MountInfo dataclass."""
    
    def test_to_dict(self):
        """Test MountInfo to_dict method."""
        info = MountInfo(
            device='/dev/sda1',
            mount_point='/',
            fstype='ext4',
            total=100 * 1024**3,
            used=50 * 1024**3,
            free=50 * 1024**3,
            percent=50.0
        )
        
        result = info.to_dict()
        
        self.assertEqual(result['device'], '/dev/sda1')
        self.assertEqual(result['mount_point'], '/')
        self.assertEqual(result['fstype'], 'ext4')
        self.assertIn('total_human', result)
        self.assertIn('used_human', result)
        self.assertIn('free_human', result)


class TestGetMountInfo(unittest.TestCase):
    """Test get_mount_info function."""
    
    @patch('disk_analyzer.mount.psutil')
    def test_get_mount_info_basic(self, mock_psutil):
        """Test basic mount info retrieval."""
        mock_partition = MagicMock()
        mock_partition.device = '/dev/sda1'
        mock_partition.mountpoint = '/'
        mock_partition.fstype = 'ext4'
        
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024**3
        mock_usage.used = 50 * 1024**3
        mock_usage.free = 50 * 1024**3
        mock_usage.percent = 50.0
        
        mock_psutil.disk_partitions.return_value = [mock_partition]
        mock_psutil.disk_usage.return_value = mock_usage
        
        result = get_mount_info()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].mount_point, '/')
        self.assertEqual(result[0].percent, 50.0)
    
    @patch('disk_analyzer.mount.psutil')
    def test_get_mount_info_with_filter(self, mock_psutil):
        """Test mount info with filter."""
        mock_partition = MagicMock()
        mock_partition.device = 'tmpfs'
        mock_partition.mountpoint = '/tmp'
        mock_partition.fstype = 'tmpfs'
        
        mock_psutil.disk_partitions.return_value = [mock_partition]
        
        filter_manager = FilterManager(exclude_fstypes={'tmpfs'})
        result = get_mount_info(filter_manager)
        
        self.assertEqual(len(result), 0)
    
    @patch('disk_analyzer.mount.psutil')
    def test_get_mount_info_with_alert(self, mock_psutil):
        """Test mount info with alert."""
        mock_partition = MagicMock()
        mock_partition.device = '/dev/sda1'
        mock_partition.mountpoint = '/'
        mock_partition.fstype = 'ext4'
        
        mock_usage = MagicMock()
        mock_usage.total = 100 * 1024**3
        mock_usage.used = 90 * 1024**3
        mock_usage.free = 10 * 1024**3
        mock_usage.percent = 90.0
        
        mock_psutil.disk_partitions.return_value = [mock_partition]
        mock_psutil.disk_usage.return_value = mock_usage
        
        alert_manager = AlertManager(warning_threshold=80.0, critical_threshold=90.0)
        result = get_mount_info(alert_manager=alert_manager)
        
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].alert)
        self.assertEqual(result[0].alert.level, 'CRITICAL')


class TestSortMountInfo(unittest.TestCase):
    """Test sort_mount_info function."""
    
    def test_sort_by_mount_point(self):
        """Test sorting by mount point."""
        infos = [
            MountInfo('/dev/sdb', '/home', 'ext4', 100, 50, 50, 50.0),
            MountInfo('/dev/sda', '/', 'ext4', 100, 50, 50, 50.0),
        ]
        
        result = sort_mount_info(infos, sort_by='mount_point')
        
        self.assertEqual(result[0].mount_point, '/')
        self.assertEqual(result[1].mount_point, '/home')
    
    def test_sort_by_percent(self):
        """Test sorting by usage percent."""
        infos = [
            MountInfo('/dev/sda', '/', 'ext4', 100, 30, 70, 30.0),
            MountInfo('/dev/sdb', '/home', 'ext4', 100, 80, 20, 80.0),
        ]
        
        result = sort_mount_info(infos, sort_by='percent', reverse=True)
        
        self.assertEqual(result[0].percent, 80.0)
        self.assertEqual(result[1].percent, 30.0)


if __name__ == '__main__':
    unittest.main()
