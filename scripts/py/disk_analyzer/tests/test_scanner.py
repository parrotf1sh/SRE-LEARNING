"""Tests for scanner module."""

import unittest
import tempfile
import os

from disk_analyzer.scanner import scan_directory, sort_file_info, get_top_n, get_dir_size
from disk_analyzer.filters import FilterManager


class TestGetDirSize(unittest.TestCase):
    """Test get_dir_size function."""
    
    def test_get_dir_size_empty(self):
        """Test size of empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            size = get_dir_size(tmpdir)
            self.assertEqual(size, 0)
    
    def test_get_dir_size_with_files(self):
        """Test size of directory with files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, 'file1.txt')
            file2 = os.path.join(tmpdir, 'file2.txt')
            
            with open(file1, 'w') as f:
                f.write('a' * 100)
            with open(file2, 'w') as f:
                f.write('b' * 200)
            
            size = get_dir_size(tmpdir)
            self.assertEqual(size, 300)


class TestScanDirectory(unittest.TestCase):
    """Test scan_directory function."""
    
    def test_scan_nonexistent_path(self):
        """Test scanning non-existent path."""
        result = scan_directory('/nonexistent/path')
        self.assertEqual(len(result), 0)
    
    def test_scan_empty_directory(self):
        """Test scanning empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = scan_directory(tmpdir)
            self.assertEqual(len(result), 0)
    
    def test_scan_with_subdirs(self):
        """Test scanning directory with subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir1 = os.path.join(tmpdir, 'subdir1')
            subdir2 = os.path.join(tmpdir, 'subdir2')
            os.makedirs(subdir1)
            os.makedirs(subdir2)
            
            with open(os.path.join(subdir1, 'file1.txt'), 'w') as f:
                f.write('a' * 100)
            with open(os.path.join(subdir2, 'file2.txt'), 'w') as f:
                f.write('b' * 200)
            
            result = scan_directory(tmpdir, depth=1)
            
            self.assertEqual(len(result), 2)
            sizes = {info.name: info.size for info in result}
            self.assertEqual(sizes['subdir1'], 100)
            self.assertEqual(sizes['subdir2'], 200)
    
    def test_scan_with_filter(self):
        """Test scanning with filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir1 = os.path.join(tmpdir, 'include')
            subdir2 = os.path.join(tmpdir, 'exclude')
            os.makedirs(subdir1)
            os.makedirs(subdir2)
            
            with open(os.path.join(subdir1, 'file.txt'), 'w') as f:
                f.write('a' * 100)
            with open(os.path.join(subdir2, 'file.txt'), 'w') as f:
                f.write('b' * 200)
            
            filter_manager = FilterManager(exclude_dirs=['exclude'])
            result = scan_directory(tmpdir, depth=1, filter_manager=filter_manager)
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, 'include')
    
    def test_scan_with_files(self):
        """Test scanning with files included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, 'file1.txt')
            with open(file1, 'w') as f:
                f.write('a' * 100)
            
            result = scan_directory(tmpdir, depth=1, include_files=True)
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, 'file1.txt')
            self.assertFalse(result[0].is_dir)


class TestSortFileInfo(unittest.TestCase):
    """Test sort_file_info function."""
    
    def test_sort_by_size(self):
        """Test sorting by size."""
        from disk_analyzer.scanner import FileInfo
        
        infos = [
            FileInfo('/path1', 100, True, 'dir1'),
            FileInfo('/path2', 300, True, 'dir2'),
            FileInfo('/path3', 200, True, 'dir3'),
        ]
        
        result = sort_file_info(infos, sort_by='size', reverse=True)
        
        self.assertEqual(result[0].size, 300)
        self.assertEqual(result[1].size, 200)
        self.assertEqual(result[2].size, 100)


class TestGetTopN(unittest.TestCase):
    """Test get_top_n function."""
    
    def test_get_top_n(self):
        """Test getting top N items."""
        from disk_analyzer.scanner import FileInfo
        
        infos = [
            FileInfo('/path1', 100, True, 'dir1'),
            FileInfo('/path2', 300, True, 'dir2'),
            FileInfo('/path3', 200, True, 'dir3'),
            FileInfo('/path4', 400, True, 'dir4'),
        ]
        
        result = get_top_n(infos, n=2)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].size, 400)
        self.assertEqual(result[1].size, 300)


if __name__ == '__main__':
    unittest.main()
