"""Запускается отдельно с плотностью экрана как у Samsung S24 FE (KIVY_METRICS_DENSITY=2.625).
Проверяет окно рулона: текст полей помещается, «СОХРАНИТЬ» выше клавиатуры. Печатает OK или причину."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
from kivy.config import Config
Config.set('graphics', 'width', '1080')
Config.set('graphics', 'height', '2340')
import main
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock

tmp = tempfile.TemporaryDirectory()
main.BASE_PATH, main.DATA_FILE = tmp.name, tmp.name + '/business_data.json'
app = main.BusinessApp(); main.App._running_app = app
app.load_data()
Window.size = (1080, 2340)
screen = main.ClientsScreen(name='p')
screen.refresh_list = lambda: None
screen._roll_edit_popup(0, None)
for _ in range(5):
    Clock.tick()
pop = next(w for w in Window.children if isinstance(w, Popup))
problems = []
for f in (w for w in pop.walk() if isinstance(w, TextInput)):
    inner = f.height - f.padding[1] - f.padding[3]
    if f.line_height > inner + 1:
        problems.append(f'поле «{f.hint_text}»: строка {f.line_height:.0f} > места {inner:.0f}')
save = next(w for w in pop.walk() if isinstance(w, Button) and w.text == 'СОХРАНИТЬ')
bottom = save.to_window(save.x, save.y)[1]
if bottom < Window.height * 0.47:
    problems.append(f'«СОХРАНИТЬ» под клавиатурой: низ кнопки {bottom:.0f} из {Window.height}')
print('OK' if not problems else '; '.join(problems))
