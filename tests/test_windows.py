"""Каждое окно с записью открывается и сохраняется через настоящие кнопки (без падений)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main

from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp(); main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.append({'name': 'ОЛЕГ', 'debt': '100', 'is_creditor': True, 'history': []})
        self.app.save_data()
        self.screen = main.ClientsScreen(name='w')
        self.screen.refresh_list = lambda: None
        self.messages = []
        self.screen._stub_popup = lambda t, m: self.messages.append(m)

    def tearDown(self):
        for w in list(Window.children):
            if isinstance(w, Popup):
                w.dismiss()
        Clock.tick()
        main.BASE_PATH, main.DATA_FILE = self.old
        self.tmp.cleanup()

    def popup(self, title=None):
        Clock.tick()
        return next(w for w in Window.children if isinstance(w, Popup) and (title is None or w.title == title))

    def press(self, pop, text):
        next(w for w in pop.walk() if isinstance(w, Button) and w.text == text).dispatch('on_release')

    def field(self, pop, hint):
        return next(w for w in pop.walk() if isinstance(w, TextInput) and w.hint_text == hint)

    def test_existing_roll_remaining_meters(self):
        self.assertTrue(self.app.rolls)          # рулон 75 м из заготовки
        self.screen._roll_edit_popup(0, None)
        pop = self.popup('РУЛОН')
        self.field(pop, 'сколько осталось').text = '63'
        self.press(pop, 'СОХРАНИТЬ')
        self.assertEqual(self.app.rolls[0]['remain'], '63')
        self.assertEqual(self.messages, [])
        self.assertEqual(main.BusinessApp.__new__(main.BusinessApp).__class__, main.BusinessApp)

    def test_roll_usage_and_new_roll_and_delete(self):
        self.screen._roll_edit_popup(0, None)
        pop = self.popup('РУЛОН')
        self.field(pop, 'расход, м').text = '12,5'
        self.press(pop, 'СОХРАНИТЬ')
        self.assertEqual(self.app.rolls[0]['remain'], '62.5')
        self.screen._roll_edit_popup(None, None)
        pop = self.popup('НОВЫЙ РУЛОН')
        self.press(pop, 'ЧЁРНЫЙ') if any(isinstance(w, Button) and w.text == 'ЧЁРНЫЙ' for w in pop.walk()) else None
        self.field(pop, 'длина всего').text = '50'
        self.field(pop, 'сколько осталось').text = '50'
        self.press(pop, 'СОХРАНИТЬ')
        self.assertEqual(len(self.app.rolls), 2)
        self.screen._roll_edit_popup(1, None)
        self.press(self.popup('РУЛОН'), 'УДАЛИТЬ')
        self.assertEqual(len(self.app.rolls), 1)
        self.assertEqual(self.messages, [])

    def test_creditor_rename_and_add(self):
        idx = next(i for i, c in enumerate(self.app.clients) if c['name'] == 'ОЛЕГ')
        self.screen.show_creditor_edit_popup(idx)
        pop = self.popup()
        name = next(w for w in pop.walk() if isinstance(w, TextInput) and w.text == 'ОЛЕГ')
        name.text = 'ОЛЕГ ПЕЧАТЬ'
        self.press(pop, 'СОХРАНИТЬ')
        self.assertEqual(self.app.clients[idx]['name'], 'ОЛЕГ ПЕЧАТЬ')
        self.screen.show_creditor_edit_popup(idx)
        pop = self.popup()
        next(w for w in pop.walk() if isinstance(w, TextInput) and 'Имя нового' in w.hint_text).text = 'КОЗОВ'
        self.press(pop, '+ ДОБАВИТЬ НОВОГО')
        self.assertTrue(any(c['name'] == 'КОЗОВ' and c.get('is_creditor') for c in self.app.clients))
        self.assertEqual(self.messages, [])

    def test_profit_correction_save(self):
        self.screen.show_profit_correction_popup()
        pop = self.popup()
        f = next(w for w in pop.walk() if isinstance(w, TextInput))
        f.text = '1500'
        self.press(pop, 'СОХРАНИТЬ')
        self.assertEqual(self.app.get_totals()[3], 1500)
        self.assertEqual(self.messages, [])

    def test_export_button(self):
        self.screen.show_profit_correction_popup()
        self.press(self.popup(), 'ЭКСПОРТ')
        self.assertIn('Копия базы сохранена', self.messages[-1])


if __name__ == '__main__':
    unittest.main()


class RollKeyboardTests(WindowTests):
    def test_enter_key_saves_roll(self):
        self.screen._roll_edit_popup(0, None)
        pop = self.popup('РУЛОН')
        f = self.field(pop, 'сколько осталось')
        f.text = '68'
        f.dispatch('on_text_validate')
        self.assertEqual(self.app.rolls[0]['remain'], '68')
        self.assertEqual(self.messages, [])

    def test_save_button_is_in_upper_part(self):
        """Все поля и «СОХРАНИТЬ» помещаются в верхние ~55% окна (над клавиатурой)."""
        Window.size = (1080, 2340)
        self.screen._roll_edit_popup(0, None)
        pop = self.popup('РУЛОН')
        for _ in range(3):
            Clock.tick()
        save = next(w for w in pop.walk() if isinstance(w, Button) and w.text == 'СОХРАНИТЬ')
        bottom_of_save = save.to_window(save.x, save.y)[1]
        self.assertGreater(bottom_of_save, Window.height * 0.45, bottom_of_save)
