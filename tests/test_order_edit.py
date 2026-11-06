"""Исправление позиции заказа: долг клиента, исполнителя и прибыль пересчитываются, дата и место сохраняются."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money


class OrderEditTests(unittest.TestCase):
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
        self.s = main.ClientsScreen(name='test')
        self.s.refresh_list = lambda: None
        self.msgs = []
        self.s._stub_popup = lambda t, m: self.msgs.append(m)
        self.app.save_data()
        self.sasha, self.oleg = self.app.clients[-2:]

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def add(self, desc, amount, cost, via=True):
        idx = self.app.clients.index(self.sasha)
        ci = self.app.clients.index(self.oleg) if via else None
        self.assertTrue(self.s._final_save(idx, money(amount) + ' руб', None, 'plenka', print_cost=cost,
                        via_malevich=via, creditor_idx=ci, order_desc=desc, price=100, badge='[ПЛ.]'))
        item = self.sasha['history'][-1]
        item['date'] = '01.11.26 10:00'
        return item

    def test_edit_sized(self):
        first = self.add('2x3 x1шт', 600, 300)
        self.add('1x1 x1шт', 100, 50)
        profit0 = self.app.get_totals()[3]
        ok, msg = self.s.apply_order_edit(self.sasha, first, 800, 400, desc='2x4 x1шт', price=100, print_price=50)
        self.assertTrue(ok, msg)
        new = self.sasha['history'][0]
        self.assertEqual(new['desc'], '2x4 x1шт')
        self.assertEqual(new['date'], '01.11.26 10:00')
        self.assertEqual(self.sasha['debt'], money(1000 + 800 + 100))
        self.assertEqual(self.oleg['debt'], money(400 + 50))
        self.assertEqual(round(self.app.get_totals()[3] - profit0, 2), 100)
        self.assertEqual(sum(1 for h in self.oleg['history'] if h.get('source_oid') == new['oid']), 1)
        self.assertEqual(len(self.oleg['history']), 2)

    def test_failure_keeps_everything(self):
        first = self.add('2x3 x1шт', 600, 300)
        before = (self.sasha['debt'], self.oleg['debt'], len(self.sasha['history']), self.app.profit_correction)
        real = self.app.save_data
        calls = []
        def flaky():
            calls.append(1)
            return real() if len(calls) == 1 else False   # отмена прошла, запись новой — сбой
        self.app.save_data = flaky
        ok, _ = self.s.apply_order_edit(self.sasha, first, 800, 400, desc='2x4 x1шт', price=100)
        self.assertFalse(ok)
        self.assertEqual((self.sasha['debt'], self.oleg['debt'], len(self.sasha['history']), self.app.profit_correction), before)
        self.assertEqual(self.sasha['history'][0]['desc'], '2x3 x1шт')
        self.app.save_data = real

    def test_regex(self):
        m = main.ClientsScreen._ORDER_RE.match('8.02x1.015 x1шт')
        self.assertEqual(m.groups(), ('8.02', '1.015', '1'))


if __name__ == '__main__':
    unittest.main()
