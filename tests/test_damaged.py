"""Шаг 7 плана: повреждённая база — отдельные точные копии, понятный экран, без записи."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main


class DamagedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        app = main.BusinessApp(); main.App._running_app = app
        app.load_data()
        app.clients.append({'name': 'НАСТЯ', 'debt': '500'})
        app._last_backup_ts = 0
        app.save_data()  # появляется исправная резервная копия

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def damaged(self):
        return sorted(Path(self.tmp.name).glob('business_data.json.damaged_*'))

    def test_two_breakages_two_exact_copies(self):
        for content in (b'{broken one', b'{broken two'):
            Path(main.DATA_FILE).write_bytes(content)
            app = main.BusinessApp(); app.load_data()
            self.assertEqual(app.clients[-1]['name'], 'НАСТЯ')  # восстановлено из копии
        copies = [p.read_bytes() for p in self.damaged()]
        self.assertEqual(sorted(copies), [b'{broken one', b'{broken two'])

    def test_failed_copy_keeps_original(self):
        Path(main.DATA_FILE).write_bytes(b'{broken')
        with patch('shutil.copy2', side_effect=OSError('нет места')):
            with self.assertRaises(OSError):
                main.BusinessApp().load_data()
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), b'{broken')

    def test_no_backup_shows_screen_and_writes_nothing(self):
        shutil.rmtree(Path(self.tmp.name, 'backups'))
        Path(main.DATA_FILE).write_bytes(b'{broken')
        app = main.BusinessApp(); main.App._running_app = app
        root = app.build()
        self.assertNotIsInstance(root, main.ScreenManager)
        texts = ' '.join(getattr(w, 'text', '') for w in root.walk())
        self.assertIn('НЕ УДАЛОСЬ ОТКРЫТЬ ДАННЫЕ', texts)
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), b'{broken')
        with self.assertRaises(OSError):
            app.save_data()
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), b'{broken')


if __name__ == '__main__':
    unittest.main()


class LegacyMessageTests(unittest.TestCase):
    def test_legacy_creditor_order_message_explains_what_to_do(self):
        tmp = tempfile.TemporaryDirectory()
        old = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = tmp.name, tmp.name + '/business_data.json'
        try:
            app = main.BusinessApp(); main.App._running_app = app; app.load_data()
            client = {'name': 'НАСТЯ', 'debt': '500', 'history': [
                {'date': '01.07.26 10:00', 'sum': '500', 'print_cost': 200.0, 'via_malevich': True,
                 'mode': 'plenka', 'creditor_name': 'ОЛЕГ', 'oid': '1720000000.1'}]}
            app.clients += [client, {'name': 'ОЛЕГ', 'debt': '200', 'is_creditor': True, 'history': [{'sum': '200'}]}]
            from accounting import reverse_order
            ok, msg = reverse_order(app, client, client['history'][0])
            self.assertFalse(ok)
            self.assertIn('Данные не изменены', msg)
            self.assertIn('долг клиента и долг исполнителя', msg)
            self.assertEqual(client['debt'], '500')
        finally:
            main.BASE_PATH, main.DATA_FILE = old
            tmp.cleanup()
