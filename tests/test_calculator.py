"""Шаг 6 плана: «ОТМЕНА ШАГА» — двойное нажатие, удалённый и архивный заказ."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import reverse_order, clear_history

from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock


class CalculatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.append({'name': 'НАСТЯ', 'debt': '0', 'history': []})
        self.app.save_data()
        self.nastya = self.app.clients[-1]
        self.screen = main.ClientsScreen(name='test')
        self.screen.refresh_list = lambda: None
        self.messages = []
        self.screen._stub_popup = lambda t, m: self.messages.append(m)
        self.screen.show_simple_calc(self.app.clients.index(self.nastya), 100)
        Clock.tick()
        self.pop = next(w for w in Window.children if isinstance(w, Popup))
        buttons = [w for w in self.pop.walk() if isinstance(w, Button)]
        self.add_btn = next(w for w in buttons if w.text == 'ДОБАВИТЬ')
        self.undo_btn = next(w for w in buttons if w.text.strip() == 'ОТМЕНА ШАГА')
        self.fields = {}
        for f in (w for w in self.pop.walk() if isinstance(w, TextInput)):
            label = ' '.join(getattr(w, 'text', '') for w in f.parent.parent.children if w is not f.parent)
            for key in ('ДЛИНА', 'ШИРИНА'):
                if key in label:
                    self.fields[key] = f

    def tearDown(self):
        self.pop.dismiss()
        Clock.tick()
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def add(self, l='2', w='3'):
        self.fields['ДЛИНА'].text, self.fields['ШИРИНА'].text = l, w
        self.add_btn.dispatch('on_release')
        time.sleep(0.65)  # защита от двойного «ДОБАВИТЬ» — 0.6 с

    def test_double_tap_undoes_one_step(self):
        self.add(); self.add('1', '1')
        self.assertEqual(len(self.nastya['history']), 2)
        self.undo_btn.dispatch('on_release'); self.undo_btn.dispatch('on_release')
        self.assertEqual(len(self.nastya['history']), 1)
        self.assertEqual(self.nastya['debt'], '600')
        time.sleep(0.85)
        self.undo_btn.dispatch('on_release')
        self.assertEqual(self.nastya['history'], [])
        self.assertEqual(self.nastya['debt'], '0')
        self.assertEqual(self.screen.order_total_accumulator, 0)

    def test_order_deleted_elsewhere_removes_stale_line_only(self):
        self.add(); self.add('1', '1')
        second = self.nastya['history'][-1]
        self.assertTrue(reverse_order(self.app, self.nastya, second)[0])
        debt, history = self.nastya['debt'], list(self.nastya['history'])
        self.undo_btn.dispatch('on_release')
        self.assertIn('уже удалён', self.messages[-1])
        self.assertEqual((self.nastya['debt'], self.nastya['history']), (debt, history))  # первый заказ не тронут
        self.assertEqual(self.screen.order_total_accumulator, 600)
        self.assertEqual(len(self.screen.raw_history_lines), 1)

    def test_archived_order_is_not_reversed(self):
        self.add()
        self.assertTrue(clear_history(self.app, self.nastya)[0])
        before = (self.nastya['debt'], list(self.nastya.get('archived_history', [])), self.screen.order_total_accumulator)
        self.undo_btn.dispatch('on_release')
        self.assertIn('в архиве', self.messages[-1])
        self.assertEqual((self.nastya['debt'], self.nastya['archived_history'], self.screen.order_total_accumulator), before)
        self.assertEqual(len(self.screen.raw_history_lines), 1)


if __name__ == '__main__':
    unittest.main()


class DecimalCommaTests(unittest.TestCase):
    def typed(self, text, **kw):
        field = TextInput(**kw)
        Clock.tick()
        for ch in text:
            field.insert_text(ch)
        Clock.tick()
        return field.text

    def test_comma_becomes_point_in_number_fields(self):
        self.assertEqual(self.typed('2,45', input_filter='float'), '2.45')
        self.assertEqual(self.typed('13.05', input_filter='float'), '13.05')
        self.assertEqual(main.safe_float(self.typed('1,5,5', input_filter='float')), 1.55)  # одна точка
        self.assertEqual(self.typed('Иванов, ООО'), 'Иванов, ООО')  # в обычных полях запятая остаётся


class DisplayTests(unittest.TestCase):
    def test_whole_rubles_on_screen(self):
        self.assertEqual([main.rub(x) for x in ('432 068.06', '640.5', '-1234.49', '0.4')],
                         ['432 068', '641', '-1 234', '0'])

    def test_long_sum_never_hides_client_name(self):
        tmp = tempfile.TemporaryDirectory()
        old = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = tmp.name, tmp.name + '/business_data.json'
        try:
            app = main.BusinessApp(); main.App._running_app = app; app.load_data()
            app.clients.append({'name': 'САША', 'debt': '432 068.06'})
            screen = main.ClientsScreen(name='d')
            row = screen._build_client_row(len(app.clients) - 1)
            name_lbl = next(w for w in row.walk() if isinstance(w, main.Label) and 'САША' in w.text)
            for width in (600, 260, 140):
                name_lbl.width = width
                Clock.tick()
                self.assertIn('САША', name_lbl.text)
                self.assertEqual(name_lbl.max_lines, 1)
            badge = [w.text for w in row.walk() if isinstance(w, main.Label) and 'р' in w.text]
            self.assertTrue(any('432 068 р' in t for t in badge), badge)
        finally:
            main.BASE_PATH, main.DATA_FILE = old
            tmp.cleanup()
