"""Экспорт и импорт базы: перенос из старой версии без потерь и с откатом."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
sys.path.insert(0, str(Path(__file__).resolve().parent))
import transfer

from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.clock import Clock

OLD_BASE = {  # как в версии 1.0: без ролей, номеров карточек и журнала
    'clients': [
        {'name': 'БАННЕР ОСТАТОК', 'debt': '0', 'm_total': '75', 'm_remain': '40'},
        {'name': 'ОЛЕГ', 'debt': '1200', 'is_creditor': True, 'history': [{'sum': '200', 'date': '01.07.26 10:00'}]},
        {'name': 'САША', 'debt': '331593.4', 'history': [{'sum': '1000', 'date': '01.07.26 11:00'}]},
        {'name': 'НАСТЯ', 'debt': '500', 'history': []},
        {'name': 'БЕЛЫЙ БАНЕР', 'debt': '2000'}, {'name': 'ЧЕРНЫЙ БАНЕР', 'debt': '700'}],
    'prices': ['160', '200', '220', '250'], 'plenka_prices': ['250', '300', '350', '400'],
    'profit_correction': '1500', 'print_cost': '55', 'profit_log': [], 'rolls': [],
    'old_unknown_field': {'keep': 1}}


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp(); main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.append({'name': 'ТЕСТ', 'debt': '10'})
        self.app.save_data()
        self.screen = main.ClientsScreen(name='t')
        self.screen.refresh_list = lambda: None
        self.messages = []
        self.screen._stub_popup = lambda t, m: self.messages.append(m)
        self.old_file_path = Path(self.tmp.name, 'old.json')
        self.old_file_path.write_text(json.dumps(OLD_BASE, ensure_ascii=False), encoding='utf-8')

    def tearDown(self):
        for w in list(Window.children):
            if isinstance(w, Popup):
                w.dismiss()
        Clock.tick()
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def test_export_is_exact_copy(self):
        path = transfer.export_database(self.app, self.tmp.name)
        self.assertEqual(json.loads(Path(path).read_text(encoding='utf-8')), json.loads(Path(main.DATA_FILE).read_text(encoding='utf-8')))

    def test_bad_files_refused(self):
        for content in ('{broken', '[1,2]', '{"clients": []}', '{"clients": [5]}'):
            p = Path(self.tmp.name, 'bad.json'); p.write_text(content)
            with self.assertRaises(ValueError):
                transfer.read_import(str(p))

    def test_import_old_base_keeps_totals_and_unknown_fields(self):
        from tests_helpers_legacy import legacy_totals
        expected = legacy_totals(OLD_BASE['clients'], OLD_BASE['profit_correction'])
        data = transfer.read_import(str(self.old_file_path))
        self.assertEqual(transfer.summarize(main.BusinessApp, data), expected)
        backup = transfer.apply_import(self.app, data, main.DATA_FILE)
        self.assertTrue(os.path.exists(backup))
        self.assertIn('ТЕСТ', Path(backup).read_text(encoding='utf-8'))  # прежняя база сохранена
        self.assertEqual(self.app.get_totals(), expected)
        self.assertEqual([c['name'] for c in self.app.clients], [c['name'] for c in OLD_BASE['clients']])
        saved = json.loads(Path(main.DATA_FILE).read_text(encoding='utf-8'))
        self.assertEqual(saved['old_unknown_field'], {'keep': 1})
        self.assertEqual(main.check_integrity(self.app), [])

    def test_failed_import_restores_previous_base(self):
        before = Path(main.DATA_FILE).read_text(encoding='utf-8')
        data = transfer.read_import(str(self.old_file_path))
        real = main.BusinessApp.load_data
        calls = []

        def flaky(app):
            calls.append(1)
            if len(calls) == 1:
                raise OSError('сбой')
            return real(app)
        with patch.object(main.BusinessApp, 'load_data', flaky):
            with self.assertRaises(OSError):
                transfer.apply_import(self.app, data, main.DATA_FILE)
        self.assertEqual(json.loads(Path(main.DATA_FILE).read_text(encoding='utf-8'))['clients'],
                         json.loads(before)['clients'])
        self.assertEqual(self.app.clients[-1]['name'], 'ТЕСТ')

    def test_import_window(self):
        self.screen.confirm_import(str(self.old_file_path))
        Clock.tick()
        pop = next(w for w in Window.children if isinstance(w, Popup) and w.title == 'ЗАМЕНИТЬ БАЗУ?')
        texts = ' '.join(getattr(w, 'text', '') for w in pop.walk())
        self.assertIn('ИЗ ФАЙЛА', texts)
        next(w for w in pop.walk() if isinstance(w, Button) and w.text == 'ЗАМЕНИТЬ').dispatch('on_release')
        self.assertIn('База загружена', self.messages[-1])
        self.assertEqual(self.app.clients[2]['name'], 'САША')


if __name__ == '__main__':
    unittest.main()
