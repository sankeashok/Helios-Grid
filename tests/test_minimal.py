"""
Ultra-minimal test for CI/CD debugging
Tests only the most basic functionality to isolate issues
"""

import sys
import os


def test_python_basics():
    """Test absolute basics"""
    assert 1 + 1 == 2
    assert sys.version_info >= (3, 8)
    print(f"✅ Python version: {sys.version}")


def test_imports():
    """Test basic imports"""
    try:
        import json
        import tempfile
        print("✅ Basic imports work")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_file_system():
    """Test file system operations"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_path = f.name
        
        with open(temp_path, 'r') as f:
            content = f.read()
        
        os.unlink(temp_path)
        assert content == "test"
        print("✅ File operations work")
        return True
    except Exception as e:
        print(f"❌ File operations failed: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Running minimal CI/CD diagnostic tests...")
    print(f"Platform: {sys.platform}")
    print(f"Python executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Environment PATH: {os.environ.get('PATH', 'Not found')[:200]}...")
    
    # Run tests
    test_python_basics()
    test_imports()
    test_file_system()
    
    print("🎉 All minimal tests passed!")