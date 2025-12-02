"""Run all tests for Khala."""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests."""
    # Add project root to path (one level up from this script)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Discover tests in 'tests' directory
    loader = unittest.TestLoader()
    start_dir = os.path.join(project_root, 'tests')
    
    if not os.path.exists(start_dir):
        print(f"Tests directory '{start_dir}' not found.")
        return
        
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
