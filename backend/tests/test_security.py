"""
Unit tests for security modules
"""
import pytest
from pathlib import Path
from security import sanitize_filename, validate_zip_path


class TestSanitizeFilename:
    """Tests for filename sanitization"""
    
    def test_normal_filename(self):
        """Test normal filename is unchanged"""
        assert sanitize_filename("test.html") == "test.html"
        assert sanitize_filename("my_file.js") == "my_file.js"
    
    def test_path_traversal_removed(self):
        """Test path traversal attempts are blocked"""
        assert sanitize_filename("../../../etc/passwd") == "passwd"
        assert sanitize_filename("..\\..\\windows\\system32") == "system32"
        assert sanitize_filename("../test.html") == "test.html"
    
    def test_special_characters(self):
        """Test special characters are handled"""
        assert sanitize_filename("file<script>.html") == "filescripthtml"
        assert sanitize_filename("test@file.js") == "testfilejs"
    
    def test_empty_filename(self):
        """Test empty filename gets fallback"""
        result = sanitize_filename("")
        assert result.startswith("unnamed_file")
        assert len(result) > 0


class TestValidateZipPath:
    """Tests for ZIP path validation"""
    
    def test_valid_path(self, tmp_path):
        """Test valid ZIP member path"""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        
        result = validate_zip_path(extract_dir, "file.html")
        assert result is not None
        assert result.name == "file.html"
    
    def test_zip_slip_attack(self, tmp_path):
        """Test ZIP slip attack is blocked"""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        
        # Attempt ZIP slip
        result = validate_zip_path(extract_dir, "../../../etc/passwd")
        assert result is None
    
    def test_nested_valid_path(self, tmp_path):
        """Test nested but valid path"""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        
        result = validate_zip_path(extract_dir, "subdir/file.html")
        assert result is not None
        assert "subdir" in str(result)
    
    def test_absolute_path_attack(self, tmp_path):
        """Test absolute path attack is blocked"""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        
        # Try absolute path
        result = validate_zip_path(extract_dir, "/etc/passwd")
        assert result is None

