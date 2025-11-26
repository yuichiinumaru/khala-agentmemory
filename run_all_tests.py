"""Run all tests for Khala."""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests."""
    # Add current directory to path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Discover tests in 'tests' directory
    loader = unittest.TestLoader()
    start_dir = 'tests'
    
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
