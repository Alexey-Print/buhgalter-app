"""Шаги 2, 5, 6, 8 плана: ошибки записи не теряют данные, исполнитель, калькулятор, общий сброс."""
import copy
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money, reverse_order

from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock

FAIL = patch('accounting.os.replace', side_effect=OSError('disk full'))


class SavingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.extend([
            {'name': 'НАСТЯ', 'debt': '0', 'history': []},
            {'name': 'ОЛЕГ', 'debt': '1000', 'is_creditor': True, 'history': []},
        ])
        self.screen = main.ClientsScreen(name='test')
        self.screen.refresh_list = lambda: None
        self.screen.build_price_grid = lambda mode: None
        self.messages = []
        self.screen._stub_popup = lambda title, msg: self.messages.append(msg)
        self.app.save_data()
        self.nastya, self.oleg = self.app.clients[-2:]

    def tearDown(self):
        for w in list(Window.children):
            if isinstance(w, Popup):
                w.dismiss()
        Clock.tick()
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    # --- helpers ---
    def top_popup(self):
        Clock.tick()
        return next(w for w in Window.children if isinstance(w, Popup))

    def press(self, text, pop=None):
        pop = pop or self.top_popup()
        next(w for w in pop.walk() if isinstance(w, Button) and w.text == text).dispatch('on_release')

    def state(self):
        return (copy.deepcopy(self.app.clients), self.app.profit_correction, copy.deepcopy(self.app.profit_log),
                copy.deepcopy(self.app.rolls), list(self.app.prices), list(self.app.plenka_prices),
                self.app.print_cost)

    def disk(self):
        return Path(main.DATA_FILE).read_bytes()

    def assert_failed_then_retry(self, action, check_done):
        """action() выполняет действие в окне; при сбое записи — всё как было, затем повтор работает."""
        before, disk = self.state(), self.disk()
        with FAIL:
            action()
        self.assertTrue(self.messages and 'повторите' in self.messages[-1], self.messages)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.disk(), disk)
        action()
        self.assertTrue(check_done())
        saved = json.loads(self.disk())
        self.assertEqual(saved['clients'], json.loads(json.dumps(self.app.clients)))

    def idx(self, client):
        return next(i for i, c in enumerate(self.app.clients) if c is client)

    # --- step 2: every window ---
    def test_client_delete_window(self):
        self.screen.show_edit_popup(self.idx(self.nastya))
        pop = self.top_popup()
        self.assert_failed_then_retry(lambda: self.press('УДАЛИТЬ', pop),
                                      lambda: not any(c is self.nastya for c in self.app.clients))

    def test_new_client_window(self):
        self.screen.show_add_popup()
        pop = self.top_popup()
        next(w for w in pop.walk() if isinstance(w, TextInput)).text = 'ДИМА'
        self.assert_failed_then_retry(lambda: self.press('ДОБАВИТЬ', pop),
                                      lambda: self.app.clients[-1]['name'] == 'ДИМА')

    def test_price_window(self):
        self.screen.open_quick_price_edit(0, self.app.prices[0], 'banner_white')
        pop = self.top_popup()
        next(w for w in pop.walk() if isinstance(w, TextInput)).text = '999'
        self.assert_failed_then_retry(lambda: self.press('СОХРАНИТЬ', pop),
                                      lambda: self.app.prices[0] == '999')

    def test_profit_log_clear(self):
        idx, ci = self.idx(self.nastya), self.idx(self.oleg)
        self.assertTrue(self.screen._final_save(idx, '500 руб', None, 'banner_white', print_cost=200,
                        via_malevich=True, creditor_idx=ci, order_desc='2x3'))
        self.screen.show_profit_history_popup()
        hist = self.top_popup()
        self.press('ОЧИСТИТЬ ИСТОРИЮ', hist)
        confirm = self.top_popup()
        self.assert_failed_then_retry(lambda: self.press('ДА, ОЧИСТИТЬ', confirm),
                                      lambda: self.app.profit_log == [])

    # --- step 5: creditor reset keeps links, delete refused when linked ---
    def test_creditor_reset_archives_and_order_still_reversible(self):
        idx, ci = self.idx(self.nastya), self.idx(self.oleg)
        self.assertTrue(self.screen._final_save(idx, '500 руб', None, 'banner_white', print_cost=200,
                        via_malevich=True, creditor_idx=ci, order_desc='2x3'))
        order = self.nastya['history'][-1]
        self.screen.show_malevich_menu(ci)
        menu = self.top_popup()
        self.press('ОБНУЛИТЬ ДОЛГ', menu)
        confirm = self.top_popup()
        self.assert_failed_then_retry(lambda: self.press('ДА, ОБНУЛИТЬ', confirm),
                                      lambda: self.oleg['debt'] == '0')
        self.assertEqual(self.oleg['history'], [])
        self.assertEqual(self.oleg['archived_history'][0]['source_oid'], order['oid'])
        ok, msg = reverse_order(self.app, self.nastya, order)
        self.assertTrue(ok, msg)
        self.assertEqual(self.oleg['debt'], '-200')  # оплаченная печать возвращается переплатой
        self.assertEqual(self.oleg['archived_history'], [])

    def test_linked_creditor_cannot_be_deleted(self):
        idx, ci = self.idx(self.nastya), self.idx(self.oleg)
        self.assertTrue(self.screen._final_save(idx, '500 руб', None, 'banner_white', print_cost=200,
                        via_malevich=True, creditor_idx=ci, order_desc='2x3'))
        self.screen.show_creditor_edit_popup(ci)
        self.press('УДАЛИТЬ')
        self.assertTrue(any(c is self.oleg for c in self.app.clients))
        self.assertIn('Нельзя удалить', self.messages[-1])

    def test_unlinked_creditor_delete_failure_and_retry(self):
        self.app.clients.append({'name': 'КОЗОВ', 'debt': '0', 'is_creditor': True})
        self.app.save_data()
        kozov = self.app.clients[-1]
        self.screen.show_creditor_edit_popup(self.idx(kozov))
        pop = self.top_popup()
        self.assert_failed_then_retry(lambda: self.press('УДАЛИТЬ', pop),
                                      lambda: not any(c is kozov for c in self.app.clients))

    # --- step 8: global reset ---
    def open_global_reset(self):
        self.screen.show_profit_correction_popup()
        self.press('СБРОС ВСЕХ ДАННЫХ', self.top_popup())
        return self.top_popup()

    def test_global_reset_makes_exact_backup_first(self):
        self.nastya['debt'] = '777'
        self.app.save_data()
        expected = json.loads(self.disk())
        confirm = self.open_global_reset()
        self.press('ДА, СБРОСИТЬ ВСЕ', confirm)
        self.assertEqual(self.nastya['debt'], '0')
        copies = list(Path(self.tmp.name, 'backups', 'before_reset').glob('before_reset_*.json'))
        self.assertEqual(len(copies), 1)
        self.assertEqual(json.loads(copies[0].read_text(encoding='utf-8')), expected)

    def test_global_reset_refused_when_backup_fails(self):
        self.nastya['debt'] = '777'
        self.app.save_data()
        before, disk = self.state(), self.disk()
        confirm = self.open_global_reset()
        with patch.object(main.BusinessApp, 'write_verified_backup', side_effect=OSError('нет места')):
            self.press('ДА, СБРОСИТЬ ВСЕ', confirm)
        self.assertIn('Сброс не выполнен', self.messages[-1])
        self.assertEqual((self.state(), self.disk()), (before, disk))

    def test_global_reset_main_write_failure_rolls_back(self):
        self.nastya['debt'] = '777'
        self.app.save_data()
        before, disk = self.state(), self.disk()
        confirm = self.open_global_reset()
        real_replace = os.replace
        calls = []

        def fail_main_file(src, dst):
            calls.append(dst)
            if os.path.abspath(dst) == os.path.abspath(main.DATA_FILE):
                raise OSError('disk full')
            return real_replace(src, dst)
        with patch('accounting.os.replace', side_effect=fail_main_file):
            self.press('ДА, СБРОСИТЬ ВСЕ', confirm)
        self.assertEqual((self.state(), self.disk()), (before, disk))
        self.assertIn('повторите', self.messages[-1])

    # --- step 6 part: no write per keystroke ---
    def test_calculator_typing_does_not_write_each_symbol(self):
        calls = []
        real = self.app.save_data
        self.app.save_data = lambda: (calls.append(1), real())[1]
        self.screen.show_simple_calc(self.idx(self.nastya), 100)
        pop = self.top_popup()
        field = next(w for w in pop.walk() if isinstance(w, TextInput))
        for ch in '1234567890':
            field.text += ch
        Clock.tick()
        self.assertEqual(calls, [])
        time.sleep(1.7)
        Clock.tick()
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
