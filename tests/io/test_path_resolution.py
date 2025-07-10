"""
Tests for path resolution functionality.
"""

import os
import tempfile
import unittest
from pathlib import Path

from codeflow.io.file import resolve_codebase_path


class TestPathResolution(unittest.TestCase):
    """Test cases for path resolution relative to pwd."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.test_dir.cleanup()

    def test_relative_path_resolution(self):
        """Test that relative paths are resolved against pwd."""
        # Create a subdirectory
        subdir = Path("subdir")
        subdir.mkdir()
        
        # Test resolving relative path
        resolved = resolve_codebase_path("subdir")
        expected = (Path(self.test_dir.name) / "subdir").resolve()
        self.assertEqual(resolved, expected)

    def test_absolute_path_resolution(self):
        """Test that absolute paths are returned as-is."""
        abs_path = Path("/tmp/test/path").resolve()
        resolved = resolve_codebase_path(abs_path)
        self.assertEqual(resolved, abs_path)

    def test_dot_path_resolution(self):
        """Test that '.' resolves to current directory."""
        resolved = resolve_codebase_path(".")
        expected = Path(self.test_dir.name).resolve()
        self.assertEqual(resolved, expected)

    def test_parent_path_resolution(self):
        """Test that '..' resolves correctly."""
        # Create and change to subdirectory
        subdir = Path("subdir")
        subdir.mkdir()
        os.chdir(subdir)
        
        resolved = resolve_codebase_path("..")
        expected = Path(self.test_dir.name).resolve()
        self.assertEqual(resolved, expected)

    def test_nested_relative_path(self):
        """Test nested relative path resolution."""
        # Create nested structure
        nested = Path("a/b/c")
        nested.mkdir(parents=True)
        
        resolved = resolve_codebase_path("a/b/c")
        expected = (Path(self.test_dir.name) / "a" / "b" / "c").resolve()
        self.assertEqual(resolved, expected)

    def test_path_with_symlinks(self):
        """Test that paths with symlinks are properly resolved."""
        # Create a directory and a symlink to it
        real_dir = Path("real_dir")
        real_dir.mkdir()
        link_dir = Path("link_dir")
        link_dir.symlink_to(real_dir)
        
        # Resolve through symlink
        resolved = resolve_codebase_path("link_dir")
        # Should resolve to the actual directory
        self.assertTrue(resolved.exists())
        self.assertTrue(resolved.is_dir())

    def test_nonexistent_path_resolution(self):
        """Test that nonexistent paths still resolve correctly."""
        # Path doesn't need to exist to be resolved
        resolved = resolve_codebase_path("nonexistent/path")
        expected = (Path(self.test_dir.name) / "nonexistent" / "path").resolve()
        self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()