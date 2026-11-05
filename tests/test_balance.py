"""Шаг 4 плана: оплата, переплата и ручное изменение долга не создают ложной прибыли."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money, reverse_order, change_balance, payment_result


class BalanceTests(unittest.TestCase):
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
        self.messages = []
        self.screen._stub_popup = lambda title, msg: self.messages.append(msg)
        self.app.save_data()
        self.nastya, self.oleg = self.app.clients[-2:]

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def profit(self):
        return self.app.get_totals()[3]

    def add(self, amount=500, cost=200):
        idx = self.app.clients.index(self.nastya)
        ci = self.app.clients.index(self.oleg)
        self.assertTrue(self.screen._final_save(idx, money(amount) + ' руб', None, 'banner_white',
                        print_cost=cost, via_malevich=True, creditor_idx=ci, order_desc='2x3 x1шт'))
        return self.nastya['history'][-1]

    def set_debt(self, client, value):
        client['debt'] = money(value)

    def test_seven_transitions(self):
        cases = [(-500, 0, 0), (-500, -200, 0), (-500, 100, 100), (100, 300, 200),
                 (300, 100, 0), (0, -200, 0)]
        for old, new, expected in cases:
            with self.subTest(old=old, new=new):
                self.set_debt(self.nastya, old)
                before = self.profit()
                self.assertTrue(change_balance(self.app, self.nastya, new)[0])
                self.assertEqual(self.nastya['debt'], money(new))
                self.assertEqual(round(self.profit() - before, 2), expected)
        # «отдал 300» при долге 100 → переплата −200, прибыль не меняется
        self.set_debt(self.nastya, 100)
        before = self.profit()
        new = payment_result(self.nastya['debt'], 300)
        self.assertTrue(change_balance(self.app, self.nastya, new)[0])
        self.assertEqual(self.nastya['debt'], '-200')
        self.assertEqual(self.profit(), before)

    def test_payment_toward_zero_from_overpayment(self):
        self.assertEqual(payment_result('-500', 200), -300)
        self.assertEqual(payment_result('-500', 900), 0)
        self.assertEqual(payment_result('100', 300), -200)

    def test_chain_paid_order_deleted_then_zeroed(self):
        start = self.profit()
        order = self.add()
        self.assertTrue(change_balance(self.app, self.nastya, payment_result(self.nastya['debt'], 500))[0])
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.nastya['debt'], '-500')
        self.assertEqual(self.profit(), start)
        self.assertTrue(change_balance(self.app, self.nastya, 0)[0])
        self.assertEqual(self.profit(), start)

    def test_chain_partial_payment_deleted_then_zeroed(self):
        start = self.profit()
        order = self.add(amount=1000, cost=0)
        self.assertTrue(change_balance(self.app, self.nastya, payment_result(self.nastya['debt'], 400))[0])
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual(self.nastya['debt'], '-400')
        self.assertTrue(change_balance(self.app, self.nastya, '0')[0])
        self.assertEqual(self.profit(), start)

    def test_chain_without_payment(self):
        before = (self.app.get_totals(), list(self.app.profit_log))
        order = self.add()
        self.assertTrue(reverse_order(self.app, self.nastya, order)[0])
        self.assertEqual((self.app.get_totals(), self.app.profit_log), before)

    def test_creditor_and_materials_not_touched_by_rule(self):
        before = self.app.profit_correction
        self.assertTrue(change_balance(self.app, self.oleg, 0)[0])
        self.assertEqual(self.app.profit_correction, before)
        _, remainder, white, black = self.app.get_special_clients()
        for i in (remainder, white, black):
            self.assertTrue(change_balance(self.app, self.app.clients[i], 777)[0])
            self.assertEqual(self.app.profit_correction, before)

    def test_save_failure_restores_everything(self):
        self.set_debt(self.nastya, -500)
        self.app.save_data()
        disk = Path(main.DATA_FILE).read_bytes()
        before = (self.nastya['debt'], self.nastya['name'], self.app.profit_correction)
        with patch('accounting.os.replace', side_effect=OSError('disk full')):
            ok, msg = change_balance(self.app, self.nastya, 0, name='НОВОЕ ИМЯ')
        self.assertFalse(ok)
        self.assertIn('повторите', msg)
        self.assertEqual((self.nastya['debt'], self.nastya['name'], self.app.profit_correction), before)
        self.assertEqual(Path(main.DATA_FILE).read_bytes(), disk)
        self.assertTrue(change_balance(self.app, self.nastya, 0)[0])

    def _popup_with(self, opener):
        from kivy.core.window import Window
        from kivy.uix.popup import Popup
        from kivy.clock import Clock
        opener()
        Clock.tick()
        return [w for w in Window.children if isinstance(w, Popup)][0]

    def test_real_debt_window_buttons(self):
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        self.set_debt(self.nastya, -500)
        start = self.profit()
        idx = self.app.clients.index(self.nastya)
        # Окно «ИЗМЕНИТЬ ДОЛГ» клиента: ручной ввод 0
        pop = self._popup_with(lambda: self.screen.show_debt_popup(idx))
        fields = [w for w in pop.walk() if isinstance(w, TextInput)]
        manual = next(f for f in fields if f.hint_text != 'Сумма оплаты...')
        manual.text = '0'
        next(w for w in pop.walk() if isinstance(w, Button) and w.text == 'СОХРАНИТЬ').dispatch('on_release')
        self.assertEqual(self.nastya['debt'], '0')
        self.assertEqual(self.profit(), start)
        # Окно правки клиента: ручной ввод −300 и обратно 0
        self.set_debt(self.nastya, -300)
        start = self.profit()
        pop = self._popup_with(lambda: self.screen.show_edit_popup(idx))
        fields = [w for w in pop.walk() if isinstance(w, TextInput)]
        debt_field = next(f for f in fields if f.text == '-300')
        debt_field.text = '0'
        next(w for w in pop.walk() if isinstance(w, Button) and w.text == 'СОХРАНИТЬ').dispatch('on_release')
        self.assertEqual(self.nastya['debt'], '0')
        self.assertEqual(self.nastya['name'], 'НАСТЯ')
        self.assertEqual(round(self.profit() - start, 2), 0)

    def test_real_quick_edit_window(self):
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        menu = main.MainMenu(name='m')
        menu._refresh_all = lambda: None
        self.set_debt(self.nastya, -500)
        start = self.profit()
        idx = self.app.clients.index(self.nastya)
        pop = self._popup_with(lambda: menu._quick_edit_one(idx, None))
        paid = next(f for f in pop.walk() if isinstance(f, TextInput) and f.hint_text == 'Сумма оплаты...')
        paid.text = '500'
        next(w for w in pop.walk() if isinstance(w, Button) and w.text == 'СОХРАНИТЬ').dispatch('on_release')
        self.assertEqual(self.nastya['debt'], '0')
        self.assertEqual(self.profit(), start)


if __name__ == '__main__':
    unittest.main()
