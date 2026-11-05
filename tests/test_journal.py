"""Журнал операций и автоматическая перепроверка базы."""
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money, reverse_order, change_balance, payment_result, check_integrity, purchase_banner, clear_history


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = self.fresh()
        self.app.clients.extend([
            {'name': 'НАСТЯ', 'debt': '0', 'history': []},
            {'name': 'ОЛЕГ', 'debt': '1000', 'is_creditor': True, 'history': []},
            {'name': 'САША', 'debt': '331 593.4', 'history': []},
        ])
        self.app.save_data()
        self.nastya, self.oleg, self.sasha = self.app.clients[-3:]
        self.screen = main.ClientsScreen(name='test')
        self.screen.refresh_list = lambda: None
        self.screen._stub_popup = lambda t, m: None

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def fresh(self):
        app = main.BusinessApp()
        main.App._running_app = app
        app.load_data()
        return app

    def add(self, client=None, amount=500, cost=200, mode='banner_white', via=True):
        client = client or self.nastya
        idx = self.app.clients.index(client)
        ci = self.app.clients.index(self.oleg)
        self.assertTrue(self.screen._final_save(idx, money(amount) + ' руб', None, mode, print_cost=cost,
                        via_malevich=via, creditor_idx=ci if via else None, order_desc='2x3 x1шт'))
        return client['history'][-1]

    def entries(self, name):
        return [e for e in self.app.journal if e['name'] == name and e['op'] != 'новая карточка']

    def test_order_payment_delete_are_journaled(self):
        order = self.add()
        self.assertEqual([(e['op'][:5], e['was'], e['now']) for e in self.entries('НАСТЯ')], [('заказ', '0', '500')])
        self.assertEqual([(e['was'], e['now']) for e in self.entries('ОЛЕГ')], [('1 000', '1 200')])
        change_balance(self.app, self.nastya, payment_result(self.nastya['debt'], 500), op='оплата')
        self.assertEqual(self.entries('НАСТЯ')[-1]['op'], 'оплата')
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        last = self.entries('НАСТЯ')[-1]
        self.assertTrue(last['op'].startswith('удаление заказа'))
        self.assertEqual((last['was'], last['now']), ('0', '-500'))
        self.assertEqual(check_integrity(self.app), [])

    def test_failed_save_adds_nothing(self):
        self.add()
        count, disk = len(self.app.journal), Path(main.DATA_FILE).read_bytes()
        with patch('accounting.os.replace', side_effect=OSError('disk full')):
            self.assertFalse(change_balance(self.app, self.nastya, 0)[0])
        self.assertEqual(len(self.app.journal), count)
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), disk)
        self.assertTrue(change_balance(self.app, self.nastya, 0)[0])
        self.assertEqual(len(self.app.journal), count + 2)  # долг Насти и корректировка прибыли

    def test_journal_survives_reload_and_explains_balance(self):
        self.add(self.sasha, amount=1949.29, cost=0, via=False)
        change_balance(self.app, self.sasha, payment_result(self.sasha['debt'], 1000), op='оплата')
        other = self.fresh()
        sasha = [e for e in other.journal if e['name'] == 'САША']
        self.assertEqual([(e['op'][:5], e['was'], e['now']) for e in sasha],
                         [('новая', None, '331 593.4'), ('заказ', '331 593.4', '333 542.69'),
                          ('оплат', '333 542.69', '332 542.69')])
        self.assertEqual(check_integrity(other), [])

    def test_change_outside_journal_is_detected(self):
        self.add()
        data = json.loads(Path(main.DATA_FILE).read_text(encoding='utf-8'))
        for c in data['clients']:
            if c['name'] == 'САША':
                c['debt'] = '100'
        Path(main.DATA_FILE).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        problems = check_integrity(self.fresh())
        self.assertTrue(any('САША' in p and 'мимо журнала' in p for p in problems), problems)

    def test_broken_link_is_detected(self):
        self.add()
        self.nastya['history'].clear()  # заказ пропал, начисление Олегу осталось
        problems = check_integrity(self.app)
        self.assertTrue(any('без заказа клиента' in p for p in problems), problems)

    def test_old_base_without_journal_no_false_alarms(self):
        Path(main.DATA_FILE).write_text(json.dumps({'clients': [
            {'name': 'НАСТЯ', 'debt': '500', 'history': [{'date': '01.07.26', 'sum': '500'}]},
            {'name': 'ОЛЕГ', 'debt': '200', 'is_creditor': True, 'history': [{'sum': '200'}]}]},
            ensure_ascii=False), encoding='utf-8')
        app = self.fresh()
        self.assertEqual(check_integrity(app), [])
        self.assertEqual(app.journal, [])

    def test_random_operations_keep_base_consistent(self):
        rnd = random.Random(11)
        _, _, w, b = self.app.get_special_clients()
        live = []
        for step in range(250):
            action = rnd.random()
            if action < .45 or not live:
                self.app.clients[w]['debt'] = money(rnd.choice([0, rnd.uniform(0, 3000)]))
                client = rnd.choice([self.nastya, self.sasha])
                mode = rnd.choice(['banner_white', 'banner_black', 'plenka', 'dop'])
                live.append((client, self.add(client, round(rnd.uniform(1, 5000), 2),
                                              round(rnd.uniform(0, 900), 3), mode, rnd.random() < .7)))
            elif action < .7:
                client, order = live.pop(rnd.randrange(len(live)))
                self.assertTrue(reverse_order(self.app, client, order)[0])
            elif action < .85:
                client = rnd.choice([self.nastya, self.sasha])
                change_balance(self.app, client, payment_result(client['debt'], rnd.uniform(0, 3000)), op='оплата')
            elif action < .92:
                purchase_banner(self.app, rnd.choice(['white', 'black']), round(rnd.uniform(1, 2000), 2))
            else:
                self.app.clients.reverse()
            self.assertEqual(check_integrity(self.app), [], step)
        self.assertEqual(check_integrity(self.fresh()), [])


if __name__ == '__main__':
    unittest.main()
