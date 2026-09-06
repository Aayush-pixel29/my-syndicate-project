"""Test runner for syndicate core engine tests."""

import sys
import os
import unittest

# Add the src directory to Python path
tests_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.dirname(tests_dir)
src_dir = os.path.join(workspace_dir, "src")
sys.path.insert(0, src_dir)


def run_tests():
    """Run all tests using unittest discovery."""
    loader = unittest.TestLoader()
    start_dir = tests_dir
    pattern = 'test_*.py'

    suite = loader.discover(start_dir=start_dir, pattern=pattern)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
