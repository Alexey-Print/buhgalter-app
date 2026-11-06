"""Дописать позицию в заказ прошлого дня: дата берётся из выбранного дня, суммы те же."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money


class AddToDayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.extend([
            {'name': 'САША', 'debt': '1000', 'history': []},
            {'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True, 'history': []},
        ])
        self.screen = main.ClientsScreen(name='test')
        self.screen.refresh_list = lambda: None
        self.screen._stub_popup = lambda title, msg: None
        self.app.save_data()
        self.sasha, self.oleg = self.app.clients[-2:]

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def save(self):
        idx = self.app.clients.index(self.sasha)
        ci = self.app.clients.index(self.oleg)
        self.assertTrue(self.screen._final_save(idx, money(500) + ' руб', None, 'plenka', print_cost=200,
                        via_malevich=True, creditor_idx=ci, order_desc='2x3 x1шт'))

    def test_past_day(self):
        self.screen._order_date_override = '01.01.20'
        profit_before = self.app.get_totals()[3]
        self.save()
        item = self.sasha['history'][-1]
        self.assertTrue(item['date'].startswith('01.01.20 '))
        self.assertTrue(self.oleg['history'][-1]['date'].startswith('01.01.20 '))
        self.assertEqual(self.sasha['debt'], money(1500))
        self.assertEqual(self.oleg['debt'], money(200))
        self.assertEqual(round(self.app.get_totals()[3] - profit_before, 2), 300)

    def test_normal_entry_resets(self):
        self.screen._order_date_override = '01.01.20'
        idx = self.app.clients.index(self.sasha)
        self.screen.show_client_choice_menu = lambda *a, **k: None
        self.screen.on_client_click(idx)
        self.assertIsNone(self.screen._order_date_override)
        self.save()
        self.assertFalse(self.sasha['history'][-1]['date'].startswith('01.01.20'))


if __name__ == '__main__':
    unittest.main()
