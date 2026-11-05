"""Окно рулона с плотностью экрана телефона (отдельный процесс, чтобы не менять остальные тесты)."""
import os
import subprocess
import sys
import unittest
from pathlib import Path


class PhoneLayoutTests(unittest.TestCase):
    def test_roll_window_on_phone_density(self):
        env = dict(os.environ, KIVY_METRICS_DENSITY='2.625', KIVY_NO_CONSOLELOG='1')
        script = Path(__file__).with_name('phone_layout_check.py')
        out = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=120)
        last = (out.stdout.strip().splitlines() or ['нет вывода: ' + out.stderr[-500:]])[-1]
        self.assertEqual(last, 'OK')


if __name__ == '__main__':
    unittest.main()
