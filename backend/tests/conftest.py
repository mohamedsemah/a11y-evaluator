"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///./test_accessibility_analyzer.db"
os.environ["DEBUG"] = "True"
os.environ["AUTH_REQUIRED"] = "False"

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment"""
    # Create test database
    yield
    # Cleanup test database
    test_db = Path("test_accessibility_analyzer.db")
    if test_db.exists():
        test_db.unlink()

