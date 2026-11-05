import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money, reverse_order, purchase_banner, clear_history


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.path, self.path + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.extend([
            {'name': 'НАСТЯ', 'debt': '0', 'history': []},
            {'name': 'ОЛЕГ', 'debt': '1000', 'is_creditor': True, 'history': []},
            {'name': 'САША', 'debt': '331 593.4', 'history': []},
        ])
        self.screen = main.ClientsScreen(name='test')
        self.screen.refresh_list = lambda: None
        self.messages = []
        self.screen._stub_popup = lambda title, msg: self.messages.append(msg)
        self.app.save_data()
        self.nastya, self.oleg, self.sasha = self.app.clients[-3:]

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def add(self, client=None, amount=500, cost=200, mode='banner_white', via=True):
        client = client if client is not None else self.nastya
        idx = next(i for i,c in enumerate(self.app.clients) if c is client)
        ci = next(i for i,c in enumerate(self.app.clients) if c is self.oleg)
        self.assertTrue(self.screen._final_save(idx, money(amount)+' руб', None, mode, print_cost=cost,
                        via_malevich=via, creditor_idx=ci if via else None, order_desc='2x3 x1шт'))
        return client['history'][-1]

    def test_kopecks_and_nonfinite(self):
        self.assertEqual(money('1949.29'), '1 949.29')
        self.assertEqual(money('1,01'), '1.01')
        self.assertEqual(money(-0.01), '-0.01')
        self.assertEqual(main.safe_float('nan'), 0)
        self.assertEqual(main.safe_float('inf'), 0)

    def test_nastya_oleg_exact_reversal(self):
        before = self.app.get_totals()
        order = self.add()
        self.assertEqual(self.oleg['debt'], '1 200')
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.oleg['debt'], '1 000')
        self.assertEqual(self.app.get_totals(), before)
        self.assertEqual(self.app.profit_log, [])

    def test_duplicate_amount_date_and_rename_reorder(self):
        first = self.add(); second = self.add()
        first['date'] = second['date']
        self.oleg['name'] = 'ОЛЕГ НОВОЕ ИМЯ'
        self.app.clients.reverse()
        self.assertTrue(reverse_order(self.app, self.nastya, first)[0])
        self.assertEqual(self.oleg['debt'], '1 200')
        self.assertEqual(self.nastya['history'], [second])
        self.assertEqual(self.oleg['history'][0]['source_oid'], second['oid'])

    def test_customer_and_creditor_overpayment(self):
        order = self.add(amount=1000)
        self.nastya['debt'] = '600'  # payment 400
        self.oleg['debt'] = '50'  # paid contractor 1150
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.nastya['debt'], '-400')
        self.assertEqual(self.oleg['debt'], '-150')

    def test_sasha_existing_balance_not_rebuilt(self):
        order = self.add(self.sasha, amount=1949.29, cost=0, via=False)
        self.assertEqual(self.sasha['debt'], '333 542.69')
        self.assertTrue(reverse_order(self.app, self.sasha, order)[0])
        self.assertEqual(self.sasha['debt'], '331 593.4')

    def test_missing_legacy_link_refuses_all_changes(self):
        order = self.add()
        del self.oleg['history'][0]['source_oid']
        before = copy.deepcopy((self.app.clients, self.app.profit_correction, self.app.profit_log))
        self.assertFalse(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual((self.app.clients, self.app.profit_correction, self.app.profit_log), before)

    def test_direct_linked_creditor_delete_refused(self):
        self.add()
        self.assertFalse(reverse_order(self.app, self.oleg, self.oleg['history'][0])[0])
        self.assertEqual(self.oleg['debt'], '1 200')

    def test_double_delete(self):
        order = self.add()
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        before = copy.deepcopy(self.app.clients)
        self.assertFalse(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.app.clients, before)

    def test_purchase_profit_negative_and_both_colors(self):
        self.app.profit_correction = money(5000 - main.safe_float(self.sasha['debt']))
        self.assertEqual(self.app.get_totals()[3], 5000)
        self.assertTrue(purchase_banner(self.app, 'white', 10000.01, '3.2', 50)[0])
        self.assertEqual(self.app.get_totals()[3], -5000.01)
        self.assertEqual(self.app.rolls[-1]['remain'], '50')
        self.assertTrue(purchase_banner(self.app, 'black', 2000)[0])
        before = self.app.get_totals()
        order = self.add(amount=11000.02)
        self.app.clients.reverse()
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.app.get_totals(), before)

    def test_clear_history_preserves_totals_and_links(self):
        order = self.add()
        before = self.app.get_totals()
        self.assertTrue(clear_history(self.app, self.oleg)[0])
        self.assertEqual(self.app.get_totals(), before)
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.oleg['debt'], '1 000')
        self.add()
        before = self.app.get_totals()
        history = self.nastya['history']
        self.assertTrue(clear_history(self.app, self.nastya)[0])
        self.assertEqual(history, [])
        self.assertEqual(self.app.get_totals(), before)

    def test_reverse_save_failure_restores_references_and_disk(self):
        order = self.add(); history = self.nastya['history']
        before = copy.deepcopy(self.app.clients)
        disk = Path(main.DATA_FILE).read_bytes()
        with patch('accounting.os.replace', side_effect=OSError('disk full')):
            self.assertFalse(reverse_order(self.app, self.nastya, order)[0])
        self.assertIs(self.nastya['history'], history)
        self.assertIs(history[0], order)
        self.assertEqual(self.app.clients, before)
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), disk)
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])

    def test_add_and_purchase_save_failure(self):
        before = copy.deepcopy(self.app.clients)
        with patch('accounting.os.replace', side_effect=OSError('disk full')):
            self.assertFalse(self.screen._final_save(len(self.app.clients)-3, '500 руб', None))
            self.assertFalse(purchase_banner(self.app, 'white', 1000)[0])
        self.assertEqual(self.app.clients, before)

    def test_roundtrip_and_unknown_fields(self):
        order = self.add(amount=672.34, cost=201.22)
        self.app._extra_data = {'future_key': {'preserve': True}}
        self.app.save_data()
        before = copy.deepcopy(self.app.clients)
        other = main.BusinessApp(); other.load_data()
        self.assertEqual(other.clients, before)
        self.assertEqual(other._extra_data['future_key'], {'preserve': True})
        self.assertEqual(other.profit_log, self.app.profit_log)
        self.assertEqual(other.rolls, self.app.rolls)
        self.assertTrue(reverse_order(other, other.clients[-3], other.clients[-3]['history'][0])[0])

    def test_corrupt_without_backup_never_overwritten(self):
        import shutil
        shutil.rmtree(self.path + '/backups')
        Path(main.DATA_FILE).write_text('{broken')
        other = main.BusinessApp()
        with self.assertRaises(RuntimeError):
            other.load_data()
        self.assertEqual(Path(main.DATA_FILE).read_text(), '{broken')

    def test_actual_kivy_build(self):
        root = self.app.build()
        self.assertEqual(root.screen_names, ['main_menu', 'clients_screen'])

    def test_calculator_buttons_add_and_undo_after_reorder(self):
        from kivy.core.window import Window
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        from kivy.uix.popup import Popup
        from kivy.clock import Clock
        idx = next(i for i,c in enumerate(self.app.clients) if c is self.nastya)
        ci = next(i for i,c in enumerate(self.app.clients) if c is self.oleg)
        self.screen.show_simple_calc(idx, 100, via_malevich=True, creditor_idx=ci)
        Clock.tick()
        pop = next(w for w in Window.children if isinstance(w, Popup))
        fields = [w for w in pop.walk() if isinstance(w, TextInput)]
        # Size fields are the inputs with those visible hints.
        for field in fields:
            label = ' '.join(getattr(w, 'text', '') for w in field.parent.parent.children if w is not field.parent)
            if 'ДЛИНА' in label:
                field.text = '2'
            elif 'ШИРИНА' in label:
                field.text = '3'
        buttons = [w for w in pop.walk() if isinstance(w, Button)]
        add = next(w for w in buttons if w.text == 'ДОБАВИТЬ')
        undo = next(w for w in buttons if w.text.strip() == 'ОТМЕНА ШАГА')
        self.app.clients.reverse()
        add.dispatch('on_release')
        self.assertEqual(len(self.nastya['history']), 1, [(w.hint_text, w.text) for w in fields])
        self.assertEqual(self.nastya['debt'], '600')
        undo.dispatch('on_release')
        self.assertEqual(self.nastya['debt'], '0')
        self.assertEqual(self.oleg['debt'], '1 000')
        pop.dismiss()
