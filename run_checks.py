"""Run the real source and Kivy callback tests with a visible CI result."""
import os
import sys
import unittest
os.environ['KIVY_NO_ARGS'] = '1'
suite = unittest.defaultTestLoader.discover('tests')
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
print('TEST_RESULT', result.testsRun, len(result.failures), len(result.errors), flush=True)
sys.exit(0 if result.wasSuccessful() and result.testsRun >= 16 else 1)
