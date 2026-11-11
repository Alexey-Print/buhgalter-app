"""3.2: заказы на своей печати сначала гасят минус рулона, прибыль — только остаток."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
import transfer
from accounting import money, reverse_order, purchase_banner, change_balance


class RollPaybackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.append({'name': 'САША', 'debt': '0', 'history': []})
        self.app.save_data()
        self.sasha = self.app.clients[-1]
        self.screen = main.ClientsScreen(name='t')
        self.screen.refresh_list = lambda: None
        self.screen._stub_popup = lambda *a: None

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def profit(self):
        return self.app.get_totals()[3]

    def order(self, amount, mode='banner_black'):
        idx = next(i for i, c in enumerate(self.app.clients) if c is self.sasha)
        self.assertTrue(self.screen._final_save(idx, money(amount) + ' руб', None, mode, order_desc='1x1 x1шт'))
        return self.sasha['history'][-1]

    def black(self):
        return self.app.clients[self.app.get_special_clients()[3]]

    def test_profit_stands_until_roll_paid(self):
        self.assertTrue(purchase_banner(self.app, 'black', 6053)[0])
        self.assertEqual(self.profit(), 0)                 # закупка прибыль не трогает
        self.order(6000)
        self.assertEqual(self.profit(), 0)                 # всё ушло в рулон
        self.assertEqual(self.black()['debt'], '53')
        last = self.order(1000)
        self.assertEqual(self.profit(), 947)               # минус погашен, остаток — прибыль
        self.assertEqual(self.app.profit_log[-1]['profit'], 947)
        self.assertEqual(self.app.profit_log[-1]['to_roll'], 53)
        self.assertNotIn('assumed', self.app.profit_log[-1])
        self.assertTrue(reverse_order(self.app, self.sasha, last)[0])
        self.assertEqual(self.profit(), 0)
        self.assertEqual(self.black()['debt'], '53')

    def test_profit_percent_from_invested(self):
        self.assertIsNone(self.app.profit_percent())
        self.assertTrue(purchase_banner(self.app, 'black', 900)[0])
        self.order(1000)                      # 900 в рулон, 100 прибыль -> 100 / 900
        self.assertEqual(self.app.profit_percent(), 11)
        self.order(1000)                      # +1000 прибыль -> 1100 / 900
        self.assertEqual(self.app.profit_percent(), 122)

    def plenka(self):
        return self.app.clients[self.app.plenka_index()]

    def test_plenka_purchase_paid_by_own_print(self):
        self.assertTrue(purchase_banner(self.app, 'plenka', 2000, '1.5', 50)[0])
        self.assertEqual(self.plenka()['debt'], '2 000')
        self.assertEqual(self.profit(), 0)
        self.assertNotIn(self.plenka(), [])            # карточка есть
        n_rolls = len(self.app.rolls)
        first = self.order(1500, mode='plenka_gloss')
        self.assertEqual(self.profit(), 0)
        self.assertEqual(self.plenka()['debt'], '500')
        self.order(1000, mode='plenka_matte')
        self.assertEqual(self.profit(), 500)
        self.assertEqual(self.app.profit_log[-1]['to_roll'], 500)
        self.assertEqual(len(self.app.rolls), n_rolls)  # метры банера плёнка не трогает
        self.assertEqual(self.app.get_totals()[0], 2500)  # «ПЛЁНКА» не считается долгом клиента
        self.assertTrue(reverse_order(self.app, self.sasha, first)[0])
        self.assertEqual(self.plenka()['debt'], '1 500')
        self.assertEqual(main.check_integrity(self.app), [])

    def test_editing_roll_minus_keeps_profit(self):
        self.order(500)
        p0 = self.profit()
        self.assertTrue(change_balance(self.app, self.black(), '3000')[0])
        self.assertEqual(self.profit(), p0)

    def test_set_total_profit(self):
        self.assertTrue(purchase_banner(self.app, 'black', 1000)[0])
        self.order(300)
        self.app.profit_correction = money(main.safe_float(self.app.profit_correction))
        tot = self.app.get_totals()[0]
        self.app.profit_correction = str(round(1234 - tot, 2))
        self.assertEqual(self.profit(), 1234)

    def _old_data(self):
        return {'clients': [
            {'name': 'БАННЕР ОСТАТОК', 'debt': '0', 'role': 'remainder', 'cid': 'r'},
            {'name': 'МАЛЕВИЧ', 'debt': '0', 'is_creditor': True, 'cid': 'm'},
            {'name': 'САША', 'debt': '5000', 'cid': 's', 'history': [
                {'oid': 'o1', 'sum': '5000', 'print_cost': 0, 'mode': 'banner_black',
                 'banner_deduction': 2698, 'banner_deduction_id': 'b', 'date': '06.11.26 10:00'}]},
            {'name': 'БЕЛЫЙ БАНЕР', 'debt': '0', 'role': 'white', 'cid': 'w'},
            {'name': 'ЧЕРНЫЙ БАНЕР', 'debt': '6053', 'role': 'black', 'cid': 'b'}],
            'profit_correction': '-2698', 'roles_version': 1,
            'profit_log': [{'oid': 'o1', 'name': 'САША', 'date': '06.11.26 10:00', 'profit': 5000, 'assumed': True}]}

    def test_migration_keeps_numbers_and_rewrites_log(self):
        data = self._old_data()
        old_profit = 5000 - 2698 - 6053
        self.assertEqual(transfer.summarize(main.BusinessApp, data)[3], old_profit)
        import json
        with open(main.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        app = main.BusinessApp()
        main.App._running_app = app
        app.load_data()
        self.assertEqual(app.get_totals()[3], old_profit)        # цифра на экране та же
        entry = app.profit_log[0]
        self.assertEqual((entry['profit'], entry['to_roll']), (2302, 2698))
        self.assertNotIn('assumed', entry)
        app2 = main.BusinessApp()                                  # повторно не переносится
        main.App._running_app = app2
        app2.load_data()
        self.assertEqual(app2.get_totals()[3], old_profit)
        self.assertEqual(app2.profit_log[0]['profit'], 2302)


if __name__ == '__main__':
    unittest.main()
