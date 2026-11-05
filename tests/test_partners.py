"""Автоматический взаимозачёт: один человек и клиент, и исполнитель (Дима Малевич)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money, reverse_order, change_balance, payment_result, check_integrity


class PartnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.extend([
            {'name': 'НАСТЯ', 'debt': '0', 'history': []},
            {'name': 'ДИМА МАЛЕВИЧ', 'debt': '5000', 'is_creditor': True, 'history': []},
        ])
        self.app.save_data()
        self.nastya, self.dima_cr = self.app.clients[-2:]
        self.screen = main.ClientsScreen(name='test')
        self.screen.refresh_list = lambda: None
        self.messages = []
        self.screen._stub_popup = lambda t, m: self.messages.append(m)
        self.start_profit = self.profit()

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def profit(self):
        return self.app.get_totals()[3]

    def add_dima_client(self, name='Дима Малевич'):
        self.app.clients.append({'name': name, 'debt': '0'})
        self.assertTrue(self.app.save_data())
        return self.app.clients[-1]

    def order(self, client, amount, cost=0, via=False):
        idx = self.app.clients.index(client)
        ci = self.app.clients.index(self.dima_cr)
        self.assertTrue(self.screen._final_save(idx, money(amount) + ' руб', None, 'plenka', print_cost=cost,
                        via_malevich=via, creditor_idx=ci if via else None, order_desc='заказ'))
        return client['history'][-1]

    def test_full_cycle(self):
        dima = self.add_dima_client()
        self.assertEqual(dima['partner_cid'], self.dima_cr['cid'])
        # Дима заказал у меня на 3000: я должен ему 5000 → 2000
        o1 = self.order(dima, 3000)
        self.assertEqual((dima['debt'], self.dima_cr['debt']), ('0', '2 000'))
        self.assertEqual(self.profit(), self.start_profit + 3000)
        # Дима напечатал для Насти, печать 1000: мой долг 2000 → 3000
        o2 = self.order(self.nastya, 1500, cost=1000, via=True)
        self.assertEqual((dima['debt'], self.dima_cr['debt']), ('0', '3 000'))
        # Дима заказал ещё на 4000: теперь он должен мне 1000
        o3 = self.order(dima, 4000)
        self.assertEqual((dima['debt'], self.dima_cr['debt']), ('1 000', '0'))
        self.assertEqual(self.profit(), self.start_profit + 3000 + 500 + 4000)
        # Дима отдал мне 1000
        self.assertTrue(change_balance(self.app, dima, payment_result(dima['debt'], 1000), op='оплата')[0])
        self.assertEqual((dima['debt'], self.dima_cr['debt']), ('0', '0'))
        self.assertEqual(self.profit(), self.start_profit + 7500)
        self.assertTrue(any(e['op'] == 'взаимозачёт' for e in self.app.journal))
        self.assertEqual(check_integrity(self.app), [])
        # Удаление всех заказов возвращает исходную картину (оплата 1000 остаётся оплатой)
        for client, o in ((dima, o3), (self.nastya, o2), (dima, o1)):
            ok, msg = reverse_order(self.app, client, o)
            self.assertTrue(ok, msg)
        self.assertEqual((dima['debt'], self.dima_cr['debt']), ('0', '6 000'))
        self.assertEqual(self.profit(), self.start_profit)

    def test_i_pay_him_in_advance(self):
        dima = self.add_dima_client()
        self.assertTrue(change_balance(self.app, self.dima_cr, payment_result('5000', 6000), op='оплата')[0])
        self.assertEqual((dima['debt'], self.dima_cr['debt']), ('1 000', '0'))
        self.assertEqual(self.profit(), self.start_profit)

    def test_link_survives_rename_and_is_not_guessed(self):
        dima = self.add_dima_client()
        self.dima_cr['name'] = 'МАЛЕВИЧ ПЕЧАТЬ'
        self.order(dima, 1000)
        self.assertEqual(self.dima_cr['debt'], '4 000')
        # Два исполнителя с тем же именем — связь не угадывается
        self.app.clients.append({'name': 'ПЕТЯ', 'debt': '100', 'is_creditor': True})
        self.app.clients.append({'name': 'ПЕТЯ', 'debt': '200', 'is_creditor': True})
        self.app.clients.append({'name': 'Петя', 'debt': '50'})
        self.app.save_data()
        self.assertNotIn('partner_cid', self.app.clients[-1])
        self.assertEqual(self.app.clients[-1]['debt'], '50')

    def test_save_failure_nets_nothing(self):
        dima = self.add_dima_client()
        before = (dima['debt'], self.dima_cr['debt'], self.app.profit_correction)
        disk = Path(main.DATA_FILE).read_bytes()
        with patch('accounting.os.replace', side_effect=OSError('disk full')):
            self.assertFalse(change_balance(self.app, dima, 300)[0])
        self.assertEqual((dima['debt'], self.dima_cr['debt'], self.app.profit_correction), before)
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), disk)

    def test_unrelated_clients_untouched(self):
        self.order(self.nastya, 700)
        self.assertEqual((self.nastya['debt'], money(self.dima_cr['debt'])), ('700', '5 000'))


if __name__ == '__main__':
    unittest.main()
