import json
import os
import re
import time
import math
import uuid
from accounting import number, money, ensure_ids, snapshot, restore, atomic_write, reverse_order, purchase_banner, clear_history, period_totals
from datetime import datetime
from collections import defaultdict

from kivy.config import Config
Config.set('kivy', 'log_level', 'error')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Rectangle, Mesh
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import ListProperty, NumericProperty

try:
    Window.softinput_mode = 'below_target'
except Exception:
    pass

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_PATH, "business_data.json")

# Фото пользователя, вшитое в код (JPEG, base64). Отдельный файл не нужен.
_AVATAR_B64 = "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"

def safe_float(val, default=0.0):
    return number(val, default)


def format_num_simple(val):
    return money(val)


def _dark_input(**kw):
    """Тёмное поле ввода в стиле приложения (вместо блеклого белого)."""
    ti = TextInput(multiline=False, halign='center', font_size='22sp',
                   background_normal='', background_active='',
                   background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1),
                   hint_text_color=(0.55, 0.6, 0.68, 1),
                   cursor_color=(0.2, 0.75, 0.84, 1), padding=[10, 40, 10, 16], **kw)

    def _sel_all(inst, val):
        if val:
            from kivy.clock import Clock as _Ck
            _Ck.schedule_once(lambda dt: inst.select_all(), 0.05)
    ti.bind(focus=_sel_all)
    return ti


def _bordered_field(field, accent=(0.4, 0.8, 1, 1), height=118, width_frac=1.0):
    """Оборачивает поле в подсвеченную рамку; при width_frac<1 — уже и по центру."""
    box = BoxLayout(size_hint_y=None, height=height, padding=[5, 5, 5, 5])
    field.size_hint_y = 1

    def _d(w, *a):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(accent[0], accent[1], accent[2], 0.9)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[(18, 18)] * 4)
    box.bind(pos=_d, size=_d)
    box.add_widget(field)
    if width_frac >= 0.999:
        return box
    box.size_hint_x = width_frac
    wrap = BoxLayout(orientation='horizontal', size_hint_y=None, height=height)
    sp = (1.0 - width_frac) / 2.0
    wrap.add_widget(Widget(size_hint_x=sp))
    wrap.add_widget(box)
    wrap.add_widget(Widget(size_hint_x=sp))
    return wrap

class RoundedButton(Button):
    bg_color = ListProperty([0.1, 0.4, 0.8, 1])

    def __init__(self, bg_color=(0.1, 0.4, 0.8, 1), radius=15, **kwargs):
        self.register_event_type('on_long_press')
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.original_color = list(bg_color)
        self.bg_color = list(bg_color)
        self.radius = [(radius, radius), (radius, radius), (radius, radius), (radius, radius)]
        self.long_press_time = 0.8
        self.long_press_trigger = None
        self._long_press_fired = False
        self.halign = 'center'
        self.valign = 'middle'
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas, bg_color=self.update_canvas)
        self.bind(size=lambda s, v: setattr(s, 'text_size', (s.width - 20, s.height - 10)))

    def on_state(self, instance, value):
        if value == 'down':
            self._long_press_fired = False
            self.long_press_trigger = Clock.schedule_once(self._on_long_press, self.long_press_time)
        elif self.long_press_trigger:
            Clock.unschedule(self.long_press_trigger)
            self.long_press_trigger = None

    def _on_long_press(self, dt):
        self.long_press_trigger = None
        self._long_press_fired = True
        self.dispatch('on_long_press')

    def on_long_press(self, *args): pass

    def on_touch_up(self, touch):
        if self._long_press_fired and touch.grab_current is self:
            touch.ungrab(self)
            self._touch = None
            self._long_press_fired = False
            self.state = 'normal'
            return True
        return super().on_touch_up(touch)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(*[min(c * 1.6, 1) for c in self.original_color[:3]], 1)
            else:
                Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

class RowButton(ButtonBehavior, BoxLayout):
    bg_color = ListProperty([0.1, 0.4, 0.8, 1])

    def __init__(self, left_text, right_text, bg_color=(0.1, 0.4, 0.8, 1), radius=15, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = [20, 10, 20, 10]
        self.spacing = 10
        self.original_color = list(bg_color)
        self.bg_color = list(bg_color)
        self.radius = [(radius, radius), (radius, radius), (radius, radius), (radius, radius)]
        self.left_lbl = Label(text=left_text, markup=True, halign='left', valign='middle')
        self.left_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.right_lbl = Label(text=right_text, markup=True, halign='right', valign='middle')
        self.right_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.add_widget(self.left_lbl)
        self.add_widget(self.right_lbl)
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas, bg_color=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(*[min(c * 1.6, 1) for c in self.original_color[:3]], 1)
            else:
                Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

    def update_texts(self, left_text, right_text):
        self.left_lbl.text = left_text
        self.right_lbl.text = right_text

class BgLabel(Label):
    bg_color = ListProperty([0, 0, 0, 0])

    def __init__(self, radius=8, **kwargs):
        super().__init__(**kwargs)
        self.radius = [(radius, radius), (radius, radius), (radius, radius), (radius, radius)]
        self.bind(pos=self.update_canvas, size=self.update_canvas, bg_color=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)

class CalendarButton(Button):
    def __init__(self, date_str, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.markup = True
        self.halign = 'center'
        self.valign = 'middle'
        self.padding = [0, 15]
        self.date_str = date_str
        self.bind(pos=self.update_canvas, size=self.update_canvas, state=self.update_canvas)
        self.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.update_look()

    def set_date(self, date_str):
        self.date_str = date_str
        self.update_look()

    def update_look(self, *args):
        self.text = f"[color=#FFFFFF][size=6sp] [/size][/color]\n[color=#111111][size=17sp][b]{self.date_str}[/b][/size][/color]"

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            if self.state == 'down':
                Color(0.85, 0.85, 0.85, 1)
            else:
                Color(0.98, 0.98, 0.98, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[(12, 12), (12, 12), (12, 12), (12, 12)])
            if self.state == 'down':
                Color(0.7, 0.15, 0.15, 1)
            else:
                Color(0.9, 0.25, 0.25, 1)
            RoundedRectangle(pos=(self.x, self.y + self.height * 0.7), size=(self.width, self.height * 0.3), radius=[(0, 0), (0, 0), (12, 12), (12, 12)])
            Color(0.15, 0.15, 0.15, 1)
            hw = self.width * 0.14
            hh = self.height * 0.22
            y_ring = self.y + self.height * 0.90
            RoundedRectangle(pos=(self.x + self.width * 0.2, y_ring), size=(hw, hh), radius=[(4, 4), (4, 4), (4, 4), (4, 4)])
            RoundedRectangle(pos=(self.x + self.width * 0.8 - hw, y_ring), size=(hw, hh), radius=[(4, 4), (4, 4), (4, 4), (4, 4)])

class EditButton(RoundedButton):
    def update_canvas(self, *args):
        super().update_canvas(*args)
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 1)
            cx, cy, d = self.center_x, self.center_y, 14
            Line(points=[cx-d-3, cy-d+3, cx+d-3, cy+d+3], width=1.5)
            Line(points=[cx-d+3, cy-d-3, cx+d+3, cy+d+3], width=1.5)
            Line(points=[cx-d-3, cy-d+3, cx-d+3, cy-d-3], width=1.5)
            Line(points=[cx-d-4, cy-d-4, cx-d-3, cy-d+3], width=1.5)
            Line(points=[cx-d-4, cy-d-4, cx-d+3, cy-d-3], width=1.5)
            tip_x, tip_y = cx+d+6, cy+d+6
            Line(points=[cx+d-3, cy+d+3, tip_x, tip_y], width=1.5)
            Line(points=[cx+d+3, cy+d-3, tip_x, tip_y], width=1.5)
            Line(points=[cx+d, cy+d, tip_x, tip_y], width=1.8)

class CancelButton(RoundedButton):
    def __init__(self, bg_color=(0.7, 0.2, 0.2, 1), **kwargs):
        if 'text' in kwargs and kwargs['text']:
            kwargs['text'] = "    " + kwargs['text'].strip()
        super().__init__(bg_color=bg_color, **kwargs)

    def update_canvas(self, *args):
        super().update_canvas(*args)
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 1)
            cx, cy = self.center_x, self.center_y
            if self.text.strip():
                lx = self.x + 40
                Line(points=[lx-10, cy-10, lx+10, cy+10], width=2)
                Line(points=[lx-10, cy+10, lx+10, cy-10], width=2)
            else:
                Line(points=[cx-12, cy-12, cx+12, cy+12], width=2)
                Line(points=[cx-12, cy+12, cx+12, cy-12], width=2)


class SlideBackButton(Widget):
    """Белый кружок справа со стрелкой влево. Тяни влево для перехода назад."""
    handle_pos = NumericProperty(1.0)

    def __init__(self, callback=None, text="<<< НАЗАД",
                 bg_color=(1, 0.45, 0, 1), **kwargs):
        super().__init__(**kwargs)
        self.callback   = callback
        self._bg        = list(bg_color)
        self._triggered = False
        self._touch_id  = None
        self._start_x   = 0.0
        self._start_hp  = 1.0
        self._lbl = Label(
            text=text, font_size='20sp', bold=True,
            color=(0, 0, 0, 1), halign='center', valign='middle'
        )
        self.add_widget(self._lbl)
        self.bind(pos=self._sync, size=self._sync, handle_pos=self._redraw)

    def _sync(self, *args):
        h = self.height
        lbl_w = max(1, self.width - h)
        self._lbl.pos       = (self.x, self.y)
        self._lbl.size      = (lbl_w, h)
        self._lbl.text_size = (lbl_w, h)
        self._redraw()

    def _hcx(self):
        pad    = self.height / 2.0
        usable = max(1.0, self.width - self.height)
        return self.x + pad + usable * self.handle_pos

    def _redraw(self, *args):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 4 or h < 4:
            return
        rp  = min(h / 2.0, 46)
        hcx = self._hcx()
        t   = 1.0 - self.handle_pos
        pad = 6
        cr  = h - pad * 2
        with self.canvas.before:
            Color(0, 0, 0, 0.22)
            RoundedRectangle(pos=(x + 5, y - 5), size=(w, h), radius=[(rp, rp)] * 4)
            Color(
                self._bg[0] * (1 - t) + 0.08 * t,
                self._bg[1] * (1 - t) + 0.72 * t,
                self._bg[2] * (1 - t) + 0.08 * t,
                1
            )
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[(rp, rp)] * 4)
            Color(1, 1, 1, 1)
            Ellipse(pos=(hcx - cr / 2.0, y + pad), size=(cr, cr))
            Color(0, 0, 0, 0.85)
            cy_c = y + h / 2.0
            aw   = cr * 0.26
            al   = cr * 0.28
            Line(points=[hcx + al * 0.55, cy_c,
                         hcx - al * 0.68, cy_c], width=3.2)
            Line(points=[hcx - al * 0.68, cy_c,
                         hcx - al * 0.68 + aw * 0.78, cy_c + aw * 0.62], width=3.2)
            Line(points=[hcx - al * 0.68, cy_c,
                         hcx - al * 0.68 + aw * 0.78, cy_c - aw * 0.62], width=3.2)

    def on_touch_down(self, touch):
        if self._triggered or not self.collide_point(*touch.pos):
            return False
        self._touch_id = touch.uid
        self._start_x  = touch.x
        self._start_hp = self.handle_pos
        return True

    def on_touch_move(self, touch):
        if touch.uid != self._touch_id or self._triggered:
            return False
        usable          = max(1, self.width * 0.6)
        delta           = (touch.x - self._start_x) / usable
        self.handle_pos = max(0.0, min(1.0, self._start_hp + delta))
        if self.handle_pos <= 0.04:
            self._triggered = True
            self._fire()
        return True

    def on_touch_up(self, touch):
        if touch.uid != self._touch_id:
            return False
        self._touch_id = None
        if not self._triggered and self.handle_pos > 0.04:
            Animation(handle_pos=1.0, duration=0.35, t='out_back').start(self)
        return True

    def _fire(self):
        Animation.cancel_all(self)
        anim = Animation(handle_pos=0.0, duration=0.10)
        def _done(a, w):
            if self.callback:
                self.callback()
            Clock.schedule_once(lambda dt: self._reset(), 0.55)
        anim.bind(on_complete=_done)
        anim.start(self)

    def _reset(self):
        self._triggered = False
        if self.parent:
            Animation(handle_pos=1.0, duration=0.35, t='out_back').start(self)
        else:
            self.handle_pos = 1.0


class NeonButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.bold = True
        self.font_size = '26sp'
        self.halign = 'center'
        self.valign = 'middle'
        self._pulse = 0.0
        self._pulse_dir = 1
        self._anim_event = Clock.schedule_interval(self._tick, 1/20)
        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw)
        self.bind(size=lambda s, v: setattr(s, 'text_size', (s.width - 20, s.height - 10)))

    def _tick(self, dt):
        self._pulse += dt * 1.2 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._pulse_dir = 1
        self._redraw()

    def on_parent(self, instance, value):
        if value is None and self._anim_event:
            self._anim_event.cancel()
            self._anim_event = None

    def _redraw(self, *args):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w <= 0 or h <= 0:
            return
        r = 16
        p = self._pulse
        pressed = self.state == 'down'
        bright = 0.7 + 0.3 * p if not pressed else 0.4
        with self.canvas.before:
            Color(0.0, 0.0, 0.06, 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[(r, r), (r, r), (r, r), (r, r)])
            Color(0.0, 0.5, 1.0, 0.06 * bright)
            RoundedRectangle(pos=(x-7, y-7), size=(w+14, h+14), radius=[(r+7, r+7), (r+7, r+7), (r+7, r+7), (r+7, r+7)])
            Color(0.0, 0.6, 1.0, 0.10 * bright)
            RoundedRectangle(pos=(x-5, y-5), size=(w+10, h+10), radius=[(r+5, r+5), (r+5, r+5), (r+5, r+5), (r+5, r+5)])
            Color(0.0, 0.7, 1.0, 0.16 * bright)
            RoundedRectangle(pos=(x-3, y-3), size=(w+6, h+6), radius=[(r+3, r+3), (r+3, r+3), (r+3, r+3), (r+3, r+3)])
            Color(0.0, 0.0, 0.06, 1)
            RoundedRectangle(pos=(x+2, y+2), size=(w-4, h-4), radius=[(r-1, r-1), (r-1, r-1), (r-1, r-1), (r-1, r-1)])
            Color(0.0, 0.75, 1.0, 0.55 * bright)
            RoundedRectangle(pos=(x+2, y+2), size=(w-4, h-4), radius=[(r-1, r-1), (r-1, r-1), (r-1, r-1), (r-1, r-1)])
            Color(0.0, 0.0, 0.06, 1)
            RoundedRectangle(pos=(x+5, y+5), size=(w-10, h-10), radius=[(r-4, r-4), (r-4, r-4), (r-4, r-4), (r-4, r-4)])
            Color(0.4, 0.9, 1.0, 0.18 * bright)
            RoundedRectangle(pos=(x+5, y+5), size=(w-10, h-10), radius=[(r-4, r-4), (r-4, r-4), (r-4, r-4), (r-4, r-4)])
            Color(0.0, 0.0, 0.06, 1)
            RoundedRectangle(pos=(x+8, y+8), size=(w-16, h-16), radius=[(r-6, r-6), (r-6, r-6), (r-6, r-6), (r-6, r-6)])

class BadgeLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.markup, self.bold, self.font_size, self.color = True, True, '13sp', (1, 1, 1, 1)
        self.size_hint, self.size, self.pos_hint = (None, None), (80, 32), {'center_y': 0.5}
        self.halign, self.valign = 'center', 'middle'
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.2, 0.4, 0.6, 0.8)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[(8, 8), (8, 8), (8, 8), (8, 8)])

class AppPopup(Popup):
    def on_open(self):
        app = App.get_running_app()
        if app:
            app.active_popups = getattr(app, 'active_popups', 0) + 1
        super().on_open()

    def on_dismiss(self):
        self.is_dismissing_flag = True
        app = App.get_running_app()
        if app:
            app.active_popups = max(0, getattr(app, 'active_popups', 0) - 1)
            app.last_popup_close = time.time()
        super().on_dismiss()

class TopMenuPopup(AppPopup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title_align, self.title_size, self.separator_height = 'center', '20sp', 0
        self.background_color, self.pos_hint = (0.12, 0.12, 0.12, 0.95), {'top': 1.0}


# ═══════════════════════════════════════════════════════════════════
#  СТАРТОВЫЙ ЭКРАН: капсульные кнопки + неоновые карточки-показатели
#  (новый дизайн; логика данных и расчётов не менялась)
# ═══════════════════════════════════════════════════════════════════
class CapsuleButton(ButtonBehavior, Label):
    """Кнопка-капсула (полностью скруглённые торцы) с тёмно-синей заливкой."""
    def __init__(self, text='', **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.markup = True
        self.bold = True
        self.color = (0.8, 0.85, 0.9, 1)
        self.font_size = '24sp'
        self.halign = 'center'
        self.valign = 'middle'
        self.border_col = (0.165, 0.29, 0.498, 1)    # #2A4A7F
        self.fill_normal = (0.094, 0.145, 0.259, 1)  # #182542
        self.fill_press = (0.063, 0.094, 0.169, 1)   # #10182B
        self.bind(pos=self._draw, size=self._draw, state=self._draw)
        self.bind(size=lambda s, v: setattr(s, 'text_size', v))

    def _draw(self, *a):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 4 or h < 4:
            return
        r = h / 2.0
        with self.canvas.before:
            Color(*self.border_col)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[(r, r)] * 4)
            f = self.fill_press if self.state == 'down' else self.fill_normal
            Color(*f)
            RoundedRectangle(pos=(x + 3, y + 3), size=(w - 6, h - 6), radius=[(r - 3, r - 3)] * 4)


class MenuIcon(Widget):
    """Вектор-иконка карточки (карта+монета / два человечка / график+стрелка)."""
    def __init__(self, kind='debt', color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.kind = kind
        self.icon_color = list(color)
        self.size_hint_x = None
        self.width = 128
        self.bind(pos=self._draw, size=self._draw)

    def set_color(self, color):
        self.icon_color = list(color)
        self._draw()

    def _draw(self, *a):
        self.canvas.after.clear()
        if self.width < 4 or self.height < 4:
            return
        k = 2.85          # масштаб относительно исходной раскладки в dp
        x = self.x + 8
        cy = self.center_y
        col = self.icon_color
        c = (col[0], col[1], col[2], col[3] if len(col) > 3 else 1)
        lw = 3.4
        with self.canvas.after:
            Color(*c)
            if self.kind == 'debt':
                # тело карты
                Line(rounded_rectangle=(x, cy - 12*k, 28*k, 18*k, 3*k), width=lw)
                # полоса
                Line(points=[x, cy - 4*k, x + 28*k, cy - 4*k], width=lw)
                # монета
                Line(circle=(x + 26*k, cy + 8*k, 6*k), width=lw)
            elif self.kind == 'users':
                # человек 1 (передний, слева)
                Line(circle=(x + 10*k, cy + 6*k, 5*k), width=lw)
                Line(points=[x + 2*k, cy - 12*k, x + 2*k, cy - 2*k, x + 18*k, cy - 2*k, x + 18*k, cy - 12*k], width=lw)
                # человек 2 (сзади, справа)
                Line(circle=(x + 26*k, cy + 2*k, 4*k), width=lw)
                Line(points=[x + 18*k, cy - 12*k, x + 18*k, cy - 4*k, x + 34*k, cy - 4*k, x + 34*k, cy - 12*k], width=lw)
            elif self.kind == 'profit':
                # три столбика
                Line(rounded_rectangle=(x, cy - 12*k, 6*k, 10*k, 1.5*k), width=lw)
                Line(rounded_rectangle=(x + 10*k, cy - 12*k, 6*k, 16*k, 1.5*k), width=lw)
                Line(rounded_rectangle=(x + 20*k, cy - 12*k, 6*k, 24*k, 1.5*k), width=lw)
                # стрелка вверх
                Line(points=[x - 2*k, cy, x + 10*k, cy + 8*k, x + 25*k, cy + 18*k], width=lw)
                Line(points=[x + 17*k, cy + 18*k, x + 25*k, cy + 18*k, x + 25*k, cy + 10*k], width=lw)


class StatCard(ButtonBehavior, BoxLayout):
    """Карточка-показатель с неоновой цветной рамкой и тёмной заливкой."""
    def __init__(self, kind='debt', title='', accent=(1, 1, 1, 1), on_tap=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self._on_tap = on_tap
        if on_tap:
            self.bind(on_release=lambda *a: self._on_tap())
        self.accent = list(accent)
        self.size_hint_y = None
        self.height = 255
        self.padding = [28, 16, 24, 16]
        self.spacing = 16
        self.icon = MenuIcon(kind=kind, color=(accent[0], accent[1], accent[2], 1))
        txt = BoxLayout(orientation='vertical', spacing=14)
        txt.add_widget(Widget())  # верхняя распорка-центровщик
        self.title_lbl = Label(text=title, font_size='19sp', bold=True,
                               color=(0.6, 0.65, 0.7, 1), halign='left', valign='middle',
                               size_hint_y=None)
        self.title_lbl.bind(width=lambda s, v: setattr(s, 'text_size', (v, None)),
                            texture_size=lambda s, v: setattr(s, 'height', v[1]))
        self.value_lbl = Label(text='', markup=True, font_size='31sp', bold=True,
                               color=(accent[0], accent[1], accent[2], 1),
                               halign='left', valign='middle', size_hint_y=None)
        self.value_lbl.bind(width=lambda s, v: setattr(s, 'text_size', (v, None)),
                            texture_size=lambda s, v: setattr(s, 'height', v[1]))
        txt.add_widget(self.title_lbl)
        txt.add_widget(self.value_lbl)
        txt.add_widget(Widget())  # нижняя распорка-центровщик
        self.add_widget(self.icon)
        self.add_widget(txt)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 4 or h < 4:
            return
        a = self.accent
        r = 60
        with self.canvas.before:
            Color(a[0], a[1], a[2], 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[(r, r)] * 4)
            Color(0.07, 0.086, 0.133, 1)   # #121622
            RoundedRectangle(pos=(x + 6, y + 6), size=(w - 12, h - 12), radius=[(r - 6, r - 6)] * 4)
            if self._on_tap:
                Color(a[0], a[1], a[2], 0.9)
                pcx, pcy, d = x + w - 82, y + 74, 22
                Line(circle=(pcx, pcy, 60), width=2.6)
                Line(points=[pcx - d - 6, pcy - d + 6, pcx + d - 6, pcy + d + 6], width=3.4)
                Line(points=[pcx - d + 6, pcy - d - 6, pcx + d + 6, pcy + d + 6], width=3.4)
                Line(points=[pcx - d - 6, pcy - d + 6, pcx - d + 6, pcy - d - 6], width=3.4)
                Line(points=[pcx - d - 8, pcy - d - 8, pcx - d - 6, pcy - d + 6], width=3.4)
                Line(points=[pcx - d - 8, pcy - d - 8, pcx - d + 6, pcy - d - 6], width=3.4)
                tip_x, tip_y = pcx + d + 12, pcy + d + 12
                Line(points=[pcx + d - 6, pcy + d + 6, tip_x, tip_y], width=3.4)
                Line(points=[pcx + d + 6, pcy + d - 6, tip_x, tip_y], width=3.4)
                Line(points=[pcx + d, pcy + d, tip_x, tip_y], width=3.6)

    def set_value(self, text, color=None):
        self.value_lbl.text = text
        if color is not None:
            self.value_lbl.color = color

    def set_accent(self, accent):
        self.accent = list(accent)
        try:
            self.icon.set_color((self.accent[0], self.accent[1], self.accent[2], 1))
        except Exception:
            pass
        self._draw()


class QuickDebtRow(ButtonBehavior, BoxLayout):
    """Крупная неоновая карточка-строка для быстрого списка долгов."""
    def __init__(self, name='', amount_text='', accent=(1, 1, 1, 1), amt_color=None, **kw):
        super().__init__(**kw)
        self.orientation = 'horizontal'
        self.accent = list(accent)
        self.size_hint_y = None
        self.height = 158
        self.padding = [30, 14, 76, 14]
        self.spacing = 8
        self.lbl_name = Label(text=f"[b]{name}[/b]", markup=True, font_size='25sp',
                              color=(1, 1, 1, 1), halign='left', valign='middle', size_hint_x=0.46)
        self.lbl_name.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.lbl_name.bind(width=lambda *a: self._fit(self.lbl_name, 25, 12),
                           text=lambda *a: self._fit(self.lbl_name, 25, 12))
        ac = amt_color if amt_color else accent
        self.lbl_amt = Label(text=f"[b]{amount_text}[/b]", markup=True, font_size='27sp',
                             color=(ac[0], ac[1], ac[2], 1), halign='right', valign='middle', size_hint_x=0.54)
        self.lbl_amt.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self.lbl_amt.bind(width=lambda *a: self._fit(self.lbl_amt, 27, 12),
                          text=lambda *a: self._fit(self.lbl_amt, 27, 12))
        self.add_widget(self.lbl_name)
        self.add_widget(self.lbl_amt)
        self.bind(pos=self._draw, size=self._draw)

    def _fit(self, lbl, maxsp, minsp):
        from kivy.core.text import Label as CoreLabel
        from kivy.metrics import sp
        avail = lbl.width - 6
        if avail < 10:
            return
        for size in range(maxsp, minsp - 1, -1):
            cl = CoreLabel(text=lbl.text, font_size=sp(size), markup=True)
            try:
                cl.refresh()
                w = cl.texture.size[0]
            except Exception:
                w = 0
            if w <= avail:
                lbl.font_size = '%dsp' % size
                return
        lbl.font_size = '%dsp' % minsp

    def _draw(self, *a):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 4 or h < 4:
            return
        a = self.accent
        r = 26
        with self.canvas.before:
            Color(a[0], a[1], a[2], 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[(r, r)] * 4)
            Color(0.07, 0.086, 0.133, 1)
            RoundedRectangle(pos=(x + 3, y + 3), size=(w - 6, h - 6), radius=[(r - 3, r - 3)] * 4)
            pcx, pcy, d = x + w - 46, y + h / 2.0, 12
            Color(a[0], a[1], a[2], 0.85)
            Line(circle=(pcx, pcy, 30), width=1.8)
            Line(points=[pcx - d - 3, pcy - d + 3, pcx + d - 3, pcy + d + 3], width=2.0)
            Line(points=[pcx - d + 3, pcy - d - 3, pcx + d + 3, pcy + d + 3], width=2.0)
            Line(points=[pcx - d - 3, pcy - d + 3, pcx - d + 3, pcy - d - 3], width=2.0)
            Line(points=[pcx - d - 4, pcy - d - 4, pcx - d - 3, pcy - d + 3], width=2.0)
            Line(points=[pcx - d - 4, pcy - d - 4, pcx - d + 3, pcy - d - 3], width=2.0)
            _tx, _ty = pcx + d + 6, pcy + d + 6
            Line(points=[pcx + d - 3, pcy + d + 3, _tx, _ty], width=2.0)
            Line(points=[pcx + d + 3, pcy + d - 3, _tx, _ty], width=2.0)
            Line(points=[pcx + d, pcy + d, _tx, _ty], width=2.2)


class PhotoAvatar(Widget):
    """Круглое фото пользователя (avatar.png рядом с main.py). Если файла нет — силуэт."""
    def __init__(self, filename='avatar.png', ring=(0.2, 0.75, 0.84, 1), **kw):
        super().__init__(**kw)
        self.ring = list(ring)
        self.texture = None
        from kivy.core.image import Image as CoreImage
        # 1) необязательная замена: если рядом лежит свой файл фото — берём его
        try:
            candidates = ['avatar.png', 'avatar.jpg', 'avatar.jpeg',
                          'foto.png', 'foto.jpg', 'photo.png', 'photo.jpg', 'me.jpg', 'me.png']
            for name in candidates:
                p = os.path.join(BASE_PATH, name)
                if os.path.exists(p):
                    self.texture = CoreImage(p).texture
                    break
        except Exception:
            self.texture = None
        # 2) иначе — фото, вшитое в код (base64)
        if self.texture is None:
            try:
                import base64 as _b64
                import io as _io
                data = _b64.b64decode(_AVATAR_B64)
                self.texture = CoreImage(_io.BytesIO(data), ext='jpg').texture
            except Exception:
                self.texture = None
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *a):
        self.canvas.before.clear()
        w, h = self.width, self.height
        if w < 4 or h < 4:
            return
        d = min(w, h)
        x = self.x + (w - d) / 2.0
        y = self.y + (h - d) / 2.0
        cx, cy = x + d / 2.0, y + d / 2.0
        with self.canvas.before:
            if self.texture is not None:
                Color(1, 1, 1, 1)
                # круглая обрезка: рисуем текстуру внутри эллипса
                Ellipse(pos=(x, y), size=(d, d), texture=self.texture)
            else:
                Color(0.14, 0.16, 0.20, 1)
                Ellipse(pos=(x, y), size=(d, d))
                Color(0.4, 0.45, 0.52, 1)
                hd = d * 0.30
                Ellipse(pos=(cx - hd / 2.0, y + d * 0.46), size=(hd, hd))
                Ellipse(pos=(cx - d * 0.27, y + d * 0.10), size=(d * 0.54, d * 0.42))
            for i, a_ in enumerate((0.10, 0.18, 0.9)):
                Color(self.ring[0], self.ring[1], self.ring[2], a_)
                Line(circle=(cx, cy, d / 2.0 - 1 - i), width=2.6 if i == 2 else 5.0)


class MainMenu(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        # Фон — на всю ширину экрана (на отдельном слое FloatLayout, а не на self.canvas,
        # т.к. у Screen в canvas.before лежит PushMatrix — его нельзя стирать).
        self.bg_layer = FloatLayout()
        self.bg_layer.bind(pos=self._draw_bg, size=self._draw_bg)

        # Колонка контента — 80% ширины, по центру.
        col = BoxLayout(orientation='vertical', size_hint=(0.8, 1),
                        pos_hint={'center_x': 0.5, 'center_y': 0.5},
                        padding=[0, 24, 0, 24], spacing=34)

        btn_uchet = CapsuleButton(text="ОТКРЫТЬ УЧЁТ", size_hint=(1, None), height=192)
        btn_uchet.bind(on_release=lambda x: setattr(self.manager, 'current', 'clients_screen'))

        self.card_debt = StatCard(kind='debt', title="МОЙ ДОЛГ", accent=(1.0, 0.322, 0.322, 1),
                                  on_tap=lambda: self._open_quick_list('creditors'))       # #FF5252
        self.card_clients = StatCard(kind='users', title="КЛИЕНТЫ ДОЛЖНЫ", accent=(0.412, 0.941, 0.682, 1),
                                     on_tap=lambda: self._open_quick_list('clients'))  # #69F0AE
        self.card_profit = StatCard(kind='profit', title="ЧИСТАЯ ПРИБЫЛЬ", accent=(1.0, 0.843, 0.251, 1))   # #FFD740

        exit_btn = CapsuleButton(text="ВЫЙТИ", size_hint=(1, None), height=176)
        exit_btn.bind(on_release=lambda x: App.get_running_app().stop())

        col.add_widget(Widget(size_hint_y=1))
        col.add_widget(PhotoAvatar(size_hint=(1, None), height=340))
        col.add_widget(Widget(size_hint_y=None, height=4))
        col.add_widget(btn_uchet)
        col.add_widget(self.card_debt)
        col.add_widget(self.card_clients)
        col.add_widget(self.card_profit)
        col.add_widget(exit_btn)
        col.add_widget(Widget(size_hint_y=1))

        self.bg_layer.add_widget(col)
        self.add_widget(self.bg_layer)

    def _draw_bg(self, *a):
        self.bg_layer.canvas.before.clear()
        with self.bg_layer.canvas.before:
            Color(0.059, 0.071, 0.102, 1)   # #0F121A
            Rectangle(pos=self.bg_layer.pos, size=self.bg_layer.size)

    def on_enter(self):
        self.update_cards()

    def update_cards(self):
        app = App.get_running_app()
        if not app:
            return
        tot_debt, my_debt, _, profit = app.get_totals()
        _red = (1.0, 0.322, 0.322, 1)
        _green = (0.412, 0.941, 0.682, 1)
        _gray = (0.6, 0.65, 0.7, 1)
        if my_debt > 0.5:
            self.card_debt.title_lbl.text = "МОЙ ДОЛГ"
            self.card_debt.set_accent(_red)
            self.card_debt.set_value(f"{format_num_simple(my_debt)} \u20bd", color=_red)
        elif my_debt < -0.5:
            self.card_debt.title_lbl.text = "ПЕРЕПЛАТА"
            self.card_debt.set_accent(_green)
            self.card_debt.set_value(f"{format_num_simple(abs(my_debt))} \u20bd", color=_green)
        else:
            self.card_debt.title_lbl.text = "МОЙ ДОЛГ"
            self.card_debt.set_accent(_red)
            self.card_debt.set_value("0 \u20bd", color=_gray)
        self.card_clients.set_value(f"{format_num_simple(tot_debt)} \u20bd")
        if profit >= 0:
            self.card_profit.set_value(f"{format_num_simple(profit)} \u20bd", color=(1.0, 0.843, 0.251, 1))
        else:
            self.card_profit.set_value(f"-{format_num_simple(abs(profit))} \u20bd", color=(1.0, 0.322, 0.322, 1))

    # ── БЫСТРЫЙ ДОСТУП К ДОЛГАМ ПРЯМО СО СТАРТОВОЙ ──
    def _refresh_all(self):
        self.update_cards()
        try:
            if self.manager and self.manager.has_screen('clients_screen'):
                self.manager.get_screen('clients_screen').refresh_list()
        except Exception:
            pass

    def _open_quick_list(self, kind):
        app = App.get_running_app()
        if not app:
            return
        m_indices, o_idx, b_idx, c_idx = app.get_special_clients()
        special = set(i for i in (o_idx, b_idx, c_idx) if i is not None)
        if kind == 'creditors':
            title = "МОЙ ДОЛГ — КОМУ Я ДОЛЖЕН"
            accent = (1.0, 0.322, 0.322, 1)
            all_idx = list(m_indices)
        else:
            title = "КЛИЕНТЫ — КТО МНЕ ДОЛЖЕН"
            accent = (0.412, 0.941, 0.682, 1)
            all_idx = [i for i in range(len(app.clients)) if i not in special and i not in m_indices]

        state = {'show_all': False}
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=18, size_hint_y=None, padding=[6, 10, 6, 10])
        grid.bind(minimum_height=grid.setter('height'))
        scroll.add_widget(grid)
        pop = TopMenuPopup(title=title, content=BoxLayout(orientation='vertical', spacing=10, padding=[10, 10, 10, 10]),
                           size_hint=(0.95, 0.9))
        pop.title_size = '18sp'
        pop.background_color = (0.043, 0.055, 0.08, 1)

        def rebuild():
            grid.clear_widgets()
            if state['show_all']:
                shown = all_idx
            else:
                shown = [i for i in all_idx if abs(safe_float(app.clients[i].get('debt', 0))) > 0.001]
            if not shown:
                lbl = Label(text="[color=#5A6472]Нет активных долгов[/color]", markup=True,
                            font_size='17sp', size_hint_y=None, height=120, halign='center', valign='middle')
                lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
                grid.add_widget(lbl)
            for i in shown:
                c = app.clients[i]
                name = c.get('name', '').upper()
                val = safe_float(c.get('debt', 0))
                # переплата (< 0) — зелёным и без минуса, как на карточке;
                # реальный долг (>= 0) — акцентным цветом списка
                if val < -0.001:
                    amt_color = (0.412, 0.941, 0.682)
                    amount_text = f"{format_num_simple(abs(val))} \u20bd"
                else:
                    amt_color = accent
                    amount_text = f"{format_num_simple(c.get('debt', 0))} \u20bd"
                row = QuickDebtRow(name=name, amount_text=amount_text,
                                   accent=accent, amt_color=amt_color)
                row.bind(on_release=lambda x, idx=i: self._quick_edit_one(idx, pop))
                grid.add_widget(row)

        rebuild()

        btn_toggle = RoundedButton(text="ПОКАЗАТЬ ВСЕХ", bg_color=(0.25, 0.3, 0.42, 1),
                                   font_size='19sp', bold=True, radius=28)

        def _toggle(x):
            state['show_all'] = not state['show_all']
            btn_toggle.text = "ТОЛЬКО С ДОЛГОМ" if state['show_all'] else "ПОКАЗАТЬ ВСЕХ"
            rebuild()
        btn_toggle.bind(on_release=_toggle)

        btn_close = CancelButton(text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1),
                                 font_size='21sp', bold=True)
        btn_close.bind(on_release=lambda x: pop.dismiss())
        btn_back = RoundedButton(text="НАЗАД", bg_color=(1, 0.45, 0, 1),
                                 font_size='21sp', bold=True, radius=28)
        btn_back.bind(on_release=lambda x: pop.dismiss())

        pop.content.add_widget(scroll)
        btn_toggle.size_hint_y = None
        btn_toggle.height = 100
        pop.content.add_widget(btn_toggle)
        nav_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=122, spacing=14)
        nav_row.add_widget(btn_back)
        nav_row.add_widget(btn_close)
        pop.content.add_widget(nav_row)
        pop._rebuild_list = rebuild   # чтобы обновить после правки
        pop.open()

    def _quick_edit_one(self, idx, list_pop):
        app = App.get_running_app()
        if not app:
            return
        c = app.clients[idx]
        content = BoxLayout(orientation='vertical', spacing=30, padding=[18, 16, 18, 16])
        pop = TopMenuPopup(title=c.get('name', '').upper(), content=content, size_hint=(0.94, 0.82))
        pop.background_color = (0.043, 0.055, 0.08, 1)

        # ── ТЕКУЩИЙ ДОЛГ — крупно, вверху ──
        head = BoxLayout(orientation='vertical', size_hint_y=None, height=228, padding=[16, 16, 16, 18], spacing=6)
        def _draw_head(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.2, 0.75, 0.84, 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(24, 24)] * 4)
                Color(0.08, 0.10, 0.15, 1)
                RoundedRectangle(pos=(w.x + 3, w.y + 3), size=(w.width - 6, w.height - 6), radius=[(21, 21)] * 4)
        head.bind(pos=_draw_head, size=_draw_head)
        cap_head = Label(text="[b]ТЕКУЩИЙ ДОЛГ[/b]", markup=True, font_size='15sp',
                         color=(0.5, 0.78, 0.85, 1), halign='center', valign='middle', size_hint_y=0.36)
        cap_head.bind(size=lambda s, v: setattr(s, 'text_size', v))
        val_head = Label(text=f"[b][color=#FFD54F]{format_num_simple(c.get('debt', '0'))} \u20bd[/color][/b]",
                         markup=True, font_size='29sp', halign='center', valign='middle', size_hint_y=0.64)
        val_head.bind(size=lambda s, v: setattr(s, 'text_size', v))
        head.add_widget(cap_head)
        head.add_widget(val_head)
        content.add_widget(head)

        content.add_widget(Label(text="[b]СКОЛЬКО ОТДАЛ (ОТНЯТЬ)[/b]", markup=True, font_size='17sp',
                                 color=(0.4, 0.8, 1, 1), halign='center', valign='middle',
                                 size_hint_y=None, height=38))
        in_minus = _dark_input(hint_text="Сумма оплаты...", input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_minus, (0.4, 0.8, 1, 1), 170, 0.6))
        content.add_widget(Label(text="ИЛИ ИЗМЕНИТЬ ДОЛГ ВРУЧНУЮ", font_size='14sp',
                                 color=(0.55, 0.6, 0.66, 1), halign='center', valign='middle',
                                 size_hint_y=None, height=32))
        in_d = _dark_input(text=format_num_simple(c.get('debt', '0')), input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_d, (0.45, 0.5, 0.6, 1), 156, 0.6))
        btn_save = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.2, 0.62, 0.42, 1),
                                 bold=True, radius=24, font_size='21sp')

        def do_save(x):
            if getattr(pop, 'is_dismissing_flag', False):
                return
            pop.is_dismissing_flag = True
            old_val = safe_float(c.get('debt', '0'))
            minus_val = safe_float(in_minus.text)
            if minus_val > 0:
                # «отдал» гасит долг В СТОРОНУ НУЛЯ (не пересекая ноль):
                # положительный уменьшается, отрицательный (переплата) подтягивается к нулю
                if old_val >= 0:
                    d_val = old_val - minus_val
                else:
                    d_val = min(0.0, old_val + minus_val)
            else:
                d_val = safe_float(in_d.text)
            c['debt'] = format_num_simple(d_val)
            if d_val == 0.0:
                c['zakupka_total'] = '0'
            if (not c.get('is_creditor')
                    and c.get('name', '').lower().strip() not in
                    ("баннер остаток", "белый банер", "черный банер", "олег белый", "олег черный")):
                # в прибыль идёт только реально погашенная ПОЛОЖИТЕЛЬНАЯ часть долга
                realized = max(0.0, old_val) - max(0.0, d_val)
                if realized > 0:
                    app.profit_correction = str(round(safe_float(app.profit_correction) + realized, 2))
            app.save_data()
            self._refresh_all()
            pop.dismiss()
            try:
                if list_pop and getattr(list_pop, '_rebuild_list', None):
                    list_pop._rebuild_list()
            except Exception:
                pass

        btn_save.bind(on_release=do_save)
        btn_save.size_hint_y = None
        btn_save.height = 110
        content.add_widget(btn_save)
        btn_back = RoundedButton(text="НАЗАД", bg_color=(1, 0.45, 0, 1),
                                 bold=True, radius=24, font_size='21sp')
        btn_back.bind(on_release=lambda x: pop.dismiss())   # назад к списку
        btn_close = CancelButton(text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1),
                                 bold=True, font_size='21sp')
        def _close_all(x):
            pop.dismiss()
            try:
                if list_pop:
                    list_pop.dismiss()
            except Exception:
                pass
        btn_close.bind(on_release=_close_all)   # выйти полностью
        nav_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=110, spacing=14)
        nav_row.add_widget(btn_back)
        nav_row.add_widget(btn_close)
        content.add_widget(nav_row)
        content.add_widget(Widget(size_hint_y=1))   # прижать содержимое вверх
        pop.open()


# ═══════════════════════════════════════════════════════════════════
#  НОВЫЕ ВИДЖЕТЫ ДЛЯ ДИЗАЙНА ЦЕНТРАЛЬНОЙ СТРАНИЦЫ
# ═══════════════════════════════════════════════════════════════════
class ClickBox(ButtonBehavior, BoxLayout):
    """Прозрачный кликабельный контейнер (аватар + текст)."""
    pass


class Avatar(Widget):
    """Круглый аватар с силуэтом человека (рисуется через canvas)."""
    def __init__(self, tint=(0.23, 0.23, 0.23, 1), fg=(0.72, 0.72, 0.72, 1), **kwargs):
        super().__init__(**kwargs)
        self.tint = list(tint)
        self.fg = list(fg)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *a):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 2 or h < 2:
            return
        d = min(w, h) * 0.92
        cx = x + w / 2.0
        cy = y + h / 2.0
        with self.canvas.before:
            Color(*self.tint)
            Ellipse(pos=(cx - d / 2.0, cy - d / 2.0), size=(d, d))
            Color(*self.fg)
            hd = d * 0.30
            Ellipse(pos=(cx - hd / 2.0, cy + d * 0.03), size=(hd, hd))
            sw = d * 0.54
            sh = d * 0.40
            Ellipse(pos=(cx - sw / 2.0, cy - d * 0.34), size=(sw, sh))


class IstClockButton(RoundedButton):
    """Сплошная синяя кнопка 'Ист' (история)."""
    def __init__(self, **kwargs):
        kwargs.setdefault('bg_color', (0.26, 0.45, 0.85, 1))
        super().__init__(text="Ист", **kwargs)
        self.markup = False
        self.bold = True
        self.font_size = '14sp'
        self.halign = 'center'
        self.valign = 'middle'
        self.bind(size=lambda s, v: setattr(s, 'text_size', (s.width - 6, s.height)))


class NeonIconButton(ButtonBehavior, Widget):
    """Неоновая кнопка с нарисованной иконкой и подписью (верхняя панель)."""
    def __init__(self, icon=None, label='', glow=(0.1, 0.78, 0.83), layout='top', **kwargs):
        super().__init__(**kwargs)
        self.icon = icon
        self.glow = list(glow)[:3]
        self.layout_mode = layout
        self._lbl = None
        if layout == 'top':
            self._lbl = Label(text=label, font_size='11sp', bold=True,
                              halign='center', valign='top', color=(1, 1, 1, 1))
            self.add_widget(self._lbl)
        elif layout == 'text':
            self._lbl = Label(text=label, font_size='15sp', bold=True,
                              halign='center', valign='middle', color=(1, 1, 1, 1))
            self.add_widget(self._lbl)
        self.bind(pos=self._sync, size=self._sync, state=self._sync)

    def _sync(self, *a):
        if self._lbl is not None:
            if self.layout_mode == 'top':
                self._lbl.pos = (self.x + 2, self.y + 8)
                self._lbl.size = (self.width - 4, self.height * 0.48)
                self._lbl.text_size = (self.width - 4, self.height * 0.48)
            else:
                self._lbl.pos = (self.x, self.y)
                self._lbl.size = (self.width, self.height)
                self._lbl.text_size = (self.width - 6, self.height)
        self._redraw()

    def _redraw(self, *a):
        self.canvas.before.clear()
        x, y, w, h = self.x, self.y, self.width, self.height
        if w < 4 or h < 4:
            return
        r = 26
        g = self.glow
        pressed = self.state == 'down'
        dim = 0.55 if pressed else 1.0
        with self.canvas.before:
            Color(0.05, 0.05, 0.07, 1)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[(r, r)] * 4)
            for exp, a_ in ((13, 0.04), (10, 0.06), (7, 0.10), (4, 0.15), (2, 0.22)):
                Color(g[0], g[1], g[2], a_ * dim)
                RoundedRectangle(pos=(x - exp, y - exp), size=(w + 2 * exp, h + 2 * exp), radius=[(r + exp, r + exp)] * 4)
            Color(g[0] * 0.14, g[1] * 0.14, g[2] * 0.14, 1)
            RoundedRectangle(pos=(x + 3, y + 3), size=(w - 6, h - 6), radius=[(r - 2, r - 2)] * 4)
            Color(g[0], g[1], g[2], 0.95 * dim)
            Line(rounded_rectangle=(x + 2, y + 2, w - 4, h - 4, r - 2), width=2.6)
        self._draw_icon(g, dim)

    def _draw_icon(self, g, dim):
        self.canvas.after.clear()
        if self.icon is None:
            return
        cx = self.center_x
        if self.layout_mode == 'top':
            iyc = self.y + self.height * 0.73
            s = min(self.width, self.height) * 0.155
        else:
            iyc = self.center_y
            s = min(self.width, self.height) * 0.30
        ic = [min(c * 1.5, 1.0) for c in g]
        with self.canvas.after:
            Color(ic[0], ic[1], ic[2], dim)
            if self.icon == 'plus':
                Line(points=[cx - s, iyc, cx + s, iyc], width=2.4)
                Line(points=[cx, iyc - s, cx, iyc + s], width=2.4)
            elif self.icon == 'chart':
                bw = s * 0.5
                base = iyc - s
                data = [(cx - s, s * 1.0), (cx - bw * 0.5, s * 1.7), (cx + bw * 0.7, s * 1.25)]
                for bx, bh in data:
                    Rectangle(pos=(bx, base), size=(bw, bh))
            elif self.icon == 'cart':
                Line(points=[cx - s, iyc + s * 0.5, cx - s * 0.7, iyc - s * 0.45,
                             cx + s * 0.95, iyc - s * 0.45, cx + s * 0.6, iyc + s * 0.5,
                             cx - s, iyc + s * 0.5], width=1.7)
                Line(points=[cx - s, iyc + s * 0.5, cx - s * 1.45, iyc + s * 1.0], width=1.7)
                Line(circle=(cx - s * 0.45, iyc - s * 0.75, s * 0.2), width=1.5)
                Line(circle=(cx + s * 0.5, iyc - s * 0.75, s * 0.2), width=1.5)
            elif self.icon == 'clock':
                Line(circle=(cx, iyc, s * 0.95), width=1.8)
                Line(points=[cx, iyc, cx, iyc + s * 0.55], width=1.8)
                Line(points=[cx, iyc, cx + s * 0.42, iyc], width=1.8)
            elif self.icon == 'pencil':
                bx0, by0 = cx - s * 0.7, iyc - s * 0.7
                Line(points=[bx0, by0, cx + s * 0.7, iyc + s * 0.7], width=2.6)
                Line(points=[bx0, by0, bx0 + s * 0.55, by0 - s * 0.12], width=2.2)
                Line(points=[bx0, by0, bx0 - s * 0.12, by0 + s * 0.55], width=2.2)
            elif self.icon == 'grid':
                half = s
                Line(rectangle=(cx - half, iyc - half, 2 * half, 2 * half), width=2.2)
                step = 2 * half / 4.0
                for k in (1, 2, 3):
                    Line(points=[cx - half + step * k, iyc - half, cx - half + step * k, iyc + half], width=1.6)
                    Line(points=[cx - half, iyc - half + step * k, cx + half, iyc - half + step * k], width=1.6)
            elif self.icon == 'refresh':
                Line(circle=(cx, iyc, s, 45, 340), width=2.6)
                a = math.radians(45)
                ex = cx + s * math.sin(a)
                ey = iyc + s * math.cos(a)
                Line(points=[ex, ey, ex - s * 0.45, ey + s * 0.02], width=2.6)
                Line(points=[ex, ey, ex + s * 0.02, ey + s * 0.45], width=2.6)


class ClientsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.layout = BoxLayout(orientation='vertical', padding=[10, 10, 10, 10], spacing=8)

        # ── ВЕРХНЯЯ ПАНЕЛЬ: 4 НЕОНОВЫЕ КНОПКИ ──
        top_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=192, spacing=8, padding=[40, 0, 40, 0])
        b_add = NeonIconButton(icon='plus', label='ДОБАВИТЬ\nКЛИЕНТА', glow=(0.1, 0.78, 0.83))
        b_add.bind(on_release=self.show_add_popup)
        b_rep = NeonIconButton(icon='grid', label='ОТЧЕТЫ', glow=(0.91, 0.64, 0.1))
        b_rep.bind(on_release=self.show_reports_stub)
        b_zak = NeonIconButton(icon='cart', label='ЗАКУПКА\nБАНЕРОВ', glow=(0.69, 0.3, 0.88))
        b_zak.bind(on_release=self.show_zakupka_menu)
        top_box.add_widget(b_add)
        top_box.add_widget(b_rep)
        top_box.add_widget(b_zak)

        self.scroll = ScrollView()
        self.list_layout = GridLayout(cols=1, spacing=15, size_hint_y=None, padding=[26, 0, 26, 0])
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        self.scroll.add_widget(self.list_layout)

        def go_main_menu(instance=None):
            app = App.get_running_app()
            if not app:
                return
            if getattr(app, 'active_popups', 0) > 0:
                return
            if time.time() - getattr(app, 'last_popup_close', 0) < 0.5:
                return
            setattr(self.manager, 'current', 'main_menu')

        self.back_btn = RoundedButton(
            text="НАЗАД", bg_color=(1, 0.45, 0, 1),
            font_size='22sp', bold=True,
            size_hint=(0.35, None),
            height=117,
            radius=45,
            pos_hint={'center_x': 0.5}
        )
        self.back_btn.bind(on_release=lambda x: go_main_menu())

        self.layout.add_widget(top_box)
        self.layout.add_widget(self.scroll)
        self.add_widget(self.layout)

    def on_enter(self):
        self.refresh_list()

    def safe_transition(self, current_pop, next_func, *args, **kwargs):
        if getattr(current_pop, 'is_dismissing_flag', False): return
        current_pop.is_dismissing_flag = True
        current_pop.dismiss()
        Clock.schedule_once(lambda dt: next_func(*args, **kwargs), 0.15)

    def get_bottom_buttons(self, pop, prev_cb=None, cancel_text="ЗАКРЫТЬ"):
        box = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=100, padding=[25, 0, 25, 0])

        def _back_cb():
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            pop.dismiss()
            if prev_cb: Clock.schedule_once(lambda dt: prev_cb(), 0.15)

        def do_cancel(instance=None):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            pop.dismiss()

        btn_back = RoundedButton(
            text="НАЗАД", bg_color=(1, 0.45, 0, 1),
            font_size='20sp', bold=True, size_hint_x=0.45
        )
        btn_back.bind(on_release=lambda x: _back_cb())
        btn_cancel = CancelButton(
            text=cancel_text, bg_color=(0.6, 0.2, 0.2, 1),
            font_size='20sp', bold=True,
            size_hint_x=0.55
        )
        btn_cancel.bind(on_release=do_cancel)
        box.add_widget(btn_back)
        box.add_widget(btn_cancel)
        return box

    # ═══════════════════════════════════════════════════════════════
    #  ПОСТРОЕНИЕ ЦЕНТРАЛЬНОЙ СТРАНИЦЫ (новый дизайн)
    # ═══════════════════════════════════════════════════════════════
    def refresh_list(self):
        app = App.get_running_app()
        if not app:
            return
        app.ensure_default_clients()
        self.list_layout.clear_widgets()
        m_indices, o_idx, b_idx, c_idx = app.get_special_clients()
        special_indices = [i for i in (o_idx, c_idx, b_idx) if i is not None] + m_indices
        other_indices = [i for i in range(len(app.clients)) if i not in special_indices]

        # 1. Панель материалов (ОСТАТОК / ЧЕРНЫЙ / БЕЛЫЙ)
        self.list_layout.add_widget(self._build_banner_panel(o_idx, c_idx, b_idx))

        # 2. Секция «КЛИЕНТЫ»
        clients_card = self._make_section("КЛИЕНТЫ", (0.2, 0.75, 0.84, 1), (0.2, 0.75, 0.84, 1), hdr_text=(0.03, 0.2, 0.23, 1))
        if other_indices:
            for i in other_indices:
                clients_card.add_widget(self._build_client_row(i))
        else:
            empty = Label(text="Нет клиентов", font_size='15sp', color=(0.55, 0.55, 0.55, 1), size_hint_y=None, height=50)
            clients_card.add_widget(empty)
        self.list_layout.add_widget(clients_card)

        # 3. Секция «МОИ ДОЛГИ» (кредиторы)
        if m_indices:
            cred_card = self._make_section("МОИ ДОЛГИ", (0.88, 0.4, 0.29, 1), (0.88, 0.4, 0.29, 1), hdr_text=(0.3, 0.08, 0.03, 1))
            for idx in m_indices:
                cred_card.add_widget(self._build_creditor_row(idx))
            self.list_layout.add_widget(cred_card)

        # 4. Секция «ОБЩИЕ ИТОГИ»
        self.list_layout.add_widget(self._build_totals_section())

        self.list_layout.add_widget(Widget(size_hint_y=None, height=20))

        # КНОПКА НАЗАД (свайп влево)
        if self.back_btn.parent:
            self.back_btn.parent.remove_widget(self.back_btn)
        back_wrapper = BoxLayout(size_hint_y=None, height=117)
        back_wrapper.add_widget(Widget(size_hint_x=0.325))
        back_wrapper.add_widget(self.back_btn)
        back_wrapper.add_widget(Widget(size_hint_x=0.325))
        self.list_layout.add_widget(back_wrapper)

    # ── ОТРИСОВКА ФОНОВ ──
    def _draw_section_bg(self, w, border):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*border)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[(22, 22)] * 4)
            Color(0.03, 0.03, 0.05, 1)
            RoundedRectangle(pos=(w.x + 7, w.y + 7), size=(w.width - 14, w.height - 14), radius=[(14, 14)] * 4)

    def _draw_header_bg(self, w, bg):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*bg)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[(0, 0), (0, 0), (15, 15), (15, 15)])

    def _draw_panel_bg(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0.5, 0.5, 0.58, 1)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[(22, 22)] * 4)
            Color(0.05, 0.05, 0.07, 1)
            RoundedRectangle(pos=(w.x + 6, w.y + 6), size=(w.width - 12, w.height - 12), radius=[(14, 14)] * 4)

    def _draw_neon(self, w, g):
        w.canvas.before.clear()
        x, y, wd, h = w.x, w.y, w.width, w.height
        with w.canvas.before:
            for exp, a_ in ((6, 0.06), (4, 0.11), (2, 0.20)):
                Color(g[0], g[1], g[2], a_)
                RoundedRectangle(pos=(x - exp, y - exp), size=(wd + 2 * exp, h + 2 * exp), radius=[(12 + exp, 12 + exp)] * 4)
            Color(g[0], g[1], g[2], 0.95)
            Line(rounded_rectangle=(x + 1, y + 1, wd - 2, h - 2, 12), width=1.8)

    def _fit_font(self, lbl, max_sp=19, min_sp=12):
        from kivy.core.text import Label as CoreLabel
        from kivy.metrics import sp

        def _do(*a):
            avail = lbl.width - 4
            if avail < 10:
                return
            chosen = min_sp
            for size in range(max_sp, min_sp - 1, -1):
                cl = CoreLabel(text=lbl.text, font_size=sp(size), markup=True)
                try:
                    cl.refresh()
                    w = cl.texture.size[0]
                except Exception:
                    w = 0
                if w <= avail:
                    chosen = size
                    break
            lbl.font_size = '%dsp' % chosen

        lbl.bind(width=_do)
        lbl.bind(text=_do)
        _do()

    def _debt_badge(self, value_text, positive=True):
        fg = (0.82, 0.10, 0.10, 1) if positive else (0.10, 0.50, 0.28, 1)
        lbl = Label(text=f"[b]{value_text}[/b]", markup=True, font_size='20sp',
                    color=fg, halign='center', valign='middle', size_hint=(None, 1))

        def _fitw(*a):
            lbl.texture_update()
            nw = max(64, lbl.texture_size[0] + 34)
            if abs(lbl.width - nw) > 0.5:
                lbl.width = nw

        def _bg(*a):
            lbl.canvas.before.clear()
            if lbl.height < 4:
                return
            h = lbl.height * 0.64
            y = lbl.y + (lbl.height - h) / 2.0
            with lbl.canvas.before:
                Color(0.92, 0.93, 0.95, 1)
                RoundedRectangle(pos=(lbl.x, y), size=(lbl.width, h),
                                 radius=[(h / 2.0, h / 2.0)] * 4)

        lbl.bind(texture_size=lambda *a: _fitw())
        lbl.bind(pos=_bg, size=_bg)
        _fitw()
        return lbl

    def _draw_tap_bg(self, w, base=(0.17, 0.17, 0.22), border=(0.46, 0.46, 0.56), rad=12):
        w.canvas.before.clear()
        pressed = getattr(w, 'state', 'normal') == 'down'
        f = [min(c + 0.1, 1.0) for c in base] if pressed else list(base)
        with w.canvas.before:
            Color(border[0], border[1], border[2], 1)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[(rad, rad)] * 4)
            Color(f[0], f[1], f[2], 1)
            RoundedRectangle(pos=(w.x + 2, w.y + 2), size=(w.width - 4, w.height - 4), radius=[(rad - 2, rad - 2)] * 4)

    def _make_section(self, title, title_bg, border, hdr_text=(0.04, 0.04, 0.05, 1)):
        card = BoxLayout(orientation='vertical', size_hint_y=None, padding=[7, 7, 7, 14], spacing=12)
        card.bind(minimum_height=card.setter('height'))
        card.bind(pos=lambda *a: self._draw_section_bg(card, border),
                  size=lambda *a: self._draw_section_bg(card, border))
        header = Label(text=f"[b]{title}[/b]", markup=True, font_size='22sp',
                       color=hdr_text, halign='center', valign='middle',
                       size_hint_y=None, height=60)
        header.bind(size=lambda s, v: setattr(s, 'text_size', v))
        header.bind(pos=lambda *a: self._draw_header_bg(header, title_bg),
                    size=lambda *a: self._draw_header_bg(header, title_bg))
        card.add_widget(header)
        return card

    def _banner_row(self, text, edit_cb, neon=None, big=False):
        row = BoxLayout(size_hint_y=None, height=(140 if big else 106), spacing=8, padding=[6, 5, 6, 5])
        click = ClickBox(orientation='horizontal', padding=[12, 0, 0, 0])
        lbl = Label(text=text, markup=True, font_size='19sp', halign='left', valign='middle')
        lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        if big:
            self._fit_font(lbl, max_sp=32, min_sp=19)
        else:
            self._fit_font(lbl, max_sp=25, min_sp=15)
        click.add_widget(lbl)
        click.bind(on_release=lambda *a: edit_cb(None))
        if neon:
            _b = (neon[0] * 0.22, neon[1] * 0.22, neon[2] * 0.22)
            _bd = neon
        else:
            _b = (0.17, 0.17, 0.22)
            _bd = (0.46, 0.46, 0.56)
        click.bind(pos=lambda *a: self._draw_tap_bg(click, base=_b, border=_bd),
                   size=lambda *a: self._draw_tap_bg(click, base=_b, border=_bd),
                   state=lambda *a: self._draw_tap_bg(click, base=_b, border=_bd))
        edit = EditButton(text="", bg_color=(0.72, 0.53, 0.13, 1), size_hint=(None, 1), width=216, radius=16)
        edit.bind(on_release=edit_cb)
        row.add_widget(click)
        row.add_widget(edit)
        if neon:
            row.bind(pos=lambda *a: self._draw_neon(row, neon),
                     size=lambda *a: self._draw_neon(row, neon))
        return row

    def _build_banner_panel(self, o_idx, c_idx, b_idx):
        app = App.get_running_app()
        panel = BoxLayout(orientation='vertical', size_hint_y=None, padding=[10, 10, 10, 10], spacing=10)
        panel.bind(minimum_height=panel.setter('height'))
        panel.bind(pos=lambda *a: self._draw_panel_bg(panel),
                   size=lambda *a: self._draw_panel_bg(panel))
        for idx, kind in ((o_idx, 'ost'), (c_idx, 'black'), (b_idx, 'white')):
            if idx is None:
                continue
            client = app.clients[idx]
            if kind == 'ost':
                rolls = getattr(app, 'rolls', []) or []
                cnt = len(rolls)
                # главный рулон — белый 3.2 (его остаток на виду, как раньше)
                main = None
                for _r in rolls:
                    if _r.get('color') == 'white' and '3.2' in str(_r.get('width', '')):
                        main = _r
                        break
                if main is None:
                    for _r in rolls:
                        if _r.get('color') == 'white':
                            main = _r
                            break
                if main is None and rolls:
                    main = rolls[0]
                if cnt == 0:
                    text = "[b][color=#FFFFFF]ОСТАТКИ[/color][/b]  [color=#9A9A9A]рулонов:[/color]  [b][color=#FFB84D]нет[/color][/b]"
                else:
                    _rem = format_num_simple(main.get('remain', '0')) if main else '0'
                    text = f"[b][color=#FFFFFF]ОСТАТКИ[/color][/b]  [size=15sp][color=#9A9A9A]рул.: {cnt}[/color][/size]    [b][color=#FFB84D]{_rem} м[/color][/b]"
                row = self._banner_row(text, (lambda x: self.show_rolls_inventory()), None, big=True)
            else:
                disp = "БЕЛЫЙ" if kind == 'white' else "ЧЕРНЫЙ"
                dnum = abs(safe_float(client.get('debt', '0')))
                dval = format_num_simple(dnum)
                if dnum > 0:
                    text = f"[b][color=#FFFFFF]{disp}[/color][/b]  [color=#9A9A9A]МИНУС:[/color] [b][color=#FF8A80]{dval} р[/color][/b]"
                else:
                    text = f"[b][color=#FFFFFF]{disp}[/color][/b]  [b][color=#5FD39B]ОСТАТОК: 0 р[/color][/b]"
                neon = (0.66, 0.3, 1.0) if kind == 'white' else (0.30, 0.55, 1.0)
                row = self._banner_row(text, (lambda x, i=idx: self.show_edit_popup(i)), neon)
            panel.add_widget(row)
        return panel

    def _build_client_row(self, i):
        app = App.get_running_app()
        client = app.clients[i]
        n_orig = client.get('name', '').upper()
        d_num = abs(safe_float(client.get('debt', '0')))
        d_val = format_num_simple(d_num)
        row = BoxLayout(size_hint_y=None, height=116, spacing=8)
        lbl = Label(text=f"[b][color=#FFFFFF]{n_orig}[/color][/b]  [color=#9A9A9A]ДОЛГ:[/color]",
                    markup=True, font_size='19sp', halign='left', valign='middle')
        lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self._fit_font(lbl, max_sp=25, min_sp=15)
        badge = self._debt_badge(f"{d_val} р" if d_num > 0 else "0", positive=(d_num > 0))
        click = ClickBox(orientation='horizontal', padding=[10, 0, 8, 0], spacing=8)
        click.add_widget(lbl)
        click.add_widget(badge)
        click.bind(on_release=lambda x, idx=i: self.on_client_click(idx))
        click.bind(pos=lambda *a: self._draw_tap_bg(click),
                   size=lambda *a: self._draw_tap_bg(click),
                   state=lambda *a: self._draw_tap_bg(click))
        ist = IstClockButton(size_hint=(None, 1), width=104, radius=16)
        ist.bind(on_release=lambda x, idx=i: self.show_history_popup(idx))
        edit = EditButton(text="", bg_color=(0.72, 0.53, 0.13, 1), size_hint=(None, 1), width=104, radius=16)
        edit.bind(on_release=lambda x, idx=i: self.show_edit_popup(idx))
        row.add_widget(click)
        row.add_widget(ist)
        row.add_widget(edit)
        return row

    def _build_creditor_row(self, idx):
        app = App.get_running_app()
        c = app.clients[idx]
        c_name = c.get('name', '').upper()
        d_val = format_num_simple(c.get('debt', '0'))
        row = BoxLayout(size_hint_y=None, height=116, spacing=8)
        d_num_cr = safe_float(c.get('debt', '0'))
        lbl = Label(text=f"[b][color=#FFFFFF]{c_name}[/color][/b]",
                    markup=True, font_size='19sp', halign='left', valign='middle')
        lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self._fit_font(lbl, max_sp=25, min_sp=15)
        badge = self._debt_badge(f"{d_val} р", positive=(d_num_cr > 0))
        click = ClickBox(orientation='horizontal', padding=[10, 0, 8, 0], spacing=8)
        click.add_widget(lbl)
        click.add_widget(badge)
        click.bind(on_release=lambda x, i=idx: self.show_malevich_main_menu(i))
        click.bind(pos=lambda *a: self._draw_tap_bg(click),
                   size=lambda *a: self._draw_tap_bg(click),
                   state=lambda *a: self._draw_tap_bg(click))
        ist = IstClockButton(size_hint=(None, 1), width=104, radius=16)
        ist.bind(on_release=lambda x, i=idx: self.show_history_popup(i))
        edit = EditButton(text="", bg_color=(0.72, 0.53, 0.13, 1), size_hint=(None, 1), width=104, radius=16)
        edit.bind(on_release=lambda x, i=idx: self.show_creditor_edit_popup(i))
        row.add_widget(click)
        row.add_widget(ist)
        row.add_widget(edit)
        return row

    def _build_totals_section(self):
        app = App.get_running_app()
        tot_debt, my_debt, _, profit_val = app.get_totals()
        card = self._make_section("ОБЩИЕ ИТОГИ", (0.5, 0.81, 0.6, 1), (0.5, 0.81, 0.6, 1), hdr_text=(0.05, 0.23, 0.11, 1))
        r1 = BoxLayout(size_hint_y=None, height=92)
        l1 = Label(text=f"[b][color=#FFFFFF]ДОЛЖНЫ: [/color][color=#8FE6B0]{format_num_simple(tot_debt)} р[/color][/b]",
                   markup=True, font_size='23sp', halign='center', valign='middle')
        l1.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self._fit_font(l1, max_sp=30, min_sp=17)
        l1.bind(pos=lambda *a: self._draw_tap_bg(l1),
                size=lambda *a: self._draw_tap_bg(l1))
        r1.add_widget(l1)
        card.add_widget(r1)
        r2 = BoxLayout(size_hint_y=None, height=92, spacing=6)
        if profit_val >= 0:
            ptxt = f"[b][color=#FFFFFF]ПРИБЫЛЬ: [/color][color=#8FE6B0]{format_num_simple(profit_val)} р[/color][/b]"
        else:
            ptxt = f"[b][color=#FF6B6B]ПРИБЫЛЬ: -{format_num_simple(abs(profit_val))} р[/color][/b]"
        pl = Label(text=ptxt, markup=True, font_size='23sp', halign='center', valign='middle')
        pl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self._fit_font(pl, max_sp=30, min_sp=17)
        pclick = ClickBox(orientation='horizontal', padding=[10, 0, 0, 0])
        pclick.add_widget(pl)
        pclick.bind(on_release=lambda x: self.show_profit_correction_popup())
        pclick.bind(pos=lambda *a: self._draw_tap_bg(pclick),
                    size=lambda *a: self._draw_tap_bg(pclick),
                    state=lambda *a: self._draw_tap_bg(pclick))
        pedit = EditButton(text="", bg_color=(0.72, 0.53, 0.13, 1), size_hint=(None, 1), width=216, radius=16)
        pedit.bind(on_release=lambda x: self.show_profit_correction_popup())
        phist = RoundedButton(text="Ист", bg_color=(0.29, 0.45, 0.78, 1), size_hint=(None, 1), width=156, radius=16, font_size='18sp', bold=True)
        phist.bind(on_release=lambda x: self.show_profit_history_popup())
        r2.add_widget(pclick)
        r2.add_widget(phist)
        r2.add_widget(pedit)
        card.add_widget(r2)
        return card

    def show_profit_history_popup(self, *args):
        app = App.get_running_app()
        if not app:
            return
        log = list(getattr(app, 'profit_log', []) or [])
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=[6, 8, 6, 8])
        grid.bind(minimum_height=grid.setter('height'))
        scroll.add_widget(grid)
        pop = TopMenuPopup(title="ИСТОРИЯ ПРИБЫЛИ",
                           content=BoxLayout(orientation='vertical', spacing=17, padding=[12, 12, 12, 12]),
                           size_hint=(0.95, 0.9))
        pop.title_size = '18sp'
        pop.background_color = (0.043, 0.055, 0.08, 1)
        legend = Label(text="", markup=True, font_size='13sp', size_hint_y=None, height=68, halign='center', valign='middle')
        legend.text = "[color=#8FE6B0]\u0437\u0435\u043b\u0451\u043d\u044b\u0439 \u2014 \u0447\u0438\u0441\u0442\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c[/color]\n[color=#FFB347]\u043e\u0440\u0430\u043d\u0436\u0435\u0432\u044b\u0439 \u2014 \u043f\u0440\u0435\u0434\u043f\u043e\u043b\u0430\u0433\u0430\u0435\u043c\u0430\u044f[/color]"
        legend.bind(size=lambda s, v: setattr(s, 'text_size', v))
        if not log:
            empty = Label(text="[color=#5A6472]\u041f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0437\u0430\u043f\u0438\u0441\u0435\u0439.\n\u041d\u043e\u0432\u044b\u0435 \u0437\u0430\u043a\u0430\u0437\u044b \u043f\u043e\u044f\u0432\u044f\u0442\u0441\u044f \u0437\u0434\u0435\u0441\u044c.[/color]",
                          markup=True, font_size='16sp', size_hint_y=None, height=150, halign='center', valign='middle')
            empty.bind(size=lambda s, v: setattr(s, 'text_size', v))
            grid.add_widget(empty)
        else:
            _MN = ["", "\u044f\u043d\u0432\u0430\u0440\u044f", "\u0444\u0435\u0432\u0440\u0430\u043b\u044f", "\u043c\u0430\u0440\u0442\u0430", "\u0430\u043f\u0440\u0435\u043b\u044f", "\u043c\u0430\u044f", "\u0438\u044e\u043d\u044f", "\u0438\u044e\u043b\u044f", "\u0430\u0432\u0433\u0443\u0441\u0442\u0430", "\u0441\u0435\u043d\u0442\u044f\u0431\u0440\u044f", "\u043e\u043a\u0442\u044f\u0431\u0440\u044f", "\u043d\u043e\u044f\u0431\u0440\u044f", "\u0434\u0435\u043a\u0430\u0431\u0440\u044f"]
            def _sd(d):
                try:
                    p = (d or '').split(' ')[0].split('.'); return '%d %s' % (int(p[0]), _MN[int(p[1])])
                except Exception:
                    return d or ''
            for it in reversed(log):
                assumed = bool(it.get('assumed'))
                pr = safe_float(it.get('profit', 0))
                col = '#FFB347' if assumed else '#8FE6B0'
                sign = '+' if pr >= 0 else '-'
                name = (it.get('name') or '').upper()
                date = _sd(it.get('date') or '')
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, padding=[16, 6, 16, 6])
                def _rb(w, *a):
                    w.canvas.before.clear()
                    with w.canvas.before:
                        Color(0.1, 0.12, 0.16, 1)
                        RoundedRectangle(pos=w.pos, size=w.size, radius=[(14, 14)] * 4)
                row.bind(pos=_rb, size=_rb)
                extra = ' [size=11sp][color=#FFB347](\u043f\u0440\u0435\u0434\u043f\u043e\u043b\u0430\u0433.)[/color][/size]' if assumed else ''
                line = Label(text=f"[b]{name}[/b]  [size=12sp][color=#7A8494]{date}[/color][/size]   [b][color={col}]{sign}{format_num_simple(abs(pr))} \u20bd[/color][/b]" + extra,
                             markup=True, font_size='17sp', color=(1, 1, 1, 1), halign='left', valign='middle')
                line.bind(size=lambda s, v: setattr(s, 'text_size', v))
                row.add_widget(line)
                grid.add_widget(row)
        pop.content.add_widget(legend)
        pop.content.add_widget(scroll)
        btn_clear = RoundedButton(text="\u041e\u0427\u0418\u0421\u0422\u0418\u0422\u042c \u0418\u0421\u0422\u041e\u0420\u0418\u042e", bg_color=(0.5, 0.22, 0.55, 1), size_hint_y=None, height=104, bold=True, radius=22, font_size='19sp')
        def _do_clear_log(*a):
            cp = AppPopup(title="\u0412\u041d\u0418\u041c\u0410\u041d\u0418\u0415", size_hint=(0.85, 0.5), content=BoxLayout(orientation='vertical', spacing=18, padding=20))
            cp.background_color = (0.043, 0.055, 0.08, 1)
            msg = Label(text="\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0432\u0441\u044e \u0438\u0441\u0442\u043e\u0440\u0438\u044e \u043f\u0440\u0438\u0431\u044b\u043b\u0438?", halign='center', valign='middle', font_size='18sp')
            msg.bind(size=lambda s, v: setattr(s, 'text_size', v))
            byes = RoundedButton(text="\u0414\u0410, \u041e\u0427\u0418\u0421\u0422\u0418\u0422\u042c", bg_color=(0.5, 0.22, 0.55, 1), size_hint_y=None, height=100, bold=True)
            def _yes(x):
                app.profit_log = []
                app.save_data()
                cp.dismiss()
                pop.dismiss()
            byes.bind(on_release=_yes)
            cp.content.add_widget(msg)
            cp.content.add_widget(byes)
            cp.content.add_widget(self.get_bottom_buttons(cp, cancel_text="\u041e\u0422\u041c\u0415\u041d\u0410"))
            cp.open()
        btn_clear.bind(on_release=_do_clear_log)
        pop.content.add_widget(btn_clear)
        pop.content.add_widget(self.get_bottom_buttons(pop, cancel_text="\u0417\u0410\u041a\u0420\u042b\u0422\u042c"))
        pop.open()

    def show_reports_stub(self, *args):
        self.show_reports_popup()

    def show_reports_popup(self, period='month'):
        app = App.get_running_app()
        if not app:
            return
        m_indices, o_idx, b_idx, c_idx = app.get_special_clients()
        special_debt_indices = [i for i in (b_idx, c_idx) if i is not None]

        now = datetime.now()
        today_str = now.strftime("%d.%m.%y")
        month_str = now.strftime("%m.%y")

        def in_period(date_field):
            d = (date_field or '').split(' ')[0]
            if period == 'day':
                return d == today_str
            elif period == 'month':
                parts = d.split('.')
                return len(parts) == 3 and f"{parts[1]}.{parts[2]}" == month_str
            return True  # all

        total_revenue, paid_to_print, banner_purchases, net_profit = period_totals(app, in_period)

        # ── UI ──
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=12, padding=[12, 15, 12, 15], size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        _ptitle = {'day': 'СЕГОДНЯ', 'month': 'ЗА МЕСЯЦ', 'all': 'ЗА ВСЁ ВРЕМЯ'}
        pop = TopMenuPopup(title=f"ОТЧЁТ · {_ptitle.get(period, '')}", content=scroll, size_hint=(0.96, 0.92))
        pop.title_size = '20sp'

        # Переключатель периода
        period_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=80, spacing=8)
        for pk, pn in (('day', 'ДЕНЬ'), ('month', 'МЕСЯЦ'), ('all', 'ВСЁ')):
            active = (pk == period)
            pbtn = RoundedButton(text=pn, bg_color=(0.2, 0.55, 0.85, 1) if active else (0.25, 0.25, 0.3, 1),
                                 font_size='18sp', bold=True)
            pbtn.bind(on_release=lambda x, k=pk: self.safe_transition(pop, self.show_reports_popup, k))
            period_box.add_widget(pbtn)
        content.add_widget(period_box)

        # Главная карточка — чистая прибыль
        prof_card = BoxLayout(orientation='vertical', size_hint_y=None, height=200, padding=[15, 16, 15, 16], spacing=8)
        def _draw_pc(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.1, 0.28, 0.16, 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(18,18)]*4)
                Color(0.25, 0.7, 0.4, 0.4)
                RoundedRectangle(pos=(w.x+2, w.y+2), size=(w.width-4, w.height-4), radius=[(16,16)]*4)
        prof_card.bind(pos=_draw_pc, size=_draw_pc)
        # акцентная плашка заголовка
        _pl1 = BgLabel(text="[b][color=#CFF5DD]ЧИСТАЯ ПРИБЫЛЬ ЗА ПЕРИОД[/color][/b]", markup=True, font_size='15sp',
                     halign='center', valign='middle', size_hint_y=0.36, radius=10)
        _pl1.bg_color = [0.06, 0.18, 0.1, 1]
        _pl1.bind(size=lambda s, v: setattr(s, 'text_size', v))
        _pl2 = Label(text=f"[b][color=#8FE6B0]{format_num_simple(net_profit)} руб[/color][/b]", markup=True,
                     font_size='30sp', halign='center', valign='middle', size_hint_y=0.64)
        _pl2.bind(size=lambda s, v: setattr(s, 'text_size', v))
        prof_card.add_widget(_pl1)
        prof_card.add_widget(_pl2)
        content.add_widget(prof_card)

        def stat_row(title, value, color="#FFFFFF"):
            row = BgLabel(text=f"[b]{title}:[/b]  [color={color}]{value}[/color]", markup=True,
                          font_size='17sp', halign='left', valign='middle', size_hint_y=None, height=58, radius=10, padding=[14, 8])
            row.bg_color = [0.14, 0.14, 0.18, 1]
            def _upd(s, *a):
                s.text_size = (s.width - 28, None)
            row.bind(width=_upd)
            def _h(s, ts):
                s.height = max(58, ts[1] + 22)
            row.bind(texture_size=_h)
            return row

        def stat_row2(title, value, color="#9FE6B5"):
            # Название сверху жирным белым, значение строчкой ниже (value несёт свои цвета)
            row = BgLabel(text=f"[b][color=#FFFFFF]{title}[/color][/b]\n[size=16sp]{value}[/size]", markup=True,
                          font_size='18sp', halign='left', valign='middle', size_hint_y=None, height=76, radius=10, padding=[14, 10])
            row.bg_color = [0.14, 0.14, 0.18, 1]
            def _upd(s, *a):
                s.text_size = (s.width - 28, None)
            row.bind(width=_upd)
            def _h(s, ts):
                s.height = max(76, ts[1] + 24)
            row.bind(texture_size=_h)
            return row

        content.add_widget(stat_row("ОБОРОТ (клиенты)", f"{format_num_simple(total_revenue)} р", "#8FD3FF"))
        content.add_widget(stat_row("ОТДАНО ЗА ПЕЧАТЬ", f"{format_num_simple(paid_to_print)} р", "#FF8A80"))
        content.add_widget(stat_row("ЗАКУПКА БАНЕРОВ", f"{format_num_simple(banner_purchases)} р", "#FF8A80"))

        content.add_widget(Widget(size_hint_y=None, height=10))
        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ"))
        content.add_widget(Widget(size_hint_y=None, height=350))
        scroll.add_widget(content)
        pop.open()

    def show_operations_history_stub(self, *args):
        self._stub_popup("ИСТОРИЯ ОПЕРАЦИЙ", "Раздел в разработке. Функционал добавим позже.")

    def _stub_popup(self, title, msg):
        content = BoxLayout(orientation='vertical', spacing=20, padding=20)
        pop = AppPopup(title=title, content=content, size_hint=(0.85, 0.45))
        lbl = Label(text=msg, halign='center', valign='middle', font_size='18sp')
        lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        content.add_widget(lbl)
        btn = CancelButton(text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1), font_size='20sp', bold=True, size_hint=(1, None), height=80)
        btn.bind(on_release=lambda x: pop.dismiss())
        content.add_widget(btn)
        pop.open()

    def show_history_popup(self, idx):
        app = App.get_running_app()
        if not app:
            return
        client = app.clients[idx]
        history = client.get('history') or []

        popup_content = BoxLayout(orientation='vertical', spacing=12, padding=[12, 12, 12, 12])

        # ── ШАПКА: слева имя + «ДОЛГ», справа сумма общего долга ──
        header_card = BoxLayout(orientation='horizontal', size_hint_y=None, height=196, padding=[26, 16, 26, 16], spacing=10)
        _hacc = (0.2, 0.75, 0.84)
        def _draw_header_card(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(_hacc[0], _hacc[1], _hacc[2], 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(24, 24)] * 4)
                Color(0.07, 0.086, 0.133, 1)
                RoundedRectangle(pos=(w.x + 3, w.y + 3), size=(w.width - 6, w.height - 6), radius=[(21, 21)] * 4)
        header_card.bind(pos=_draw_header_card, size=_draw_header_card)
        left_box = BoxLayout(orientation='vertical', size_hint_x=0.42, spacing=22)
        left_box.add_widget(Widget())  # центрируем пару имя+ДОЛГ по вертикали
        lbl_name = Label(
            text=f"[b]{client.get('name', '').upper()}[/b]",
            markup=True, font_size='26sp', color=(1, 1, 1, 1),
            halign='left', valign='middle', size_hint_y=None, height=60
        )
        lbl_name.bind(width=lambda s, v: setattr(s, 'text_size', (v, None)))
        self._fit_font(lbl_name, max_sp=26, min_sp=13)
        _dolg_caption = "МОЙ ДОЛГ" if client.get('is_creditor') else "ДОЛГ"
        lbl_dolg_cap = Label(
            text=f"[b]{_dolg_caption}[/b]", markup=True, font_size='15sp',
            color=(0.55, 0.6, 0.68, 1), halign='left', valign='middle',
            size_hint_y=None, height=30
        )
        lbl_dolg_cap.bind(width=lambda s, v: setattr(s, 'text_size', (v, None)))
        left_box.add_widget(lbl_name)
        left_box.add_widget(lbl_dolg_cap)
        left_box.add_widget(Widget())
        lbl_total = Label(
            text="[b][color=#FFD54F]0 \u20bd[/color][/b]",
            markup=True, font_size='34sp', halign='right', valign='middle', size_hint_x=0.58
        )
        lbl_total.bind(size=lambda s, v: setattr(s, 'text_size', v))
        self._fit_font(lbl_total, max_sp=36, min_sp=20)
        # дата в шапке не показывается; переменная оставлена для refresh
        lbl_viewdate = BgLabel(text="", markup=True, size_hint_y=None, height=0, radius=11)
        lbl_viewdate.bg_color = [0.11, 0.13, 0.18, 1]
        header_card.add_widget(left_box)
        header_card.add_widget(lbl_total)
        popup_content.add_widget(header_card)

        # ── ПАНЕЛЬ ФИЛЬТРА: дата | сумма/метры за день | ранее ──
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=110, spacing=10)
        current_date_str = datetime.now().strftime("%d.%m.%y")
        filter_btn = CalendarButton(date_str=current_date_str, size_hint_x=0.3)

        mid_box = BoxLayout(orientation='vertical', size_hint_x=0.38, spacing=2, padding=[0, 8, 0, 8])
        def _draw_mid_bg(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.11, 0.13, 0.18, 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(14, 14)] * 4)
        mid_box.bind(pos=_draw_mid_bg, size=_draw_mid_bg)
        title_lbl = Label(text="", markup=True, font_size='20sp', bold=True,
                          halign='center', valign='middle', size_hint_y=0.55)
        title_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        meters_lbl = Label(text="", markup=True, font_size='15sp',
                           halign='center', valign='middle',
                           color=(0.6, 0.88, 1, 1), size_hint_y=0.45)
        meters_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        mid_box.add_widget(title_lbl)
        mid_box.add_widget(meters_lbl)

        btn_earlier = RoundedButton(text="РАНЕЕ", bg_color=(0.22, 0.28, 0.4, 1),
                                    size_hint_x=0.32, font_size='19sp', bold=True, radius=18)
        top_bar.add_widget(filter_btn)
        top_bar.add_widget(mid_box)
        top_bar.add_widget(btn_earlier)
        popup_content.add_widget(top_bar)

        popup_content.add_widget(Widget(size_hint_y=None, height=25))

        scroll = ScrollView(bar_width=5, bar_color=(0.4, 0.45, 0.55, 0.5), bar_inactive_color=(0.4, 0.45, 0.55, 0.15))
        list_layout = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=[2, 12, 2, 0])
        list_layout.bind(minimum_height=list_layout.setter('height'))
        scroll.add_widget(list_layout)
        list_frame = BoxLayout(padding=[10, 10, 10, 10])
        def _draw_list_frame(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.9, 0.72, 0.2, 0.95)   # золотая рамка для красоты
                Line(rounded_rectangle=(w.x + 2, w.y + 2, w.width - 4, w.height - 4, 20), width=2.6)
        list_frame.bind(pos=_draw_list_frame, size=_draw_list_frame)
        list_frame.add_widget(scroll)
        popup_content.add_widget(list_frame)

        popup_content.add_widget(Widget(size_hint_y=None, height=10))

        btn_all_orders = RoundedButton(
            text="ВСЕ ЗАКАЗЫ /\nКОПИРОВАТЬ", bg_color=(0.13, 0.38, 0.7, 1),
            size_hint=(1, 1), font_size='15sp', bold=True, radius=22
        )
        def _hist_back_cb():
            if getattr(pop, 'is_dismissing_flag', False): return
            if current_viewed_date[0] == current_date_str:
                pop.is_dismissing_flag = True
                pop.dismiss()
            else:
                open_date_filter_menu(None, go_to_days_of=current_viewed_date[0])

        btn_clear_hist = RoundedButton(
            text="ОЧИСТИТЬ\nИСТОРИЮ", bg_color=(0.42, 0.2, 0.62, 1),
            size_hint=(1, 1), font_size='15sp', bold=True, radius=22
        )

        def confirm_clear_history(instance):
            c_name = client.get('name', '').upper()
            p_conf = AppPopup(
                title="ВНИМАНИЕ",
                content=BoxLayout(orientation='vertical', spacing=20, padding=20),
                size_hint=(0.85, 0.5)
            )
            btn_yes = RoundedButton(
                text="ДА, УДАЛИТЬ ВСЁ", bg_color=(0.8, 0.2, 0.2, 1),
                height=100, size_hint_y=None, bold=True
            )

            def on_yes(x):
                if getattr(p_conf, 'is_dismissing_flag', False): return
                p_conf.is_dismissing_flag = True
                ok, message = clear_history(app, client)
                if not ok:
                    p_conf.is_dismissing_flag = False
                    self._stub_popup('ИСТОРИЯ', message)
                    return
                refresh_history_view(current_viewed_date[0])
                p_conf.dismiss()

            btn_yes.bind(on_release=on_yes)
            p_conf.content.add_widget(
                Label(
                    text=f"Удалить всю историю\nклиента {c_name}?\nЭто необратимо.",
                    halign='center', valign='middle', font_size='18sp'
                )
            )
            p_conf.content.add_widget(btn_yes)
            p_conf.content.add_widget(self.get_bottom_buttons(p_conf, cancel_text="ОТМЕНА"))
            p_conf.open()

        btn_clear_hist.bind(on_release=confirm_clear_history)

        actions_row = BoxLayout(orientation='horizontal', size_hint_x=0.875, spacing=12)
        actions_row.add_widget(btn_all_orders)
        actions_row.add_widget(btn_clear_hist)
        actions_wrap = BoxLayout(orientation='horizontal', size_hint_y=None, height=133)
        actions_wrap.add_widget(Widget(size_hint_x=0.0625))
        actions_wrap.add_widget(actions_row)
        actions_wrap.add_widget(Widget(size_hint_x=0.0625))
        popup_content.add_widget(actions_wrap)
        popup_content.add_widget(Widget(size_hint_y=None, height=8))

        pop = TopMenuPopup(title="ИСТОРИЯ ЗАКАЗОВ", content=popup_content, size_hint=(0.95, 0.9))
        pop.title_size = '20sp'
        pop.background_color = (0.043, 0.055, 0.08, 1)

        months_names = {"01": "Январь", "02": "Февраль", "03": "Март", "04": "Апрель",
                        "05": "Май", "06": "Июнь", "07": "Июль", "08": "Август",
                        "09": "Сентябрь", "10": "Октябрь", "11": "Ноябрь", "12": "Декабрь"}

        current_viewed_date = [current_date_str]

        def refresh_history_view(date_str):
            current_viewed_date[0] = date_str
            list_layout.clear_widgets()
            filter_btn.set_date(date_str)
            filtered_items = []
            for i, item in enumerate(history):
                if not item:
                    continue
                raw_date = (item.get('date') or '').split(' ')[0]
                if raw_date == date_str:
                    filtered_items.append((i, item))
            day_total = sum(safe_float(item.get('sum', '0')) for _, item in filtered_items)
            grand_total = safe_float(client.get('debt', '0'))
            lbl_total.text = f"[b][color=#FFD54F]{format_num_simple(grand_total)} \u20bd[/color][/b]"
            _today = datetime.now().strftime("%d.%m.%y")
            _dp = date_str.split('.')
            if len(_dp) == 3:
                _mname = months_names.get(_dp[1], _dp[1])
                _readable = f"{int(_dp[0])} {_mname} 20{_dp[2]}"
            else:
                _readable = date_str
            if date_str == _today:
                lbl_viewdate.text = f"[b][color=#5FD3FF]СЕГОДНЯ · {_readable}[/color][/b]"
            else:
                lbl_viewdate.text = f"[b][color=#FFB84D]{_readable}[/color][/b]"
            day_meters = 0.0
            for _, item in filtered_items:
                p = safe_float(item.get('price', 0))
                s = safe_float(item.get('sum', 0))
                if p > 0:
                    day_meters += s / p
            title_lbl.text = f"[color=#00FF00][b]{format_num_simple(day_total)} \u20bd[/b][/color]"
            meters_lbl.text = f"[color=#88CCFF]{format_num_simple(round(day_meters, 2))} м²[/color]" if day_meters > 0 else ""

            if not filtered_items:
                empty = Label(text=f"[color=#5A6472]Нет записей за {date_str}[/color]",
                              markup=True, font_size='17sp', size_hint_y=None, height=140,
                              halign='center', valign='middle')
                empty.bind(size=lambda s, v: setattr(s, 'text_size', v))
                list_layout.add_widget(empty)
            else:
                row_counter = 1
                for orig_idx, item in filtered_items:
                    if not item:
                        continue
                    raw_desc = str(item.get('desc') or "")
                    sum_val = str(item.get('sum') or "0")
                    price_val = item.get('price', None)
                    badge_val = item.get('badge', None)
                    if badge_val is None:
                        b_match = re.search(r'\[(.*?)\]', raw_desc)
                        if b_match:
                            badge_val = f"[{b_match.group(1)}]"
                            raw_desc = re.sub(r'\s*\[.*?\]', '', raw_desc)
                        else:
                            badge_val = ""
                    raw_desc = raw_desc.replace("Заказ:", "").strip()
                    if price_val is None:
                        nums = re.findall(r'\b\d+(?:\.\d+)?\b', raw_desc)
                        if len(nums) >= 2:
                            try:
                                l, w = safe_float(nums[0]), safe_float(nums[1])
                                c = safe_float(nums[2]) if len(nums) >= 3 else 1.0
                                area = l * w * c
                                if area > 0: price_val = safe_float(sum_val) / area
                            except: pass
                    item_meters = 0.0
                    pv = safe_float(price_val) if price_val else 0
                    if pv > 0:
                        item_meters = safe_float(sum_val) / pv
                    qty_match = re.search(r'\s+x\s*(\d+(?:\.\d+)?)(шт)?', raw_desc)
                    if qty_match:
                        qty_str = f"x{qty_match.group(1)}шт"
                        raw_desc = raw_desc.replace(qty_match.group(0), "")
                        p_str = f" [color=#FF4444]{format_num_simple(price_val)}[/color] {qty_str}" if price_val else f" {qty_str}"
                    else:
                        p_str = f" [color=#FF4444]{format_num_simple(price_val)}[/color]" if price_val else ""
                    b_str = f"  [size=11sp][color=#8A8A8A]{badge_val}[/size]" if badge_val else ""
                    m_str = f"  [color=#88CCFF][size=12sp]{format_num_simple(round(item_meters,2))}м²[/size][/color]" if item_meters > 0 else ""
                    desc_text = f"[b]{row_counter}) {raw_desc}[/b]{p_str}  [color=#00FF00]= {sum_val}[/color]{m_str}{b_str}"
                    row_counter += 1
                    row = BoxLayout(size_hint_y=None, height=64, spacing=10, padding=[12, 4, 8, 4])
                    def _draw_row_bg(w, *a):
                        w.canvas.before.clear()
                        with w.canvas.before:
                            Color(0.1, 0.12, 0.16, 1)
                            RoundedRectangle(pos=w.pos, size=w.size, radius=[(12, 12)] * 4)
                    row.bind(pos=_draw_row_bg, size=_draw_row_bg)
                    lbl = Label(text=desc_text, markup=True, font_size='13sp', halign='left', valign='middle')
                    lbl.bind(size=lambda s, v: setattr(s, 'text_size', (v[0], None)))
                    del_btn = RoundedButton(text="X", bg_color=(0.8, 0.2, 0.2, 1), size_hint_x=None, width=54, radius=12)
                    del_btn.bind(on_release=lambda x, order=item, day=date_str: delete_item_callback(order, day))
                    row.add_widget(lbl)
                    row.add_widget(del_btn)
                    list_layout.add_widget(row)

        def delete_item_callback(item, date_str):
            ok, message = reverse_order(app, client, item)
            if not ok:
                self._stub_popup("УДАЛЕНИЕ ЗАКАЗА", message)
                return
            self.refresh_list()
            refresh_history_view(date_str)

        def show_all_orders_popup():
            all_content = BoxLayout(orientation='vertical', spacing=10, padding=[12, 12, 12, 12])
            all_pop = TopMenuPopup(
                title=f"ВСЕ ЗАКАЗЫ: {client.get('name', '').upper()}",
                content=all_content, size_hint=(0.97, 0.95)
            )

            grand_total = safe_float(client.get('debt', '0'))

            lbl_g = Label(
                text=f"[b][color=#FFD700]ИТОГО ДОЛГ: {format_num_simple(grand_total)} р[/color][/b]",
                markup=True, font_size='22sp', halign='center', valign='middle',
                size_hint_y=None, height=55
            )
            lbl_g.bind(size=lambda s, v: setattr(s, 'text_size', v))
            all_content.add_widget(lbl_g)

            date_groups = defaultdict(list)
            for h_item in history:
                if not h_item:
                    continue
                d_str = (h_item.get('date') or '').split(' ')[0]
                date_groups[d_str].append(h_item)

            def date_sort_key(d):
                try:
                    parts = d.split('.')
                    return (int(parts[2]), int(parts[1]), int(parts[0]))
                except:
                    return (0, 0, 0)

            sorted_dates = sorted(date_groups.keys(), key=date_sort_key, reverse=True)

            copy_lines = [
                f"КЛИЕНТ: {client.get('name', '').upper()}",
                f"ОБЩИЙ ДОЛГ: {format_num_simple(grand_total)} р",
                "=" * 34
            ]

            all_scroll = ScrollView()
            all_list = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=[0, 5, 0, 10])
            all_list.bind(minimum_height=all_list.setter('height'))
            all_scroll.add_widget(all_list)
            all_content.add_widget(all_scroll)

            if not sorted_dates:
                all_list.add_widget(Label(
                    text="История пуста", font_size='18sp', color=(0.6, 0.6, 0.6, 1),
                    size_hint_y=None, height=100, halign='center'
                ))
            else:
                for d_str in sorted_dates:
                    items_for_day = date_groups[d_str]
                    day_total = sum(safe_float(it.get('sum', 0)) for it in items_for_day)

                    hdr = Label(
                        text=f"[b][color=#AABBFF]  {d_str}[/color]   [color=#00FF88]+ {format_num_simple(day_total)} р[/color][/b]",
                        markup=True, font_size='17sp', halign='left', valign='middle',
                        size_hint_y=None, height=44
                    )
                    hdr.bind(size=lambda s, v: setattr(s, 'text_size', v))
                    all_list.add_widget(hdr)
                    copy_lines.append(f"\n{d_str}  (+{format_num_simple(day_total)} р):")

                    counter = 1
                    for item in items_for_day:
                        raw_desc = str(item.get('desc') or "")
                        sum_val = str(item.get('sum') or "0")
                        price_val = item.get('price', None)
                        badge_val = item.get('badge', '')
                        raw_desc = raw_desc.replace("Заказ:", "").strip()
                        if not badge_val:
                            b_match = re.search(r'\[(.*?)\]', raw_desc)
                            if b_match:
                                badge_val = f"[{b_match.group(1)}]"
                                raw_desc = re.sub(r'\s*\[.*?\]', '', raw_desc)

                        p_str = f" [color=#FF6666]{format_num_simple(price_val)}р/м2[/color]" if price_val else ""
                        b_str = f"  [size=11sp][color=#888888]{badge_val}[/color][/size]" if badge_val else ""

                        row_lbl = Label(
                            text=f"  [b]{counter})[/b] {raw_desc}{p_str}  [color=#00FF00]= {sum_val} р[/color]{b_str}",
                            markup=True, font_size='13sp', halign='left', valign='middle',
                            size_hint_y=None, height=44
                        )
                        row_lbl.bind(size=lambda s, v: setattr(s, 'text_size', (v[0], None)))
                        row_lbl.bind(texture_size=lambda s, ts: setattr(s, 'height', max(44, ts[1] + 8)))
                        all_list.add_widget(row_lbl)

                        copy_lines.append(f"  {counter}) {raw_desc} = {sum_val} р  {badge_val}")
                        counter += 1

            copy_lines.append(f"\n{'=' * 34}")
            copy_lines.append(f"ИТОГО ДОЛГ: {format_num_simple(grand_total)} р")
            copy_text = "\n".join(copy_lines)

            btn_copy = RoundedButton(
                text="СКОПИРОВАТЬ ВСЁ", bg_color=(0.2, 0.55, 0.85, 1),
                size_hint_y=None, height=75, font_size='18sp', bold=True
            )

            def do_copy(instance):
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(copy_text)
                instance.text = "СКОПИРОВАНО!"
                instance.bg_color = [0.1, 0.7, 0.1, 1]
                Clock.schedule_once(
                    lambda dt: (
                        setattr(instance, 'text', 'СКОПИРОВАТЬ ВСЁ'),
                        setattr(instance, 'bg_color', [0.2, 0.55, 0.85, 1])
                    ), 2.0
                )

            btn_copy.bind(on_release=do_copy)
            all_content.add_widget(btn_copy)
            all_content.add_widget(self.get_bottom_buttons(all_pop, cancel_text="ЗАКРЫТЬ"))
            all_pop.open()

        def open_date_filter_menu(instance, go_to_days_of=None):
            available_dates = defaultdict(set)
            for h_item in history:
                if not h_item:
                    continue
                d_str = (h_item.get('date') or '').split(' ')[0]
                if d_str.count('.') == 2:
                    d, m, y = d_str.split('.')
                    available_dates[f"{m}.{y}"].add(d)
            if go_to_days_of and go_to_days_of.count('.') == 2:
                parts = go_to_days_of.split('.')
                month_year = f"{parts[1]}.{parts[2]}"
                if month_year in available_dates:
                    open_day_filter_menu(month_year, available_dates)
                    return

            monthly_totals = defaultdict(float)
            for h_item in history:
                if not h_item:
                    continue
                d_str = (h_item.get('date') or '').split(' ')[0]
                if d_str.count('.') == 2:
                    d, m, y = d_str.split('.')
                    monthly_totals[f"{m}.{y}"] += safe_float(h_item.get('sum', 0))

            m_content = BoxLayout(orientation='vertical', spacing=10, padding=15)
            m_scroll = ScrollView()
            m_grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
            m_grid.bind(minimum_height=m_grid.setter('height'))
            m_scroll.add_widget(m_grid)
            m_pop = AppPopup(title="ВЫБОР МЕСЯЦА", content=m_content, size_hint=(0.85, 0.7))

            def on_today(x):
                if getattr(m_pop, 'is_dismissing_flag', False): return
                m_pop.is_dismissing_flag = True
                refresh_history_view(datetime.now().strftime("%d.%m.%y"))
                m_pop.dismiss()

            btn_today = RoundedButton(text="СЕГОДНЯ", bg_color=(0.2, 0.6, 0.4, 1), height=90, size_hint_y=None, bold=True)
            btn_today.bind(on_release=on_today)
            m_grid.add_widget(btn_today)
            sorted_months = sorted(available_dates.keys(), key=lambda my: (int(my.split('.')[1]), int(my.split('.')[0])), reverse=True)
            for my in sorted_months:
                m_code, y_code = my.split('.')
                m_name = months_names.get(m_code, m_code)
                m_total = monthly_totals.get(my, 0)
                btn_m = RoundedButton(
                    text=f"[b]{m_name.upper()}[/b]    [color=#FFD700]{format_num_simple(m_total)} р[/color]",
                    markup=True, font_size='19sp',
                    bg_color=(0.15, 0.45, 0.75, 1), height=100, size_hint_y=None, bold=True
                )
                btn_m.bind(on_release=lambda x, month_year=my: self.safe_transition(m_pop, open_day_filter_menu, month_year, available_dates))
                m_grid.add_widget(btn_m)
            m_content.add_widget(m_scroll)
            m_content.add_widget(self.get_bottom_buttons(m_pop, cancel_text="ЗАКРЫТЬ"))
            m_pop.open()

        def open_day_filter_menu(month_year, available_dates):
            m_code, y_code = month_year.split('.')
            m_name = months_names.get(m_code, m_code)
            d_content = BoxLayout(orientation='vertical', spacing=10, padding=15)
            d_scroll = ScrollView()
            d_grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
            d_grid.bind(minimum_height=d_grid.setter('height'))
            d_scroll.add_widget(d_grid)
            d_pop = AppPopup(title=f"ЧИСЛА: {m_name.upper()} 20{y_code}", content=d_content, size_hint=(0.85, 0.7))

            daily_totals = defaultdict(float)
            for h_item in history:
                if not h_item:
                    continue
                d_str = (h_item.get('date') or '').split(' ')[0]
                if d_str.count('.') == 2:
                    d_part, m_part, y_part = d_str.split('.')
                    if f"{m_part}.{y_part}" == month_year:
                        daily_totals[d_part] += safe_float(h_item.get('sum', 0))

            sorted_days = sorted(list(available_dates[month_year]), key=lambda d: int(d) if d.isdigit() else 0)
            for day in sorted_days:
                full_date_str = f"{day}.{month_year}"
                day_total = daily_totals.get(day, 0)
                btn_d = RoundedButton(
                    text=f"[b][size=24sp]{int(day)}[/size][/b]   [size=13sp][color=#FFD700]{format_num_simple(day_total)} р[/color][/size]",
                    markup=True,
                    bg_color=(0.7, 0.4, 0.1, 1), height=80, size_hint_y=None
                )

                def on_day_select(x, ds=full_date_str):
                    if getattr(d_pop, 'is_dismissing_flag', False): return
                    d_pop.is_dismissing_flag = True
                    refresh_history_view(ds)
                    d_pop.dismiss()

                btn_d.bind(on_release=on_day_select)
                d_grid.add_widget(btn_d)
            d_content.add_widget(d_scroll)
            d_content.add_widget(self.get_bottom_buttons(d_pop, prev_cb=lambda: open_date_filter_menu(None), cancel_text="ЗАКРЫТЬ"))
            d_pop.open()

        filter_btn.bind(on_release=open_date_filter_menu)
        btn_earlier.bind(on_release=open_date_filter_menu)
        btn_all_orders.bind(on_release=lambda x: show_all_orders_popup())
        refresh_history_view(current_date_str)

        def do_cancel(instance):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            pop.dismiss()

        popup_content.add_widget(Widget(size_hint_y=None, height=6))
        bottom_row = BoxLayout(orientation='horizontal', spacing=12, size_hint_x=0.875)
        btn_back_bot = RoundedButton(
            text="НАЗАД", bg_color=(1, 0.45, 0, 1),
            font_size='21sp', bold=True, size_hint_x=0.45
        )
        btn_back_bot.bind(on_release=lambda x: _hist_back_cb())
        btn_cancel = CancelButton(
            text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1),
            font_size='21sp', bold=True, size_hint_x=0.55
        )
        btn_cancel.bind(on_release=do_cancel)
        bottom_row.add_widget(btn_back_bot)
        bottom_row.add_widget(btn_cancel)
        bottom_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=137)
        bottom_box.add_widget(Widget(size_hint_x=0.0625))
        bottom_box.add_widget(bottom_row)
        bottom_box.add_widget(Widget(size_hint_x=0.0625))
        popup_content.add_widget(bottom_box)
        pop.open()

    def copy_all_debts(self, instance):
        from kivy.core.clipboard import Clipboard
        app = App.get_running_app()
        if not app:
            return
        tot_debt, my_debt, _, _ = app.get_totals()
        m_indices, o_idx, b_idx, c_idx = app.get_special_clients()
        special_indices = [i for i in (o_idx, c_idx, b_idx) if i is not None] + m_indices
        lines = [f"{c.get('name', '').upper().strip()}: {format_num_simple(safe_float(c.get('debt', 0)))} руб"
                 for i, c in enumerate(app.clients) if i not in special_indices]
        lines.append(f"КЛИЕНТЫ ДОЛЖНЫ: {format_num_simple(tot_debt)} руб")
        lines.append(f"МОЙ ДОЛГ (ВСЕГО): {format_num_simple(my_debt)} руб")
        Clipboard.copy("\n".join(lines))
        instance.bg_color = [0.1, 0.8, 0.1, 1]
        Clock.schedule_once(lambda dt: (setattr(instance, 'text', "СКОПИРОВАТЬ"), setattr(instance, 'bg_color', [0.15, 0.55, 0.75, 1])), 1.5)

    def show_creditor_edit_popup(self, idx):
        app = App.get_running_app()
        if not app:
            return
        c = app.clients[idx]
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=15, padding=15, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        pop = TopMenuPopup(title="РЕДАКТИРОВАНИЕ КРЕДИТОРА", content=scroll, size_hint=(0.95, 0.85))
        content.add_widget(Label(text="Изменить имя текущего:", font_size='18sp', color=(0.8, 0.8, 0.8, 1), size_hint_y=None, height=30))
        in_n = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), text=c.get('name', ''), font_size='22sp', size_hint_y=None, height=90, multiline=False)
        content.add_widget(in_n)
        btn_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=90)
        btn_ok = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.2, 0.6, 0.4, 1), bold=True)
        btn_del = RoundedButton(text="УДАЛИТЬ", bg_color=(0.8, 0.3, 0.3, 1), bold=True)

        def on_edit_save(instance):
            if getattr(pop, 'is_dismissing_flag', False): return
            new_name = in_n.text.strip()
            if new_name:
                c['name'] = new_name
                app.save_data()
                self.refresh_list()
            pop.is_dismissing_flag = True
            pop.dismiss()

        def on_delete(instance):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            app.clients.pop(idx)
            app.save_data()
            self.refresh_list()
            pop.dismiss()

        btn_ok.bind(on_release=on_edit_save)
        btn_del.bind(on_release=on_delete)
        btn_box.add_widget(btn_ok)
        btn_box.add_widget(btn_del)
        content.add_widget(btn_box)
        content.add_widget(Widget(size_hint_y=None, height=10))
        content.add_widget(Label(text="[b]--- ИЛИ ДОБАВИТЬ НОВОГО ---[/b]", markup=True, font_size='18sp', size_hint_y=None, height=40, color=(0.7,0.7,0.7,1)))
        in_new = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="Имя нового (например: КОЗОВ)...", font_size='22sp', size_hint_y=None, height=90, multiline=False)
        content.add_widget(in_new)
        btn_add = RoundedButton(text="+ ДОБАВИТЬ НОВОГО", bg_color=(0.1, 0.5, 0.9, 1), height=90, size_hint_y=None, bold=True)

        def on_add_new(instance):
            if getattr(pop, 'is_dismissing_flag', False): return
            new_name = in_new.text.strip()
            if new_name:
                pop.is_dismissing_flag = True
                app.clients.append({'name': new_name, 'debt': '0', 'is_creditor': True})
                app.save_data()
                self.refresh_list()
                pop.dismiss()

        btn_add.bind(on_release=on_add_new)
        content.add_widget(btn_add)
        content.add_widget(Widget(size_hint_y=None, height=10))
        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ"))
        content.add_widget(Widget(size_hint_y=None, height=350))
        scroll.add_widget(content)
        pop.open()

    def show_profit_correction_popup(self):
        app = App.get_running_app()
        if not app:
            return
        scroll = ScrollView()
        tot_debt, _, banner_deficit, current_profit = app.get_totals()
        content = BoxLayout(orientation='vertical', spacing=12, padding=[8, 15, 8, 15], size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        pop = TopMenuPopup(title="ЧИСТАЯ ПРИБЫЛЬ", content=scroll, size_hint=(0.95, 0.85))
        pop.title_size = '28sp'
        pop.title_color = [0.56, 0.9, 0.69, 1]

        # ── Карточка с текущей прибылью ──
        profit_card = BoxLayout(orientation='vertical', size_hint_y=None, height=195, padding=[15, 14, 15, 14])
        def _draw_profit_card(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.12, 0.28, 0.18, 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(16,16)]*4)
                Color(0.2, 0.65, 0.35, 0.3)
                RoundedRectangle(pos=(w.x+2, w.y+2), size=(w.width-4, w.height-4), radius=[(14,14)]*4)
        profit_card.bind(pos=_draw_profit_card, size=_draw_profit_card)
        lbl_subtitle = Label(text="[color=#AAAAAA]ТЕКУЩАЯ ПРИБЫЛЬ[/color]", markup=True, font_size='15sp',
                             halign='center', valign='bottom', size_hint_y=0.3)
        lbl_subtitle.bind(size=lambda s, v: setattr(s, 'text_size', v))
        if current_profit >= 0:
            profit_color = "#8FE6B0"
        else:
            profit_color = "#FF6B6B"
        lbl_profit_val = Label(
            text=f"[b][color={profit_color}]{format_num_simple(current_profit)} руб[/color][/b]",
            markup=True, font_size='36sp', halign='center', valign='middle', size_hint_y=0.7)
        lbl_profit_val.bind(size=lambda s, v: setattr(s, 'text_size', v))
        profit_card.add_widget(lbl_subtitle)
        profit_card.add_widget(lbl_profit_val)
        content.add_widget(profit_card)

        # ── Поле ввода ──
        lbl_edit = BgLabel(text="[b]ИЗМЕНИТЬ ЗНАЧЕНИЕ:[/b]", markup=True,
                         font_size='18sp', halign='center', valign='middle',
                         size_hint_y=None, height=50, radius=10)
        lbl_edit.bg_color = [0.18, 0.18, 0.22, 1]
        lbl_edit.color = (0.75, 0.85, 1, 1)
        lbl_edit.bind(size=lambda s, v: setattr(s, 'text_size', v))
        content.add_widget(lbl_edit)
        in_wrap = BoxLayout(orientation='horizontal', size_hint_y=None, height=108)
        in_wrap.add_widget(Widget(size_hint_x=0.18))
        in_profit = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), text=format_num_simple(current_profit), input_type='number',
                              input_filter='float', multiline=False, font_size='26sp',
                              halign='center', size_hint_x=0.64)
        def _center_input(inst, *a):
            top = max(6, (inst.height - inst.line_height) / 2 - 6)
            inst.padding = [10, top, 10, 4]
        in_profit.bind(height=_center_input, line_height=_center_input)
        in_wrap.add_widget(in_profit)
        in_wrap.add_widget(Widget(size_hint_x=0.18))
        content.add_widget(in_wrap)

        def save_profit(val):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            app.profit_correction = str(round(val - tot_debt + banner_deficit, 2))
            app.save_data(); self.refresh_list(); pop.dismiss()

        btn_save = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.15, 0.55, 0.35, 1),
                                 height=90, size_hint_y=None, bold=True, font_size='22sp')
        btn_save.bind(on_release=lambda x: save_profit(safe_float(in_profit.text)))
        content.add_widget(btn_save)

        # ── Разделитель ──
        content.add_widget(Widget(size_hint_y=None, height=15))
        sep_lbl = Label(text="[color=#555555]─────── СБРОС ───────[/color]", markup=True,
                        font_size='14sp', halign='center', size_hint_y=None, height=25)
        sep_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
        content.add_widget(sep_lbl)

        btn_zero = RoundedButton(text="ОБНУЛИТЬ ПРИБЫЛЬ", bg_color=(0.65, 0.25, 0.2, 1),
                                 height=100, size_hint_y=None, bold=True, font_size='20sp')
        btn_zero.bind(on_release=lambda x: save_profit(0.0))
        content.add_widget(btn_zero)

        content.add_widget(Widget(size_hint_y=None, height=50))

        btn_global_reset = RoundedButton(text="СБРОС ВСЕХ ДАННЫХ", bg_color=(0.45, 0.08, 0.08, 1),
                                         height=100, size_hint_y=None, bold=True, font_size='20sp')

        def confirm_global_reset(instance):
            p_conf = AppPopup(title="ВНИМАНИЕ! СБРОС ВСЕГО!", content=BoxLayout(orientation='vertical', spacing=20, padding=20), size_hint=(0.85, 0.5))
            btn_yes = RoundedButton(text="ДА, СБРОСИТЬ ВСЕ", bg_color=(0.8, 0.2, 0.2, 1), height=100, size_hint_y=None, bold=True)

            def on_yes_global(x):
                if getattr(p_conf, 'is_dismissing_flag', False): return
                p_conf.is_dismissing_flag = True
                for c in app.clients:
                    c.update({'debt': '0', 'zakupka_total': '0', 'history': []})
                app.profit_correction = '0'
                app.save_data()
                self.refresh_list()
                p_conf.dismiss()
                if not getattr(pop, 'is_dismissing_flag', False):
                    pop.is_dismissing_flag = True
                    pop.dismiss()

            btn_yes.bind(on_release=on_yes_global)
            p_conf.content.add_widget(Label(text="Вы уверены, что хотите обнулить\nдолги ВСЕХ клиентов, истории\nи всю чистую прибыль?", halign='center'))
            p_conf.content.add_widget(btn_yes)
            p_conf.content.add_widget(self.get_bottom_buttons(p_conf, cancel_text="ОТМЕНА"))
            p_conf.open()

        btn_global_reset.bind(on_release=confirm_global_reset)
        content.add_widget(btn_global_reset)

        content.add_widget(Widget(size_hint_y=None, height=25))
        bottom_profit = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=110, padding=[15, 0, 15, 0])
        btn_back_pr = RoundedButton(text="НАЗАД", bg_color=(1, 0.45, 0, 1), font_size='24sp', bold=True, size_hint_x=0.45)
        def _pr_back(x):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            pop.dismiss()
        btn_back_pr.bind(on_release=_pr_back)
        btn_close_pr = CancelButton(text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1), font_size='24sp', bold=True, size_hint_x=0.55)
        btn_close_pr.bind(on_release=_pr_back)
        bottom_profit.add_widget(btn_back_pr)
        bottom_profit.add_widget(btn_close_pr)
        content.add_widget(bottom_profit)
        content.add_widget(Widget(size_hint_y=None, height=350))
        scroll.add_widget(content); pop.open()

    def show_zakupka_menu(self, instance):
        content = BoxLayout(orientation='vertical', spacing=20, padding=20)
        pop = AppPopup(title="ЗАКУПКА БАНЕРОВ", content=content, size_hint=(0.9, 0.65))
        b_w = RoundedButton(text="БЕЛЫЙ БАНЕР", bg_color=(0.95, 0.95, 0.95, 1), color=(0,0,0,1), height=130, size_hint_y=None, font_size='24sp', bold=True)
        b_w.bind(on_release=lambda x: self.safe_transition(pop, self.show_zakupka_input_popup, "white", prev_cb=lambda p=None: self.show_zakupka_menu(instance)))
        b_b = RoundedButton(text="ЧЕРНЫЙ БАНЕР", bg_color=(0.1, 0.1, 0.1, 1), height=130, size_hint_y=None, font_size='24sp', bold=True)
        b_b.bind(on_release=lambda x: self.safe_transition(pop, self.show_zakupka_input_popup, "black", prev_cb=lambda p=None: self.show_zakupka_menu(instance)))
        content.add_widget(b_w); content.add_widget(b_b); content.add_widget(Widget())
        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ"))
        pop.open()

    def show_zakupka_input_popup(self, mode="white", prev_cb=None):
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=18, padding=20, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        pop = TopMenuPopup(title=f"ЗАКУПКА: {'БЕЛЫЙ' if mode == 'white' else 'ЧЕРНЫЙ'}", content=scroll, size_hint=(0.9, 0.72))
        in_sum = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="Введите сумму...", input_type='number', input_filter='float', multiline=False, font_size='28sp', halign='center', size_hint_y=None, height=110)
        # ширина и длина рулона (для остатков материала)
        roll_row = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=100)
        in_w = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="ширина, м", input_type='number', input_filter='float', multiline=False, font_size='22sp', halign='center')
        in_len = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="длина, м", input_type='number', input_filter='float', multiline=False, font_size='22sp', halign='center')
        roll_row.add_widget(in_w)
        roll_row.add_widget(in_len)
        lbl_roll = Label(text="[color=#9A9A9A]Рулон (для остатков) — можно оставить пустым[/color]", markup=True, font_size='14sp', size_hint_y=None, height=30, halign='center', valign='middle')
        lbl_roll.bind(size=lambda s, v: setattr(s, 'text_size', v))
        btn_save = RoundedButton(text="ДОБАВИТЬ В СУММУ", bg_color=(0.2, 0.6, 0.4, 1), height=110, size_hint_y=None, bold=True)

        def save_zakupka(instance):
            if getattr(pop, 'is_dismissing_flag', False):
                return
            app = App.get_running_app()
            if not app:
                return
            ok, message = purchase_banner(app, mode, in_sum.text, in_w.text, in_len.text)
            if not ok:
                self._stub_popup('ЗАКУПКА', message)
                return
            pop.is_dismissing_flag = True
            self.refresh_list()
            pop.dismiss()

        btn_save.bind(on_release=save_zakupka)
        content.add_widget(in_sum)
        content.add_widget(lbl_roll)
        content.add_widget(roll_row)
        content.add_widget(btn_save)
        content.add_widget(self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ"))
        content.add_widget(Widget(size_hint_y=None, height=350))
        scroll.add_widget(content); pop.open()

    def show_rolls_inventory(self, *args):
        app = App.get_running_app()
        if not app:
            return
        if not hasattr(app, 'rolls') or app.rolls is None:
            app.rolls = []
        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=14, size_hint_y=None, padding=[6, 10, 6, 10])
        grid.bind(minimum_height=grid.setter('height'))
        scroll.add_widget(grid)
        pop = TopMenuPopup(title="ОСТАТКИ МАТЕРИАЛА",
                           content=BoxLayout(orientation='vertical', spacing=12, padding=[10, 10, 10, 10]),
                           size_hint=(0.95, 0.9))
        pop.title_size = '19sp'
        pop.background_color = (0.043, 0.055, 0.08, 1)

        def rebuild():
            grid.clear_widgets()
            if not app.rolls:
                empty = Label(text="[color=#5A6472]Рулонов пока нет.\nДобавь при закупке или кнопкой ниже.[/color]",
                              markup=True, font_size='17sp', size_hint_y=None, height=140, halign='center', valign='middle')
                empty.bind(size=lambda s, v: setattr(s, 'text_size', v))
                grid.add_widget(empty)
            for ri, roll in enumerate(app.rolls):
                is_white = roll.get('color', 'white') == 'white'
                disp = "БЕЛЫЙ" if is_white else "ЧЁРНЫЙ"
                accent = (0.66, 0.3, 1.0) if is_white else (0.30, 0.55, 1.0)
                w = roll.get('width', '0')
                rem = format_num_simple(roll.get('remain', '0'))
                tot = format_num_simple(roll.get('total', '0'))
                text = f"[b][color=#FFFFFF]{disp}[/color][/b]  [color=#9A9A9A]{w} м[/color]   [b][color=#5FD39B]{rem} м[/color][/b] [color=#7A8494]/ {tot}[/color]"
                r = QuickDebtRow(name="", amount_text="", accent=accent)
                r.clear_widgets()
                lbl = Label(text=text, markup=True, font_size='20sp', halign='left', valign='middle')
                lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
                r.add_widget(lbl)
                r.bind(on_release=lambda x, i=ri: self._roll_edit_popup(i, pop))
                grid.add_widget(r)

        rebuild()
        pop._rebuild_rolls = rebuild

        btn_add = RoundedButton(text="+ ДОБАВИТЬ РУЛОН", bg_color=(0.15, 0.55, 0.9, 1),
                                font_size='27sp', bold=True, radius=30, size_hint_y=None, height=188)
        btn_add.bind(on_release=lambda x: self._roll_edit_popup(None, pop))
        # нижняя навигация — покрупнее, с воздухом между кнопками
        nav = BoxLayout(orientation='horizontal', spacing=16, size_hint_y=None, height=140, padding=[8, 0, 8, 0])
        btn_back = RoundedButton(text="НАЗАД", bg_color=(1, 0.45, 0, 1), font_size='24sp', bold=True, size_hint_x=0.45)
        btn_back.bind(on_release=lambda x: pop.dismiss())
        btn_close = CancelButton(text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1), font_size='24sp', bold=True, size_hint_x=0.55)
        btn_close.bind(on_release=lambda x: pop.dismiss())
        nav.add_widget(btn_back)
        nav.add_widget(btn_close)
        pop.content.add_widget(scroll)
        pop.content.add_widget(btn_add)
        pop.content.add_widget(Widget(size_hint_y=None, height=22))
        pop.content.add_widget(nav)
        pop.open()

    def _roll_edit_popup(self, ri, list_pop):
        app = App.get_running_app()
        if not app:
            return
        if not hasattr(app, 'rolls') or app.rolls is None:
            app.rolls = []
        is_new = ri is None
        roll = {} if is_new else app.rolls[ri]
        state = {'color': roll.get('color', 'white')}
        content = BoxLayout(orientation='vertical', spacing=18, padding=[16, 14, 16, 14])
        pop = TopMenuPopup(title=("НОВЫЙ РУЛОН" if is_new else "РУЛОН"), content=content, size_hint=(0.94, 0.86))
        pop.background_color = (0.043, 0.055, 0.08, 1)

        # выбор цвета
        color_row = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=100)
        btn_white = RoundedButton(text="БЕЛЫЙ", bg_color=(0.95, 0.95, 0.95, 1), color=(0, 0, 0, 1), bold=True, radius=20)
        btn_black = RoundedButton(text="ЧЁРНЫЙ", bg_color=(0.1, 0.1, 0.1, 1), color=(1, 1, 1, 1), bold=True, radius=20)

        def paint_colors():
            if state['color'] == 'white':
                btn_white.bg_color = [0.2, 0.7, 0.3, 1]; btn_white.color = (1, 1, 1, 1)
                btn_black.bg_color = [0.1, 0.1, 0.1, 1]; btn_black.color = (1, 1, 1, 1)
            else:
                btn_black.bg_color = [0.2, 0.7, 0.3, 1]; btn_black.color = (1, 1, 1, 1)
                btn_white.bg_color = [0.95, 0.95, 0.95, 1]; btn_white.color = (0, 0, 0, 1)
        btn_white.bind(on_release=lambda x: (state.update(color='white'), paint_colors()))
        btn_black.bind(on_release=lambda x: (state.update(color='black'), paint_colors()))
        paint_colors()
        color_row.add_widget(btn_white)
        color_row.add_widget(btn_black)
        content.add_widget(Label(text="[b]ЦВЕТ[/b]", markup=True, font_size='15sp', color=(0.6, 0.65, 0.72, 1), size_hint_y=None, height=30))
        content.add_widget(color_row)

        content.add_widget(Label(text="[b]ШИРИНА, м[/b]", markup=True, font_size='15sp', color=(0.4, 0.8, 1, 1), size_hint_y=None, height=30))
        in_w = _dark_input(text=str(roll.get('width', '')), hint_text="напр. 3.2", input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_w, (0.4, 0.8, 1, 1), 150, 0.6))

        content.add_widget(Label(text="[b]ВСЕГО, м[/b]", markup=True, font_size='15sp', color=(0.55, 0.6, 0.7, 1), size_hint_y=None, height=30))
        in_tot = _dark_input(text=format_num_simple(roll.get('total', '0')) if not is_new else "", hint_text="длина всего", input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_tot, (0.45, 0.5, 0.6, 1), 140, 0.6))

        content.add_widget(Label(text="[b]ОСТАТОК, м[/b]", markup=True, font_size='15sp', color=(0.41, 0.94, 0.68, 1), size_hint_y=None, height=30))
        in_rem = _dark_input(text=format_num_simple(roll.get('remain', '0')) if not is_new else "", hint_text="сколько осталось", input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_rem, (0.41, 0.94, 0.68, 1), 140, 0.6))

        content.add_widget(Label(text="СПИСАТЬ РАСХОД (ОТНЯТЬ ОТ ОСТАТКА)", font_size='13sp', color=(0.55, 0.6, 0.66, 1), size_hint_y=None, height=28))
        in_use = _dark_input(hint_text="метры расхода...", input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_use, (1.0, 0.72, 0.3, 1), 140, 0.6))

        def do_save(x):
            if getattr(pop, 'is_dismissing_flag', False):
                return
            pop.is_dismissing_flag = True
            use_val = safe_float(in_use.text)
            rem_val = safe_float(in_rem.text)
            if use_val > 0:
                rem_val = max(0.0, rem_val - use_val)
            data = {
                'color': state['color'],
                'width': (in_w.text.strip() or '0'),
                'total': format_num_simple(in_tot.text or '0'),
                'remain': format_num_simple(rem_val)
            }
            if is_new:
                app.rolls.append(data)
            else:
                app.rolls[ri] = data
            app.save_data()
            self.refresh_list()
            pop.dismiss()
            try:
                if list_pop and getattr(list_pop, '_rebuild_rolls', None):
                    list_pop._rebuild_rolls()
            except Exception:
                pass

        btn_save = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.2, 0.62, 0.42, 1), bold=True, radius=22, font_size='21sp', size_hint_y=None, height=104)
        btn_save.bind(on_release=do_save)
        content.add_widget(btn_save)

        row = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=100)
        btn_back = RoundedButton(text="НАЗАД", bg_color=(1, 0.45, 0, 1), bold=True, radius=22, font_size='20sp', size_hint_x=0.45)
        btn_back.bind(on_release=lambda x: pop.dismiss())
        if is_new:
            btn_close = CancelButton(text="ОТМЕНА", bg_color=(0.6, 0.2, 0.2, 1), bold=True, font_size='20sp', size_hint_x=0.55)
            btn_close.bind(on_release=lambda x: pop.dismiss())
        else:
            btn_close = RoundedButton(text="УДАЛИТЬ", bg_color=(0.8, 0.3, 0.3, 1), bold=True, radius=22, font_size='20sp', size_hint_x=0.55)
            def do_delete(x):
                if getattr(pop, 'is_dismissing_flag', False):
                    return
                pop.is_dismissing_flag = True
                try:
                    app.rolls.pop(ri)
                except Exception:
                    pass
                app.save_data()
                self.refresh_list()
                pop.dismiss()
                try:
                    if list_pop and getattr(list_pop, '_rebuild_rolls', None):
                        list_pop._rebuild_rolls()
                except Exception:
                    pass
            btn_close.bind(on_release=do_delete)
        row.add_widget(btn_back)
        row.add_widget(btn_close)
        content.add_widget(row)
        content.add_widget(Widget(size_hint_y=1))
        pop.open()

    def on_client_click(self, idx):
        app = App.get_running_app()
        if not app:
            return
        c = app.clients[idx]
        if c.get('is_creditor'):
            self.show_malevich_main_menu(idx)
        else:
            self.show_client_choice_menu(idx)

    def show_malevich_main_menu(self, idx):
        app = App.get_running_app()
        if not app:
            return
        c_name = app.clients[idx].get('name', 'КРЕДИТОР').upper()
        content = BoxLayout(orientation='vertical', spacing=10, padding=15)
        pop = AppPopup(title=f"{c_name} -> ЧТО ДЕЛАЕМ?", content=content, size_hint=(0.9, 0.6))
        b_print = RoundedButton(text="ПЕЧАТЬ ДЛЯ КЛИЕНТА", bg_color=(0.1, 0.5, 0.9, 1), height=110, size_hint_y=None, font_size='20sp', bold=True)
        b_print.bind(on_release=lambda x: self.safe_transition(pop, self.show_malevich_client_select, idx, prev_cb=lambda p=None: self.show_malevich_main_menu(idx)))
        b_debt = RoundedButton(text="НАСТРОЙКИ ДОЛГА", bg_color=(0.4, 0.4, 0.4, 1), height=110, size_hint_y=None, font_size='20sp', bold=True)
        b_debt.bind(on_release=lambda x: self.safe_transition(pop, self.show_malevich_menu, idx, prev_cb=lambda p=None: self.show_malevich_main_menu(idx)))
        content.add_widget(b_print); content.add_widget(b_debt); content.add_widget(Widget())
        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ"))
        pop.open()

    def show_malevich_client_select(self, creditor_idx, prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        scroll = ScrollView()
        list_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        list_layout.bind(minimum_height=list_layout.setter('height'))
        pop = TopMenuPopup(title="ВЫБЕРИТЕ КЛИЕНТА", content=scroll, size_hint=(0.95, 0.8))
        m_indices, o_idx, b_idx, c_idx = app.get_special_clients()
        special = m_indices + [i for i in (b_idx, c_idx, o_idx) if i is not None]
        ordered = [i for i in range(len(app.clients)) if i not in special]
        for i in ordered:
            btn = RoundedButton(text=app.clients[i].get('name', '').upper(), bg_color=(0.15, 0.6, 0.3, 1), height=100, size_hint_y=None, font_size='22sp', bold=True)
            btn.bind(on_release=lambda x, i_idx=i: self.safe_transition(pop, self.show_client_choice_menu, i_idx, creditor_idx=creditor_idx, prev_cb=lambda p_cb=prev_cb: self.show_malevich_client_select(creditor_idx, p_cb)))
            list_layout.add_widget(btn)
        list_layout.add_widget(Widget(size_hint_y=None, height=20))
        list_layout.add_widget(self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ"))
        scroll.add_widget(list_layout); pop.open()

    def cr_calc_row(self, lbl_t, hnt):
        r = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, spacing=10)
        inp = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text=hnt, input_type='number', input_filter='float', multiline=False, font_size='24sp', halign='center', size_hint_x=0.45)
        r.add_widget(Label(text=lbl_t, size_hint_x=0.55, font_size='20sp')); r.add_widget(inp)
        return r, inp

    def _calc_section(self, title, accent=(0.3, 0.5, 0.75), title_color="#FFFFFF"):
        """Карточка-секция с центрированным заголовком в округлой рамке."""
        card = BoxLayout(orientation='vertical', size_hint_y=None, padding=[10, 10, 10, 12], spacing=10)
        card.bind(minimum_height=card.setter('height'))
        def _draw(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(accent[0], accent[1], accent[2], 0.5)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(16, 16)] * 4)
                Color(0.11, 0.11, 0.14, 1)
                RoundedRectangle(pos=(w.x + 2, w.y + 2), size=(w.width - 4, w.height - 4), radius=[(14, 14)] * 4)
        card.bind(pos=_draw, size=_draw)
        hc = (min(accent[0]*1.3, 1), min(accent[1]*1.3, 1), min(accent[2]*1.3, 1))
        hdr = Label(text=f"[b]{title}[/b]", markup=True, font_size='18sp',
                    color=(hc[0], hc[1], hc[2], 1),
                    halign='center', valign='middle', size_hint_y=None, height=60)
        hdr.bind(size=lambda s, v: setattr(s, 'text_size', v))
        def _draw_hdr(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(hc[0], hc[1], hc[2], 0.9)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(12, 12)] * 4)
                Color(0.09, 0.09, 0.12, 1)
                RoundedRectangle(pos=(w.x + 2, w.y + 2), size=(w.width - 4, w.height - 4), radius=[(10, 10)] * 4)
        hdr.bind(pos=_draw_hdr, size=_draw_hdr)
        card.add_widget(hdr)
        body = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8)
        body.bind(minimum_height=body.setter('height'))
        card.add_widget(body)
        return card, body

    def _labeled_field(self, label_text, hint="0.0", init=""):
        """Поле ввода: подпись сверху, рабочее поле в скруглённой рамке-обёртке."""
        box = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=150)
        lbl = Label(text=label_text, font_size='13sp', color=(0.8, 0.82, 0.9, 1), bold=True, size_hint_y=None, height=36, halign='center', valign='middle', shorten=False)
        lbl.bind(size=lambda s, v: setattr(s, 'text_size', (None, v[1])))
        # обёртка рисует скруглённую рамку, поле внутри — обычное рабочее
        wrap = BoxLayout(size_hint_y=None, height=104, padding=[4, 4, 4, 4])
        def _draw_wrap(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.4, 0.55, 0.85, 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(14, 14)] * 4)
                Color(0.95, 0.95, 0.97, 1)
                RoundedRectangle(pos=(w.x + 3, w.y + 3), size=(w.width - 6, w.height - 6), radius=[(11, 11)] * 4)
        wrap.bind(pos=_draw_wrap, size=_draw_wrap)
        inp = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text=hint, text=init, input_type='number', input_filter='float',
                        multiline=False, font_size='26sp', halign='center')
        def _vcenter(inst, *a):
            lh = inst.line_height if inst.line_height else 30
            pad_top = max(4, (inst.height - lh) / 2.0)
            inst.padding = [6, pad_top, 6, 4]
        inp.bind(height=_vcenter, line_height=_vcenter, size=_vcenter)

        def _sel_all(inst, val):
            if val:
                from kivy.clock import Clock as _Ck
                _Ck.schedule_once(lambda dt: inst.select_all(), 0.05)
        inp.bind(focus=_sel_all)
        wrap.add_widget(inp)
        box.add_widget(lbl)
        box.add_widget(wrap)
        return box, inp

    def open_quick_add_creditor(self, parent_pop, client_idx):
        content = BoxLayout(orientation='vertical', spacing=15, padding=15)
        pop = TopMenuPopup(title="НОВЫЙ КРЕДИТОР", content=content, size_hint=(0.85, 0.5))
        in_n = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="Имя (напр. ОЛЕГ)...", font_size='22sp', size_hint_y=None, height=90, multiline=False)

        def save_creditor(x):
            name = in_n.text.strip()
            if name:
                if getattr(pop, 'is_dismissing_flag', False): return
                pop.is_dismissing_flag = True
                app = App.get_running_app()
                if not app:
                    return
                app.clients.append({'name': name, 'debt': '0', 'is_creditor': True})
                app.save_data()
                self.refresh_list()
                pop.dismiss()
                self.safe_transition(parent_pop, self.show_client_choice_menu, client_idx, creditor_idx="unselected")

        btn_save = RoundedButton(text="ДОБАВИТЬ", bg_color=(0.2, 0.6, 0.4, 1), height=90, size_hint_y=None, bold=True)
        btn_save.bind(on_release=save_creditor)
        content.add_widget(in_n)
        content.add_widget(btn_save)
        content.add_widget(Widget())
        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ОТМЕНА"))
        pop.open()

    def show_client_choice_menu(self, idx, creditor_idx="unselected", prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        c_name = app.clients[idx].get('name', '').upper()
        content = BoxLayout(orientation='vertical', spacing=12, padding=15)
        pop = TopMenuPopup(title=c_name, content=content, size_hint=(0.95, 0.92))
        state = {'creditor_idx': creditor_idx}
        top_box = BoxLayout(orientation='vertical', spacing=15, size_hint_y=None, height=275)
        b_baner = RoundedButton(text="БАНЕР", height=130, size_hint_y=None, font_size='28sp', bold=True)
        b_plenka = RoundedButton(text="ПЛЕНКА", height=130, size_hint_y=None, font_size='28sp', bold=True)
        top_box.add_widget(b_baner)
        top_box.add_widget(b_plenka)
        content.add_widget(top_box)
        source_box = BoxLayout(orientation='vertical', spacing=0, size_hint_y=None, height=170)
        def _draw_arrows_fn(w, direction):
            w.canvas.clear()
            if w.height < 5:
                return
            cx = w.x + w.width / 2.0
            cy = w.y + w.height / 2.0
            s = min(w.width * 0.20, 42)
            with w.canvas:
                Color(0.15, 0.45, 0.95, 1)
                if direction == 'down':
                    Mesh(vertices=[cx-s*1.5,cy+s*0.9,0,0, cx+s*1.5,cy+s*0.9,0,0, cx,cy+s*0.1,0,0], indices=[0,1,2], mode='triangle_fan')
                    Mesh(vertices=[cx-s*1.5,cy+s*0.0,0,0, cx+s*1.5,cy+s*0.0,0,0, cx,cy-s*0.8,0,0], indices=[0,1,2], mode='triangle_fan')
                else:
                    Mesh(vertices=[cx-s*1.5,cy-s*0.1,0,0, cx+s*1.5,cy-s*0.1,0,0, cx,cy+s*0.7,0,0], indices=[0,1,2], mode='triangle_fan')
                    Mesh(vertices=[cx-s*1.5,cy-s*0.9,0,0, cx+s*1.5,cy-s*0.9,0,0, cx,cy-s*0.1,0,0], indices=[0,1,2], mode='triangle_fan')
        arrow_up_w = Widget(size_hint_y=None, height=0, opacity=0)
        arrow_up_w.bind(pos=lambda w,*a: _draw_arrows_fn(w,'up'), size=lambda w,*a: _draw_arrows_fn(w,'up'))
        source_frame = BoxLayout(size_hint_y=None, height=80, padding=[0,0,0,0])
        source_frame._show_border = False
        def _draw_frame(w, *a):
            w.canvas.before.clear()
            x, y, wd, h = w.x, w.y, w.width, w.height
            if wd < 4 or h < 4:
                return
            r = 16
            with w.canvas.before:
                if getattr(w, '_show_border', False):
                    Color(0.15, 0.45, 0.95, 1)
                    RoundedRectangle(pos=(x,y), size=(wd,h), radius=[(r,r)]*4)
                    Color(0.12, 0.12, 0.14, 1)
                    RoundedRectangle(pos=(x+4,y+4), size=(wd-8,h-8), radius=[(r-2,r-2)]*4)
        source_frame.bind(pos=_draw_frame, size=_draw_frame)
        lbl_source = BgLabel(text="", font_size='22sp', markup=True, halign='center', valign='middle', radius=14)
        lbl_source.bind(size=lambda s,v: setattr(s,'text_size',v))
        source_frame.add_widget(lbl_source)
        arrow_down_w = Widget(size_hint_y=None, height=80)
        arrow_down_w.bind(pos=lambda w,*a: _draw_arrows_fn(w,'down'), size=lambda w,*a: _draw_arrows_fn(w,'down'))
        source_box.add_widget(arrow_up_w)
        source_box.add_widget(source_frame)
        source_box.add_widget(arrow_down_w)
        content.add_widget(source_box)
        scroll = ScrollView()
        creditors_grid = GridLayout(cols=1, spacing=15, size_hint_y=None)
        creditors_grid.bind(minimum_height=creditors_grid.setter('height'))
        creditor_btns = []
        anim_warning = Animation(bg_color=[0.4, 0.24, 0.06, 1], duration=1.2) + Animation(bg_color=[0.25, 0.14, 0.03, 1], duration=1.2)
        anim_warning.repeat = True
        anim_cred_btn = Animation(bg_color=[0.32, 0.2, 0.48, 1], duration=1.4) + Animation(bg_color=[0.22, 0.13, 0.36, 1], duration=1.4)
        anim_cred_btn.repeat = True
        anim_baner = Animation(bg_color=[0.12, 0.48, 0.88, 1], duration=0.8) + Animation(bg_color=[0.06, 0.28, 0.55, 1], duration=0.8)
        anim_baner.repeat = True
        anim_plenka = Animation(bg_color=[0.12, 0.55, 0.28, 1], duration=0.8) + Animation(bg_color=[0.06, 0.35, 0.18, 1], duration=0.8)
        anim_plenka.repeat = True
        anim_arrow = Animation(opacity=0.25, duration=0.7) + Animation(opacity=1.0, duration=0.7)
        anim_arrow.repeat = True

        def update_selection():
            is_selected = state['creditor_idx'] != "unselected"
            if is_selected:
                Animation.cancel_all(lbl_source)
                Animation.cancel_all(arrow_down_w)
                Animation.cancel_all(arrow_up_w)
                source_frame._show_border = False
                _draw_frame(source_frame)
                arrow_down_w.opacity = 0
                arrow_down_w.height = 0
                arrow_up_w.height = 65
                arrow_up_w.opacity = 1
                anim_arrow.start(arrow_up_w)
                source_box.height = 145
                lbl_source.bg_color = [0.06, 0.2, 0.1, 1]
                if state['creditor_idx'] is None:
                    cr_disp = "СВОЙ РУЛОН"
                else:
                    cr_disp = app.clients[state['creditor_idx']].get('name', '').upper()
                lbl_source.text = f"[color=#8FE6B0][b]В ДОЛГ У: {cr_disp}[/b][/color]"
                b_baner.color = (1, 1, 1, 1)
                b_plenka.color = (1, 1, 1, 1)
                anim_baner.start(b_baner)
                anim_plenka.start(b_plenka)
            else:
                Animation.cancel_all(b_baner)
                Animation.cancel_all(b_plenka)
                Animation.cancel_all(arrow_down_w)
                Animation.cancel_all(arrow_up_w)
                b_baner.bg_color = [0.1, 0.18, 0.32, 1]
                b_plenka.bg_color = [0.08, 0.2, 0.14, 1]
                b_baner.color = (0.4, 0.55, 0.78, 1)
                b_plenka.color = (0.35, 0.6, 0.45, 1)
                source_frame._show_border = True
                _draw_frame(source_frame)
                arrow_up_w.height = 0
                arrow_up_w.opacity = 0
                arrow_down_w.height = 80
                arrow_down_w.opacity = 1
                source_box.height = 170
                _draw_arrows_fn(arrow_down_w, 'down')
                anim_arrow.start(arrow_down_w)
                lbl_source.bg_color = [0, 0, 0, 0]
                lbl_source.text = "[color=#FFFFFF][b]ИСТОЧНИК ПЕЧАТИ[/b][/color]"
            for b, c_idx in creditor_btns:
                Animation.cancel_all(b)
                if c_idx is None:
                    if is_selected:
                        b.height = 110
                        b.opacity = 1
                    else:
                        b.height = 0
                        b.opacity = 0
                if state['creditor_idx'] == c_idx:
                    b.bg_color = [0.2, 0.7, 0.2, 1]
                    b.text = f"[b]{b.base_text}[/b]  [size=14sp](выбрано)[/size]"
                else:
                    if not is_selected:
                        b.bg_color = [0.28, 0.18, 0.42, 1]
                    else:
                        b.bg_color = [0.2, 0.2, 0.26, 1]
                    b.text = f"[b]{b.base_text}[/b]"
            if is_selected:
                btn_add.height = 0
                btn_add.opacity = 0
                spacer_add.height = 0
                mid_arrow_w.height = 55
                mid_arrow_w.opacity = 1
                anim_arrow.start(mid_arrow_w)
            else:
                btn_add.height = 100
                btn_add.opacity = 1
                spacer_add.height = 25
                Animation.cancel_all(mid_arrow_w)
                mid_arrow_w.height = 0
                mid_arrow_w.opacity = 0

        def on_creditor_select(instance, c_idx):
            state['creditor_idx'] = c_idx
            update_selection()

        m_indices = [i for i, c in enumerate(app.clients) if c.get('is_creditor')]
        for i in m_indices:
            name = app.clients[i].get('name', '').upper()
            c_box = BoxLayout(orientation='horizontal', spacing=8, size_hint_y=None, height=110)
            btn_c = RoundedButton(markup=True, size_hint_x=0.75, font_size='22sp')
            btn_c.base_text = name
            btn_c.bind(on_release=lambda x, c_idx=i: on_creditor_select(x, c_idx))
            creditor_btns.append((btn_c, i))
            btn_edit = EditButton(text="", bg_color=(0.72, 0.53, 0.13, 1), size_hint_x=0.25, radius=12)
            def do_edit(x, c_idx=i):
                if getattr(pop, 'is_dismissing_flag', False): return
                pop.is_dismissing_flag = True
                pop.dismiss()
                Clock.schedule_once(lambda dt: self.show_creditor_edit_popup(c_idx), 0.15)
            btn_edit.bind(on_release=do_edit)
            c_box.add_widget(btn_c)
            c_box.add_widget(btn_edit)
            creditors_grid.add_widget(c_box)

        mid_arrow_w = Widget(size_hint_y=None, height=0, opacity=0)
        mid_arrow_w.bind(pos=lambda w,*a: _draw_arrows_fn(w, 'down'), size=lambda w,*a: _draw_arrows_fn(w, 'down'))
        creditors_grid.add_widget(mid_arrow_w)

        btn_svoy = RoundedButton(markup=True, height=0, size_hint_y=None, font_size='22sp', opacity=0)
        btn_svoy.base_text = "СВОЙ РУЛОН"
        btn_svoy.bind(on_release=lambda x: on_creditor_select(x, None))
        creditor_btns.append((btn_svoy, None))
        creditors_grid.add_widget(btn_svoy)

        spacer_add = Widget(size_hint_y=None, height=25)
        creditors_grid.add_widget(spacer_add)

        btn_add = RoundedButton(text="+ ДОБАВИТЬ ИМЯ", bg_color=(0.7, 0.5, 0.1, 1), height=100, size_hint_y=None, bold=True, font_size='20sp')
        def on_add_click(x):
            Animation.cancel_all(lbl_source); Animation.cancel_all(b_baner); Animation.cancel_all(b_plenka)
            for b, _ in creditor_btns: Animation.cancel_all(b)
            self.open_quick_add_creditor(pop, idx)
        btn_add.bind(on_release=on_add_click)
        creditors_grid.add_widget(btn_add)

        update_selection()
        scroll.add_widget(creditors_grid)
        content.add_widget(scroll)
        bottom_row = BoxLayout(orientation='horizontal', spacing=12, size_hint_y=None, height=100, padding=[25, 0, 25, 0])
        btn_back_nav = RoundedButton(text="НАЗАД", bg_color=(1, 0.45, 0, 1), font_size='22sp', bold=True, size_hint_x=0.45)
        def _do_back_nav(x):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            Animation.cancel_all(lbl_source); Animation.cancel_all(b_baner); Animation.cancel_all(b_plenka)
            for b, _ in creditor_btns: Animation.cancel_all(b)
            pop.dismiss()
            if prev_cb: Clock.schedule_once(lambda dt: prev_cb(), 0.15)
        btn_back_nav.bind(on_release=_do_back_nav)
        btn_close_nav = CancelButton(text="ЗАКРЫТЬ", bg_color=(0.6, 0.2, 0.2, 1), font_size='22sp', bold=True, size_hint_x=0.55)
        def _do_close_nav(x):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            Animation.cancel_all(lbl_source); Animation.cancel_all(b_baner); Animation.cancel_all(b_plenka)
            for b, _ in creditor_btns: Animation.cancel_all(b)
            pop.dismiss()
        btn_close_nav.bind(on_release=_do_close_nav)
        bottom_row.add_widget(btn_back_nav)
        bottom_row.add_widget(btn_close_nav)
        content.add_widget(bottom_row)

        def on_baner_click(x):
            if state['creditor_idx'] == "unselected": return
            self.safe_transition(pop, self.show_banner_color_menu, idx, via_malevich=(state['creditor_idx'] is not None), creditor_idx=state['creditor_idx'], prev_cb=lambda p=None: self.show_client_choice_menu(idx, creditor_idx=state['creditor_idx'], prev_cb=p))

        def on_plenka_click(x):
            if state['creditor_idx'] == "unselected": return
            self.safe_transition(pop, self.show_price_popup, idx, mode="plenka", via_malevich=(state['creditor_idx'] is not None), creditor_idx=state['creditor_idx'], prev_cb=lambda p=None: self.show_client_choice_menu(idx, creditor_idx=state['creditor_idx'], prev_cb=p))

        b_baner.bind(on_release=on_baner_click)
        b_plenka.bind(on_release=on_plenka_click)

        def stop_animations(*args):
            Animation.cancel_all(lbl_source)
            Animation.cancel_all(arrow_up_w)
            Animation.cancel_all(arrow_down_w)
            Animation.cancel_all(mid_arrow_w)
            Animation.cancel_all(b_baner)
            Animation.cancel_all(b_plenka)
            for b, _ in creditor_btns:
                Animation.cancel_all(b)
        pop.bind(on_dismiss=stop_animations)
        pop.open()

    def show_banner_color_menu(self, idx, via_malevich=False, creditor_idx=None, prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        c_name = app.clients[idx].get('name', '').upper()
        cr_name = app.clients[creditor_idx].get('name', '').upper() if creditor_idx is not None else "МАЛЕВИЧ"
        pop = AppPopup(title=f"{cr_name} -> {c_name} -> БАНЕР" if via_malevich else f"{c_name} -> БАНЕР", content=BoxLayout(orientation='vertical', spacing=10, padding=15), size_hint=(0.9, 0.6))
        b_w = RoundedButton(text="БЕЛЫЙ", bg_color=(0.95, 0.95, 0.95, 1), color=(0,0,0,1), height=110, size_hint_y=None, font_size='20sp', bold=True)
        b_w.bind(on_release=lambda x: self.safe_transition(pop, self.show_price_popup, idx, mode="banner_white", via_malevich=via_malevich, creditor_idx=creditor_idx, prev_cb=lambda p=prev_cb: self.show_banner_color_menu(idx, via_malevich, creditor_idx, p)))
        b_b = RoundedButton(text="ЧЕРНЫЙ", bg_color=(0.1, 0.1, 0.1, 1), color=(1,1,1,1), height=110, size_hint_y=None, font_size='20sp', bold=True)
        b_b.bind(on_release=lambda x: self.safe_transition(pop, self.show_price_popup, idx, mode="banner_black", via_malevich=via_malevich, creditor_idx=creditor_idx, prev_cb=lambda p=prev_cb: self.show_banner_color_menu(idx, via_malevich, creditor_idx, p)))
        for w in (b_w, b_b, Widget(), self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ")): pop.content.add_widget(w)
        pop.open()

    def show_price_popup(self, idx, mode="banner_white", via_malevich=False, creditor_idx=None, prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        scroll = ScrollView()
        self.price_popup_content = BoxLayout(orientation='vertical', spacing=15, padding=20, size_hint_y=None)
        self.price_popup_content.bind(minimum_height=self.price_popup_content.setter('height'))
        self.price_grid = GridLayout(cols=2, spacing=12, size_hint_y=None, height=220)
        self.in_p = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), text=str(app.prices[0] if "banner" in mode else app.plenka_prices[0]), hint_text="Цена...", input_type='number', input_filter='float', multiline=False, font_size='32sp', halign='center', size_hint_y=None, height=110)
        self.build_price_grid(mode)
        titles = {"banner_white": "ВЫБОР ЦЕНЫ (БЕЛЫЙ БАНЕР)", "banner_black": "ВЫБОР ЦЕНЫ (ЧЕРНЫЙ БАНЕР)", "malevich_banner": "МАЛЕВИЧ: ВЫБОР ЦЕНЫ БАНЕРА", "malevich_plenka_gloss": "МАЛЕВИЧ: ПЛЕНКА ГЛЯНЕЦ", "malevich_plenka_matte": "МАЛЕВИЧ: ПЛЕНКА МАТОВАЯ"}
        pop = AppPopup(title=titles.get(mode, "ВЫБОР ЦЕНЫ (ПЛЕНКА)"), content=scroll, size_hint=(0.9, 0.85))
        btn_next = RoundedButton(text="ДАЛЕЕ >>>", bg_color=(0.2, 0.65, 0.42, 1), height=135, size_hint_y=None, bold=True, font_size='26sp')

        def on_next(instance):
            if self.in_p.text.strip():
                self.safe_transition(pop, self.show_simple_calc, idx, safe_float(self.in_p.text), mode=mode, via_malevich=via_malevich, creditor_idx=creditor_idx, prev_cb=lambda p=prev_cb: self.show_price_popup(idx, mode, via_malevich, creditor_idx, p))

        btn_next.bind(on_release=on_next)
        _price_hint = Label(text="[b][color=#FFD54F]ВЫБРАННАЯ ЦЕНА\n(можно изменить вручную)[/color][/b]", markup=True, size_hint_y=None, height=60, font_size='18sp', halign='center', valign='middle')
        _price_hint.bind(size=lambda s, v: setattr(s, 'text_size', v))
        for w in (self.price_grid, _price_hint, self.in_p, Widget(size_hint_y=None, height=18), btn_next, Widget(size_hint_y=None, height=10), self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ"), Label(text="* Зажмите кнопку цены подольше,\nчтобы изменить её шаблон", color=(0.7,0.7,0.7,1), font_size='14sp', halign='center', size_hint_y=None, height=50), Widget(size_hint_y=None, height=400)): self.price_popup_content.add_widget(w)
        scroll.add_widget(self.price_popup_content); pop.open()

    def build_price_grid(self, mode):
        self.price_grid.clear_widgets()
        app = App.get_running_app()
        if not app:
            return
        prices = app.prices if "banner" in mode else app.plenka_prices
        bg = (0.1, 0.45, 0.85, 1) if mode == "malevich_banner" else (0.1, 0.4, 0.7, 1) if mode == "banner_white" else (0.2, 0.2, 0.2, 1) if "banner" in mode else (0.15, 0.6, 0.35, 1) if "gloss" in mode else (0.11, 0.48, 0.28, 1) if "matte" in mode else (0.12, 0.5, 0.3, 1)
        for i, p in enumerate(prices):
            btn = RoundedButton(text=str(p), bg_color=bg, font_size='24sp', bold=True)
            btn.bind(on_release=lambda x, val=p: setattr(self.in_p, 'text', str(val)), on_long_press=lambda x, b_idx=i, c_val=p: self.open_quick_price_edit(b_idx, c_val, mode))
            self.price_grid.add_widget(btn)

    def open_quick_price_edit(self, btn_idx, current_value, mode):
        app = App.get_running_app()
        if not app:
            return
        content = BoxLayout(orientation='vertical', padding=20, spacing=25)
        pop = TopMenuPopup(title=f"ИЗМЕНИТЬ ЦЕНУ {btn_idx + 1}", content=content, size_hint=(0.9, 0.58))
        ti = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), text=str(current_value), input_type='number', input_filter='int', multiline=False, font_size='26sp', halign='center', size_hint_y=None, height=110, padding=[10, 25, 10, 10])

        def save_price(x):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            (app.prices if "banner" in mode else app.plenka_prices)[btn_idx] = ti.text.strip() or "0"
            app.save_data(); self.build_price_grid(mode); pop.dismiss()

        btn_save = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.2, 0.6, 0.4, 1), size_hint_y=None, height=100, font_size='20sp', bold=True)
        btn_save.bind(on_release=save_price)
        for w in (Label(text="Введите новое значение кнопки:", font_size='18sp'), ti, Widget(size_hint_y=None, height=5), btn_save, self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ")): content.add_widget(w)
        pop.open()

    def show_simple_calc(self, idx, price, mode="banner_white", via_malevich=False, creditor_idx=None, prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        calc_client = app.clients[idx]
        calc_creditor = app.clients[creditor_idx] if creditor_idx is not None else None

        def resolve_targets():
            nonlocal idx, creditor_idx
            targets = [i for i, c in enumerate(app.clients) if c is calc_client]
            creditors = [i for i, c in enumerate(app.clients) if c is calc_creditor]
            if len(targets) != 1 or (calc_creditor is not None and len(creditors) != 1):
                self._stub_popup('ЗАКАЗ', 'Клиент или исполнитель удалён. Откройте расчёт заново')
                return False
            idx = targets[0]
            creditor_idx = creditors[0] if creditors else None
            return True

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=15, padding=20, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        c_name = app.clients[idx].get('name', '').upper()
        cr_name = app.clients[creditor_idx].get('name', '').upper() if creditor_idx is not None else "КРЕДИТОРА"
        self.current_calc_price, self.current_calc_mode = float(price), mode
        descs = {"banner_white": "БЕЛЫЙ БАНЕР", "banner_black": "ЧЕРНЫЙ БАНЕР", "malevich_banner": "БАНЕР", "plenka_gloss": "ПЛЕНКА ГЛЯНЕЦ", "plenka_matte": "ПЛЕНКА МАТОВАЯ"}
        badges = {"banner_white": "Б-БАН", "banner_black": "Ч-БАН", "malevich_banner": "БАН", "plenka_gloss": "П-ГЛ", "plenka_matte": "П-МТ"}
        bgs = {"banner_white": (0.05, 0.3, 0.65, 1), "banner_black": (0.15, 0.15, 0.15, 1), "malevich_banner": (0.1, 0.45, 0.85, 1), "plenka_gloss": (0.15, 0.6, 0.35, 1), "plenka_matte": (0.11, 0.48, 0.28, 1)}
        _is_creditor_client = app.clients[idx].get('is_creditor')
        _show_print_cost = via_malevich and not _is_creditor_client

        # ── СЕКЦИЯ: КЛИЕНТ / ПРИНТЕР (обе строки одинаковым шрифтом) ──
        card_client = BoxLayout(orientation='vertical', size_hint_y=None, padding=[14, 26, 14, 26], spacing=18)
        card_client.bind(minimum_height=card_client.setter('height'))
        def _draw_client(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.3, 0.5, 0.8, 0.55)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(18, 18)] * 4)
                Color(0.11, 0.11, 0.14, 1)
                RoundedRectangle(pos=(w.x + 3, w.y + 3), size=(w.width - 6, w.height - 6), radius=[(15, 15)] * 4)
        card_client.bind(pos=_draw_client, size=_draw_client)
        lbl_cl1 = Label(text=f"[size=16sp][color=#7FB0FF]КЛИЕНТ:[/color][/size]  [size=21sp][b][color=#FFFFFF]{c_name}[/color][/b][/size]", markup=True, size_hint_y=None, height=54, halign='center', valign='middle', shorten=False)
        lbl_cl1.bind(size=lambda s, v: setattr(s, 'text_size', (None, v[1])))
        card_client.add_widget(lbl_cl1)
        if via_malevich:
            lbl_cl2 = Label(text=f"[size=16sp][color=#FFD54F]печать через:[/color][/size]  [size=21sp][b][color=#FFFFFF]{cr_name}[/color][/b][/size]", markup=True, size_hint_y=None, height=54, halign='center', valign='middle', shorten=False)
            lbl_cl2.bind(size=lambda s, v: setattr(s, 'text_size', (None, v[1])))
            card_client.add_widget(lbl_cl2)

        # ── СЕКЦИЯ: МАТЕРИАЛ ──
        card_mat, body_mat = self._calc_section("МАТЕРИАЛ", accent=(0.55, 0.4, 0.75), title_color="#C0A0FF")
        header_banner = RoundedButton(text=f"{descs.get(mode, 'ПЛЕНКА')} {format_num_simple(self.current_calc_price)} р/м2", font_size='19sp', halign='center', bg_color=bgs.get(mode, (0.08, 0.4, 0.25, 1)), size_hint_y=None, height=62, radius=12, bold=True)
        body_mat.add_widget(header_banner)

        # ── СЕКЦИЯ: РАЗМЕРЫ (поля в ряд) ──
        card_size, body_size = self._calc_section("РАЗМЕРЫ И КОЛИЧЕСТВО", accent=(0.85, 0.6, 0.25), title_color="#FFCB66")
        body_size.add_widget(Widget(size_hint_y=None, height=12))
        size_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=150)
        f_l, in_l = self._labeled_field("ДЛИНА, м", "0.0")
        f_w, in_w = self._labeled_field("ШИРИНА, м", "0.0")
        f_c, in_c = self._labeled_field("КОЛ-ВО, шт", "1", "1")
        size_row.add_widget(f_l); size_row.add_widget(f_w); size_row.add_widget(f_c)
        body_size.add_widget(size_row)

        # ── СЕКЦИЯ: РАСЧЁТ ──
        card_calc, body_calc = self._calc_section("ФИНАНСОВЫЙ РАСЧЁТ", accent=(0.85, 0.35, 0.3), title_color="#FF8577")
        if _show_print_cost:
            r_cost, in_cost = self.cr_calc_row(f"{cr_name} (р/м2):", "55"); in_cost.text = app.print_cost
            body_calc.add_widget(r_cost)
            res = Label(text="", markup=True, font_size='1sp', size_hint_y=None, height=0, opacity=0)
            cost_res = res
            profit_res = Label(text="", markup=True, font_size='1sp', size_hint_y=None, height=0, opacity=0)
        else:
            r_cost, in_cost = self.cr_calc_row("СЕБЕСТ. (р/м2):", "55"); in_cost.text = app.print_cost
            res = Label(text="[b]КЛИЕНТ: 0 руб[/b]", markup=True, font_size='24sp', bold=True, color=(0.4, 1, 0.5, 1), size_hint_y=None, height=54, halign='center', valign='middle', shorten=True, shorten_from='right')
            res.bind(size=lambda s, v: setattr(s, 'text_size', (v[0], None)))
            body_calc.add_widget(res)
            cost_res = Label(text="", markup=True, font_size='17sp', size_hint_y=None, height=0, opacity=0)
            profit_res = Label(text="", markup=True, font_size='21sp', size_hint_y=None, height=0, opacity=0)

        def recalculate_total(*a):
            l, w, c, cost = safe_float(in_l.text), safe_float(in_w.text), safe_float(in_c.text, 1), safe_float(in_cost.text)
            client_pay = l * w * self.current_calc_price * c
            print_pay = l * w * cost * c
            if not _show_print_cost:
                res.text = f"[b]КЛИЕНТ: {format_num_simple(client_pay)} руб[/b]"
            app.print_cost = str(cost); app.save_data()

        for inp in (in_l, in_w, in_c, in_cost): inp.bind(text=recalculate_total)
        pop, btn_box = AppPopup(title="", content=scroll, size_hint=(0.9, 0.9)), BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=140)
        btn_s = RoundedButton(text="ЗАПИСАТЬ\nВ ДОЛГ", bg_color=(0.2, 0.6, 0.4, 1), bold=True, size_hint_x=0.5, font_size='16sp')
        btn_add = RoundedButton(text="ДОБАВИТЬ", bg_color=(0.1, 0.4, 0.8, 1), bold=True, size_hint_x=0.5, font_size='18sp')
        btn_box.add_widget(btn_s); btn_box.add_widget(btn_add)
        hint_add_material = Label(text="* Зажмите [b]ДОБАВИТЬ[/b] подольше, чтобы сменить материал/цену", markup=True, color=(0.7,0.7,0.7,1), font_size='13sp', halign='center', size_hint_y=None, height=45)
        btn_dop = RoundedButton(text="+ ДОПОБРАБОТКА\n(проклейка / люверсы)", markup=True, bg_color=(0.55, 0.35, 0.7, 1), bold=True, size_hint_y=None, height=110, font_size='17sp')
        self.order_total_accumulator, self.raw_history_lines, self.history_counter = 0.0, [], 0
        last_add_click_ts = [0.0]
        total_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=140)
        btn_total_order = RoundedButton(text="СУММА ЗАКАЗА:\n0 руб", bg_color=(0.5, 0.0, 0.0, 1), size_hint_x=0.6, font_size='18sp', bold=True)
        btn_undo = CancelButton(text="ОТМЕНА ШАГА", bg_color=(0.7, 0.2, 0.2, 1), size_hint_x=0.4, font_size='14sp', bold=True)
        total_box.add_widget(btn_total_order); total_box.add_widget(btn_undo)
        history_header = Label(text="[b]--- ТЕКУЩИЙ ЗАКАЗ ---[/b]", markup=True, font_size='16sp', color=(1, 1, 1, 1), size_hint_y=None, height=35)
        history_layout = BoxLayout(orientation='vertical', spacing=15, size_hint_y=None)
        history_layout.bind(minimum_height=history_layout.setter('height'))
        empty_placeholder = Label(text="Пока пусто.\nЗаполните размеры и нажмите ДОБАВИТЬ", halign='center', valign='middle', font_size='15sp', color=(0.6, 0.6, 0.6, 1), size_hint_y=None, height=70)
        empty_placeholder.bind(size=lambda s, v: setattr(s, 'text_size', v))
        history_layout.add_widget(empty_placeholder)

        def flash_btn(btn, ok=True, msg=None):
            old_t, old_c = btn.text, list(btn.bg_color)
            btn.text = msg or ("OK" if ok else "ОШИБКА")
            btn.bg_color = [0.1, 0.8, 0.1, 1] if ok else [0.9, 0.15, 0.15, 1]
            Clock.schedule_once(lambda dt: (setattr(btn, 'text', old_t), setattr(btn, 'bg_color', old_c)), 1.2)

        def on_undo_clicked(instance):
            if not self.raw_history_lines:
                return
            last = self.raw_history_lines[-1]
            matches = [(c, h) for c in app.clients for h in c.get('history', [])
                       if last.get('oid') and h.get('oid') == last['oid']]
            if len(matches) != 1:
                flash_btn(instance, ok=False, msg="ЗАКАЗ НЕ НАЙДЕН")
                return
            ok, message = reverse_order(app, *matches[0])
            if not ok:
                self._stub_popup("ОТМЕНА ШАГА", message)
                return
            self.raw_history_lines.pop()
            self.order_total_accumulator = round(self.order_total_accumulator - safe_float(last['sum']), 2)
            btn_total_order.text = f"СУММА ЗАКАЗА:\n{format_num_simple(self.order_total_accumulator)} руб"
            if history_layout.children:
                history_layout.remove_widget(history_layout.children[0])
            if not self.raw_history_lines and empty_placeholder.parent is None:
                history_layout.add_widget(empty_placeholder)
            self.refresh_list()
            flash_btn(instance, ok=True, msg="ОТМЕНЕНО")

        btn_undo.bind(on_release=on_undo_clicked)

        def on_add_to_debt_clicked(instance):
            if not resolve_targets():
                return
            now_ts = time.time()
            if now_ts - last_add_click_ts[0] < 0.6:
                return
            last_add_click_ts[0] = now_ts
            if not in_l.text or not in_w.text:
                flash_btn(instance, ok=False, msg="ВВЕДИТЕ\nРАЗМЕР")
                return
            try:
                l_v, w_v, c_v = safe_float(in_l.text), safe_float(in_w.text), safe_float(in_c.text, 1)
                cost_per_m2 = safe_float(in_cost.text)
                client_pay = l_v * w_v * self.current_calc_price * c_v
                t_text = f"{format_num_simple(client_pay)} руб"
                p_cost = (l_v * w_v * cost_per_m2 * c_v) if _show_print_cost else 0.0
                l_val, w_val, c_val = in_l.text or "0", in_w.text or "0", in_c.text or "1"
                badge = badges.get(self.current_calc_mode, "ПЛ.")
                saved_ok = self._final_save(idx, t_text, instance, self.current_calc_mode, print_cost=p_cost, via_malevich=via_malevich, creditor_idx=creditor_idx, order_desc=f"{l_val}x{w_val} x{c_val}шт", price=self.current_calc_price, badge=f"[{badge}]", print_price=cost_per_m2)
            except Exception:
                flash_btn(instance, ok=False, msg="ОШИБКА")
                return
            if not saved_ok:
                flash_btn(instance, ok=False, msg="СУММА=0")
                return
            self.history_counter += 1
            pure_sum = format_num_simple(client_pay).replace(' ', '')
            self.order_total_accumulator += safe_float(pure_sum)
            btn_total_order.text = f"СУММА ЗАКАЗА:\n{format_num_simple(self.order_total_accumulator)} руб"
            saved_item = app.clients[idx]['history'][-1]
            banner_deducted = saved_item.get('banner_deduction', 0.0)
            banner_deducted2 = saved_item.get('banner_deduction2', 0.0)
            banner_deducted2_idx = saved_item.get('banner_deduction2_idx')
            cr_name_target = saved_item.get('creditor_name')
            self.raw_history_lines.append({'oid': saved_item.get('oid'), 'num': self.history_counter, 'l': l_val, 'w': w_val, 'c': c_val, 'sum': pure_sum, 'mode': self.current_calc_mode, 'price': self.current_calc_price, 'print_cost': p_cost, 'via_malevich': via_malevich, 'creditor_name': cr_name_target, 'client_idx': idx, 'banner_deduction': banner_deducted, 'banner_deduction2': banner_deducted2, 'banner_deduction2_idx': banner_deducted2_idx})
            if empty_placeholder.parent is None:
                pass
            else:
                history_layout.remove_widget(empty_placeholder)
            row_card = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, padding=[10, 10, 10, 10])
            with row_card.canvas.before:
                Color(0.25, 0.25, 0.25, 0.4)
                rect = RoundedRectangle(pos=row_card.pos, size=row_card.size, radius=[(10, 10), (10, 10), (10, 10), (10, 10)])
            row_card.bind(pos=lambda s, p: setattr(rect, 'pos', p), size=lambda s, sz: setattr(rect, 'size', sz))
            t_line = f"{l_val}x{w_val} [color=#FF4444]{format_num_simple(self.current_calc_price)}[/color] x{c_val}шт = {pure_sum}" + (f" [color=#FF4444](-{format_num_simple(p_cost)})[/color]" if not app.clients[idx].get('is_creditor') else "")
            h_line = Label(text=t_line, markup=True, font_size='16sp', halign='left', valign='middle')
            h_line.bind(size=lambda s, v: setattr(s, 'text_size', (s.width, None)))
            row_card.add_widget(h_line)
            row_card.add_widget(BadgeLabel(text=badge))
            history_layout.add_widget(row_card)
            in_l.text, in_w.text, in_c.text = "", "", "1"
            if not _show_print_cost:
                res.text = "[b]КЛИЕНТ: 0 руб[/b]"

        def on_add_material_clicked(instance):
            mat_scroll = ScrollView()
            mat_content = BoxLayout(orientation='vertical', spacing=15, padding=[15, 20, 15, 20], size_hint_y=None)
            mat_content.bind(minimum_height=mat_content.setter('height'))
            mat_pop = TopMenuPopup(title="ВЫБОР МАТЕРИАЛА", content=mat_scroll, size_hint=(0.9, 0.8))

            def open_price_popup(c_mode):
                p_scroll = ScrollView()
                p_content = BoxLayout(orientation='vertical', spacing=15, padding=[15, 20, 15, 20], size_hint_y=None)
                p_content.bind(minimum_height=p_content.setter('height'))
                _ptitles = {"malevich_banner": "ЦЕНА (БАНЕР)", "banner_white": "ЦЕНА (БЕЛЫЙ БАНЕР)", "banner_black": "ЦЕНА (ЧЕРНЫЙ БАНЕР)", "malevich_plenka_gloss": "ЦЕНА (ПЛЕНКА ГЛЯНЕЦ)", "malevich_plenka_matte": "ЦЕНА (ПЛЕНКА МАТОВАЯ)", "plenka": "ЦЕНА (ПЛЕНКА)"}
                p_pop = TopMenuPopup(title=_ptitles.get(c_mode, "ВЫБОР ЦЕНЫ"), content=p_scroll, size_hint=(0.9, 0.85))
                p_grid = GridLayout(cols=2, spacing=12, size_hint_y=None, height=220)
                prices = app.prices if "banner" in c_mode else app.plenka_prices
                _pbg = bgs.get(c_mode, (0.1, 0.45, 0.85, 1))
                n_inp = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), text=str(prices[0]), input_type='number', input_filter='float', multiline=False, font_size='32sp', halign='center', size_hint_y=None, height=110)
                for p in prices:
                    p_btn = RoundedButton(text=str(p), bg_color=_pbg, font_size='24sp', bold=True)
                    p_btn.bind(on_release=lambda x, val=p: setattr(n_inp, 'text', str(val)))
                    p_grid.add_widget(p_btn)

                def apply_price(x):
                    if getattr(p_pop, 'is_dismissing_flag', False): return
                    p_pop.is_dismissing_flag = True
                    self.current_calc_price = safe_float(n_inp.text)
                    self.current_calc_mode = c_mode
                    header_banner.text = f"{descs.get(c_mode, 'ПЛЕНКА')} {format_num_simple(n_inp.text)} р/м2"
                    header_banner.bg_color = bgs.get(c_mode, (0.08, 0.4, 0.25, 1))
                    recalculate_total()
                    p_pop.dismiss()

                btn_apply = RoundedButton(text="ДАЛЕЕ >>>", bg_color=(0.2, 0.65, 0.42, 1), height=135, size_hint_y=None, bold=True, font_size='26sp')
                btn_apply.bind(on_release=apply_price)
                _phint = Label(text="[b][color=#FFD54F]ВЫБРАННАЯ ЦЕНА\n(можно изменить вручную)[/color][/b]", markup=True, size_hint_y=None, height=60, font_size='18sp', halign='center', valign='middle')
                _phint.bind(size=lambda s, v: setattr(s, 'text_size', v))
                for w in (p_grid, _phint, n_inp, Widget(size_hint_y=None, height=18), btn_apply, Widget(size_hint_y=None, height=10), self.get_bottom_buttons(p_pop, prev_cb=lambda: on_add_material_clicked(instance), cancel_text="ЗАКРЫТЬ"), Widget(size_hint_y=None, height=350)):
                    p_content.add_widget(w)
                p_scroll.add_widget(p_content)
                p_pop.open()

            btns_data = [("БАНЕР", (0.1, 0.45, 0.85, 1), "malevich_banner"), ("ПЛЕНКА ГЛЯНЕЦ", (0.15, 0.6, 0.35, 1), "malevich_plenka_gloss"), ("ПЛЕНКА МАТОВАЯ", (0.11, 0.48, 0.28, 1), "malevich_plenka_matte")] if app.clients[idx].get('is_creditor') else [("БЕЛЫЙ БАНЕР", (0.1, 0.5, 0.8, 1), "banner_white"), ("ЧЕРНЫЙ БАНЕР", (0.2, 0.2, 0.2, 1), "banner_black"), ("ПЛЕНКА", (0.15, 0.6, 0.3, 1), "plenka")]
            for t, col, m in btns_data:
                btn = RoundedButton(text=t, bg_color=col, height=130, size_hint_y=None, bold=True, font_size='24sp')
                btn.bind(on_release=lambda x, md=m: self.safe_transition(mat_pop, open_price_popup, md))
                mat_content.add_widget(btn)
            mat_content.add_widget(self.get_bottom_buttons(mat_pop, cancel_text="ЗАКРЫТЬ"))
            mat_content.add_widget(Widget(size_hint_y=None, height=350))
            mat_scroll.add_widget(mat_content)
            mat_pop.open()

        def _add_order_row(sum_str, desc_text, badge_text):
            self.history_counter += 1
            if empty_placeholder.parent is not None:
                history_layout.remove_widget(empty_placeholder)
            row_card = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, padding=[10, 10, 10, 10])
            with row_card.canvas.before:
                Color(0.25, 0.25, 0.25, 0.4)
                rect = RoundedRectangle(pos=row_card.pos, size=row_card.size, radius=[(10, 10)] * 4)
            row_card.bind(pos=lambda s, p: setattr(rect, 'pos', p), size=lambda s, sz: setattr(rect, 'size', sz))
            h_line = Label(text=desc_text, markup=True, font_size='16sp', halign='left', valign='middle')
            h_line.bind(size=lambda s, v: setattr(s, 'text_size', (s.width, None)))
            row_card.add_widget(h_line)
            row_card.add_widget(BadgeLabel(text=badge_text))
            history_layout.add_widget(row_card)

        def on_dop_clicked(instance):
            dop_pop = TopMenuPopup(title="ДОПОБРАБОТКА", content=BoxLayout(orientation='vertical', spacing=15, padding=20), size_hint=(0.9, 0.62))
            lbl_info = Label(text="[color=#CCCCCC]Проклейка, люверсы и др.\nСумма идёт клиенту в долг\nи полностью в чистую прибыль[/color]",
                             markup=True, font_size='16sp', halign='center', valign='middle', size_hint_y=None, height=90)
            lbl_info.bind(size=lambda s, v: setattr(s, 'text_size', v))
            in_dop = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="Сумма за допобработку...", input_type='number', input_filter='float',
                               multiline=False, font_size='30sp', halign='center', size_hint_y=None, height=100)
            dop_pop.content.add_widget(lbl_info)
            dop_pop.content.add_widget(in_dop)

            def save_dop(x):
                if not resolve_targets():
                    return
                val = safe_float(in_dop.text)
                if val <= 0:
                    return
                if getattr(dop_pop, 'is_dismissing_flag', False): return
                dop_pop.is_dismissing_flag = True
                # print_cost=0 -> всё в прибыль; mode='dop' -> материал не списывается
                saved_ok = self._final_save(idx, f"{format_num_simple(val)} руб", instance, "dop",
                                            print_cost=0.0, via_malevich=via_malevich, creditor_idx=creditor_idx,
                                            order_desc="Допобработка", price=None, badge="[ДОП]", print_price=0.0)
                if not saved_ok:
                    dop_pop.dismiss()
                    return
                self.order_total_accumulator += val
                btn_total_order.text = f"СУММА ЗАКАЗА:\n{format_num_simple(self.order_total_accumulator)} руб"
                cr_name_target = app.clients[idx]['history'][-1].get('creditor_name')
                self.raw_history_lines.append({'oid': app.clients[idx]['history'][-1].get('oid'), 'num': self.history_counter + 1, 'l': '', 'w': '', 'c': '1',
                                               'sum': format_num_simple(val), 'mode': 'dop', 'price': None,
                                               'print_cost': 0.0, 'via_malevich': via_malevich,
                                               'creditor_name': cr_name_target, 'client_idx': idx, 'banner_deduction': 0.0})
                _add_order_row(format_num_simple(val),
                               f"[b]Допобработка[/b]  [color=#00FF00]= {format_num_simple(val)}[/color]", "ДОП")
                dop_pop.dismiss()

            btn_save_dop = RoundedButton(text="ДОБАВИТЬ В ЗАКАЗ", bg_color=(0.2, 0.6, 0.4, 1), height=90, size_hint_y=None, bold=True)
            btn_save_dop.bind(on_release=save_dop)
            dop_pop.content.add_widget(btn_save_dop)
            dop_pop.content.add_widget(self.get_bottom_buttons(dop_pop, cancel_text="ОТМЕНА"))
            dop_pop.open()

        btn_dop.bind(on_release=on_dop_clicked)
        btn_s.bind(on_release=on_add_to_debt_clicked)
        btn_add.bind(on_release=on_add_to_debt_clicked, on_long_press=on_add_material_clicked)
        _gap = lambda: Widget(size_hint_y=None, height=12)
        for w in (card_client, _gap(), card_mat, _gap(), card_size, _gap(), card_calc, btn_box, btn_dop, Widget(size_hint_y=None, height=15), total_box, history_header, history_layout, Widget(size_hint_y=None, height=20), self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ"), Widget(size_hint_y=None, height=350)):
            content.add_widget(w)
        scroll.add_widget(content); pop.open()

    def _final_save(self, idx, res_t, btn, mode="banner_white", print_cost=0.0, via_malevich=False, creditor_idx=None, order_desc=None, price=None, badge=None, print_price=0.0):
        app = App.get_running_app()
        if not app:
            return False
        state = snapshot(app)
        try:
            ensure_ids(app.clients)
            val = safe_float(res_t.replace(' руб', ''))
            if val <= 0 or not math.isfinite(print_cost) or print_cost < 0: return False
            if via_malevich and (creditor_idx is None or not app.clients[creditor_idx].get('is_creditor') or idx == creditor_idx):
                return False
            c = app.clients[idx]
            if 'history' not in c: c['history'] = []
            total_deducted = 0.0
            _oid = uuid.uuid4().hex
            hist_item = {
                'oid': _oid,
                'date': datetime.now().strftime("%d.%m.%y %H:%M"),
                'desc': order_desc or f"Заказ: {mode.replace('_', ' ')}",
                'sum': format_num_simple(val),
                'print_cost': print_cost,
                'via_malevich': via_malevich,
                'mode': mode,
                'banner_deduction': 0.0
            }
            if price is not None: hist_item['price'] = price
            if badge is not None: hist_item['badge'] = badge
            if via_malevich and creditor_idx is not None:
                hist_item['creditor_name'] = app.clients[creditor_idx].get('name')
                hist_item['creditor_id'] = app.clients[creditor_idx]['cid']
            c['history'].append(hist_item)
            c['debt'] = format_num_simple(safe_float(c.get('debt', 0)) + val)
            app.profit_correction = str(round(safe_float(app.profit_correction) - print_cost, 2))
            m_indices, _, b_idx, black_idx = app.get_special_clients()
            if via_malevich and creditor_idx is not None and print_cost > 0:
                app.clients[creditor_idx]['debt'] = format_num_simple(safe_float(app.clients[creditor_idx].get('debt', 0)) + print_cost)
                if 'history' not in app.clients[creditor_idx]:
                    app.clients[creditor_idx]['history'] = []
                c_name = app.clients[idx].get('name', 'Клиент')
                m_hist_item = {
                    'source_oid': _oid,
                    'date': hist_item['date'],
                    'desc': f"{c_name} {order_desc}",
                    'sum': format_num_simple(print_cost),
                    'price': print_price if print_price > 0 else safe_float(app.print_cost),
                    'print_cost': 0.0,
                    'via_malevich': False,
                    'mode': mode,
                    'banner_deduction': 0.0
                }
                if badge is not None: m_hist_item['badge'] = badge
                app.clients[creditor_idx]['history'].append(m_hist_item)
            # Любой баннерный заказ гасит общий минус: сначала свой цвет, потом остаток — другой цвет
            is_banner_order = ("banner_white" in mode) or ("banner_black" in mode)
            if is_banner_order and val > 0:
                primary_idx = b_idx if "banner_white" in mode else black_idx
                secondary_idx = black_idx if "banner_white" in mode else b_idx
                remaining = val
                total_deducted = 0.0
                # 1) гасим свой цвет
                if primary_idx is not None:
                    pdebt = safe_float(app.clients[primary_idx].get('debt', 0))
                    if pdebt > 0 and remaining > 0:
                        d1 = min(pdebt, remaining)
                        app.clients[primary_idx]['debt'] = format_num_simple(max(0.0, pdebt - d1))
                        remaining -= d1
                        total_deducted += d1
                        hist_item['banner_deduction'] = d1
                        hist_item['banner_deduction_id'] = app.clients[primary_idx]['cid']
                # 2) остаток гасит другой цвет
                if secondary_idx is not None and remaining > 0:
                    sdebt = safe_float(app.clients[secondary_idx].get('debt', 0))
                    if sdebt > 0:
                        d2 = min(sdebt, remaining)
                        app.clients[secondary_idx]['debt'] = format_num_simple(max(0.0, sdebt - d2))
                        remaining -= d2
                        total_deducted += d2
                        hist_item['banner_deduction2'] = d2
                        hist_item['banner_deduction2_idx'] = secondary_idx
                        hist_item['banner_deduction2_id'] = app.clients[secondary_idx]['cid']
                if total_deducted > 0:
                    app.profit_correction = str(round(safe_float(app.profit_correction) - total_deducted, 2))
            try:
                _op = round(val - safe_float(print_cost), 2)
                if not hasattr(app, 'profit_log') or app.profit_log is None:
                    app.profit_log = []
                if not c.get('is_creditor'):
                    app.profit_log.append({'oid': _oid, 'date': hist_item['date'], 'name': c.get('name', ''),
                    'desc': (order_desc or '').strip() or hist_item['desc'],
                    'profit': _op, 'assumed': bool(total_deducted > 0)})
            except Exception:
                pass
            if app.save_data() is not True:
                raise OSError('Сохранение не подтверждено')
        except Exception as exc:
            restore(app, state)
            self._stub_popup('СОХРАНЕНИЕ ЗАКАЗА', 'Заказ не сохранён: ' + str(exc))
            return False
        self.refresh_list()
        return True


    def show_edit_popup(self, idx):
        app = App.get_running_app()
        if not app:
            return
        c = app.clients[idx]
        m_indices, o_idx, b_idx, c_idx = app.get_special_clients()
        is_special_banner = idx in (b_idx, c_idx)

        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=32, padding=[16, 14, 16, 14], size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        pop = TopMenuPopup(title="РЕДАКТИРОВАНИЕ", content=scroll, size_hint=(0.95, 0.9))
        pop.background_color = (0.043, 0.055, 0.08, 1)

        def make_card(caption, accent, field, height=272):
            card = BoxLayout(orientation='vertical', size_hint_y=None, height=height,
                             padding=[20, 18, 20, 22], spacing=20)

            def _draw(w, *a):
                w.canvas.before.clear()
                with w.canvas.before:
                    Color(accent[0], accent[1], accent[2], 1)
                    RoundedRectangle(pos=w.pos, size=w.size, radius=[(24, 24)] * 4)
                    Color(0.07, 0.086, 0.133, 1)
                    RoundedRectangle(pos=(w.x + 3, w.y + 3), size=(w.width - 6, w.height - 6), radius=[(21, 21)] * 4)
            card.bind(pos=_draw, size=_draw)
            cap = Label(text=f"[b]{caption}[/b]", markup=True, font_size='16sp',
                        color=(accent[0], accent[1], accent[2], 1), halign='center', valign='middle',
                        size_hint_y=None, height=42)
            cap.bind(size=lambda s, v: setattr(s, 'text_size', v))
            card.add_widget(cap)
            card.add_widget(field)
            return card

        def styled_input(**kw):
            return TextInput(multiline=False, halign='center', font_size='26sp',
                             background_normal='', background_active='',
                             background_color=(0.11, 0.13, 0.19, 1), foreground_color=(1, 1, 1, 1),
                             cursor_color=(0.2, 0.75, 0.84, 1), size_hint_y=None, height=132,
                             padding=[10, 30, 10, 16], **kw)

        # ── ИМЯ ──
        if is_special_banner:
            in_n = None
            name_lbl = Label(text=f"[b]{c.get('name', '').upper()}[/b]", markup=True,
                             font_size='27sp', color=(1, 0.8, 0.2, 1), halign='center', valign='middle',
                             size_hint_y=None, height=132)
            name_lbl.bind(size=lambda s, v: setattr(s, 'text_size', v))
            content.add_widget(make_card("МАТЕРИАЛ", (0.2, 0.75, 0.84, 1), name_lbl))
        else:
            in_n = styled_input(text=c.get('name', ''))
            content.add_widget(make_card("ИМЯ КЛИЕНТА", (0.2, 0.75, 0.84, 1), in_n))

        # ── ДОЛГ ──
        in_d = styled_input(text=str(c.get('debt', '0')).replace(',', '.'),
                            input_type='number', input_filter='float')
        content.add_widget(make_card("ДОЛГ / МИНУС", (1.0, 0.843, 0.251, 1), in_d))

        def on_edit_save(instance):
            if getattr(pop, 'is_dismissing_flag', False):
                return
            pop.is_dismissing_flag = True
            d_val, old_val = safe_float(in_d.text), safe_float(c.get('debt', '0'))
            if not is_special_banner and in_n:
                c['name'] = in_n.text.strip()
            c['debt'] = format_num_simple(d_val)
            if d_val == 0.0:
                c['zakupka_total'] = '0'
            if not c.get('is_creditor') and not is_special_banner:
                realized = max(0.0, old_val) - max(0.0, d_val)
                if realized > 0:
                    app.profit_correction = str(round(safe_float(app.profit_correction) + realized, 2))
            app.save_data()
            self.refresh_list()
            pop.dismiss()

        def on_delete(instance):
            if getattr(pop, 'is_dismissing_flag', False):
                return
            pop.is_dismissing_flag = True
            app.clients.pop(idx)
            app.save_data()
            self.refresh_list()
            pop.dismiss()

        # ── КНОПКИ ──
        btn_reset = RoundedButton(text="ОБНУЛИТЬ", bg_color=(0.32, 0.36, 0.44, 1),
                                  height=98, size_hint_y=None, bold=True, radius=24, font_size='20sp')
        btn_reset.bind(on_release=lambda x: setattr(in_d, 'text', '0'))
        content.add_widget(btn_reset)

        row = BoxLayout(orientation='horizontal', spacing=14, size_hint_y=None, height=120)
        btn_ok = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.2, 0.62, 0.42, 1), bold=True, radius=24, font_size='21sp')
        btn_ok.bind(on_release=on_edit_save)
        row.add_widget(btn_ok)
        if not is_special_banner:
            btn_del = RoundedButton(text="УДАЛИТЬ", bg_color=(0.8, 0.3, 0.3, 1), bold=True, radius=24, font_size='21sp')
            btn_del.bind(on_release=on_delete)
            row.add_widget(btn_del)
        content.add_widget(row)

        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ"))
        content.add_widget(Widget(size_hint_y=None, height=300))
        scroll.add_widget(content)
        pop.open()

    def show_debt_popup(self, idx, prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        scroll, c = ScrollView(), app.clients[idx]
        content = BoxLayout(orientation='vertical', spacing=30, padding=[18, 16, 18, 16], size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # ── ТЕКУЩИЙ ДОЛГ — крупно, вверху ──
        head = BoxLayout(orientation='vertical', size_hint_y=None, height=228, padding=[16, 16, 16, 18], spacing=6)
        def _draw_head(w, *a):
            w.canvas.before.clear()
            with w.canvas.before:
                Color(0.2, 0.75, 0.84, 1)
                RoundedRectangle(pos=w.pos, size=w.size, radius=[(24, 24)] * 4)
                Color(0.08, 0.10, 0.15, 1)
                RoundedRectangle(pos=(w.x + 3, w.y + 3), size=(w.width - 6, w.height - 6), radius=[(21, 21)] * 4)
        head.bind(pos=_draw_head, size=_draw_head)
        cap_head = Label(text="[b]ТЕКУЩИЙ ДОЛГ[/b]", markup=True, font_size='15sp',
                         color=(0.5, 0.78, 0.85, 1), halign='center', valign='middle', size_hint_y=0.36)
        cap_head.bind(size=lambda s, v: setattr(s, 'text_size', v))
        val_head = Label(text=f"[b][color=#FFD54F]{c.get('debt', '0')} \u20bd[/color][/b]",
                         markup=True, font_size='29sp', halign='center', valign='middle', size_hint_y=0.64)
        val_head.bind(size=lambda s, v: setattr(s, 'text_size', v))
        head.add_widget(cap_head)
        head.add_widget(val_head)
        content.add_widget(head)

        content.add_widget(Label(text="[b]СКОЛЬКО ОТДАЛ (ОТНЯТЬ)[/b]", markup=True, font_size='19sp',
                                 color=(0.4, 0.8, 1, 1), halign='center', valign='middle',
                                 size_hint_y=None, height=40))
        in_minus = _dark_input(hint_text="Сумма оплаты...", input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_minus, (0.4, 0.8, 1, 1), 172, 0.6))
        content.add_widget(Label(text="ИЛИ ИЗМЕНИТЬ ДОЛГ ВРУЧНУЮ", font_size='15sp',
                                 color=(0.55, 0.6, 0.66, 1), halign='center', valign='middle',
                                 size_hint_y=None, height=34))
        in_d = _dark_input(text=str(c.get('debt', '0')), input_type='number', input_filter='float')
        content.add_widget(_bordered_field(in_d, (0.45, 0.5, 0.6, 1), 156, 0.6))
        btn = RoundedButton(text="СОХРАНИТЬ", bg_color=(0.2, 0.62, 0.42, 1), height=116, size_hint_y=None,
                            bold=True, radius=24, font_size='22sp')
        pop = TopMenuPopup(title=c.get('name', '').upper(), content=scroll, size_hint=(0.94, 0.82))
        pop.background_color = (0.043, 0.055, 0.08, 1)

        def save_debt(instance):
            if getattr(pop, 'is_dismissing_flag', False): return
            pop.is_dismissing_flag = True
            old_val = safe_float(c.get('debt', '0'))
            minus_val = safe_float(in_minus.text)
            if minus_val > 0:
                # «отдал» гасит долг В СТОРОНУ НУЛЯ (не пересекая ноль):
                # положительный уменьшается, отрицательный (переплата) подтягивается к нулю
                if old_val >= 0:
                    d_val = old_val - minus_val
                else:
                    d_val = min(0.0, old_val + minus_val)
            else:
                d_val = safe_float(in_d.text)
            c['debt'] = format_num_simple(d_val)
            if d_val == 0.0:
                c['zakupka_total'] = '0'
            if not c.get('is_creditor') and c.get('name', '').lower().strip() not in ("баннер остаток", "белый банер", "черный банер", "олег белый", "олег черный"):
                realized = max(0.0, old_val) - max(0.0, d_val)
                if realized > 0:
                    app.profit_correction = str(round(safe_float(app.profit_correction) + realized, 2))
            app.save_data()
            self.refresh_list()
            pop.dismiss()

        btn.bind(on_release=save_debt)
        content.add_widget(btn)
        content.add_widget(Widget(size_hint_y=None, height=10))
        content.add_widget(self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ"))
        content.add_widget(Widget(size_hint_y=None, height=350))
        scroll.add_widget(content)
        pop.open()

    def show_add_popup(self, *args):
        scroll = ScrollView()
        content = BoxLayout(orientation='vertical', spacing=20, padding=20, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))
        in_n = TextInput(background_normal='', background_active='', background_color=(0.17, 0.20, 0.27, 1), foreground_color=(1, 1, 1, 1), hint_text_color=(0.55, 0.6, 0.68, 1), cursor_color=(0.2, 0.75, 0.84, 1), hint_text="Имя...", multiline=False, font_size='22sp', size_hint_y=None, height=100)
        btn = RoundedButton(text="ДОБАВИТЬ", bg_color=(0.2, 0.6, 0.4, 1), height=110, size_hint_y=None, bold=True)
        pop = TopMenuPopup(title="НОВЫЙ КЛИЕНТ", content=scroll, size_hint=(0.9, 0.6))

        def save_new(instance):
            if in_n.text.strip():
                if getattr(pop, 'is_dismissing_flag', False): return
                pop.is_dismissing_flag = True
                App.get_running_app().clients.append({'name': in_n.text.strip(), 'debt': '0'})
                App.get_running_app().save_data(); self.refresh_list(); pop.dismiss()

        btn.bind(on_release=save_new)
        content.add_widget(in_n); content.add_widget(btn)
        content.add_widget(self.get_bottom_buttons(pop, cancel_text="ЗАКРЫТЬ"))
        content.add_widget(Widget(size_hint_y=None, height=350))
        scroll.add_widget(content); pop.open()

    def show_malevich_menu(self, idx, prev_cb=None):
        app = App.get_running_app()
        if not app:
            return
        content = BoxLayout(orientation='vertical', spacing=20, padding=20)
        c_name = app.clients[idx].get('name', 'КРЕДИТОР').upper()
        pop = AppPopup(title=f"{c_name} -> НАСТРОЙКИ", content=content, size_hint=(0.9, 0.6))
        b_edit = RoundedButton(text="ИЗМЕНИТЬ ДОЛГ", bg_color=(0.2, 0.5, 0.8, 1), height=140, size_hint_y=None, font_size='24sp', bold=True)
        b_edit.bind(on_release=lambda x: self.safe_transition(pop, self.show_debt_popup, idx, prev_cb=lambda p=None: self.show_malevich_menu(idx, prev_cb)))
        b_reset = RoundedButton(text="ОБНУЛИТЬ ДОЛГ", bg_color=(0.7, 0.1, 0.1, 1), height=140, size_hint_y=None, font_size='24sp', bold=True)

        def confirm_reset(instance):
            p_conf = AppPopup(title="ВНИМАНИЕ", content=BoxLayout(orientation='vertical', spacing=20, padding=20), size_hint=(0.85, 0.5))
            btn_yes = RoundedButton(text="ДА, ОБНУЛИТЬ", bg_color=(0.8, 0.2, 0.2, 1), height=100, size_hint_y=None, bold=True)

            def on_yes(x):
                if getattr(p_conf, 'is_dismissing_flag', False): return
                p_conf.is_dismissing_flag = True
                app.clients[idx].update({'debt': '0', 'zakupka_total': '0', 'history': []})
                app.save_data()
                self.refresh_list()
                p_conf.dismiss()
                if not getattr(pop, 'is_dismissing_flag', False):
                    pop.is_dismissing_flag = True
                    pop.dismiss()

            btn_yes.bind(on_release=on_yes)
            p_conf.content.add_widget(Label(text=f"Обнулить долг и историю\nтолько для {c_name}?", halign='center'))
            p_conf.content.add_widget(btn_yes)
            p_conf.content.add_widget(self.get_bottom_buttons(p_conf, cancel_text="ЗАКРЫТЬ"))
            p_conf.open()

        b_reset.bind(on_release=confirm_reset)
        for w in (b_edit, b_reset, self.get_bottom_buttons(pop, prev_cb, cancel_text="ЗАКРЫТЬ")): content.add_widget(w)
        pop.open()


class BusinessApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_popup_close = 0
        self.active_popups = 0

    def build(self):
        self.load_data()
        sm = ScreenManager()
        sm.add_widget(MainMenu(name='main_menu'))
        sm.add_widget(ClientsScreen(name='clients_screen'))
        return sm

    def get_special_clients(self):
        m_indices = []
        o_idx = b_idx = c_idx = None
        for i, c in enumerate(self.clients):
            n = c.get('name', '').lower().strip()
            if c.get('is_creditor') or n == "малевич":
                c['is_creditor'] = True
                m_indices.append(i)
            elif n in ("олега", "олег", "баннер остаток") and not c.get('is_creditor'):
                o_idx = i
            elif "белый" in n and "олег" not in n: b_idx = i
            elif ("черный" in n or "чёрный" in n) and "олег" not in n: c_idx = i
        return m_indices, o_idx, b_idx, c_idx

    def ensure_default_clients(self):
        names = [c.get('name', '').upper() for c in self.clients]
        has_ost = any(n in ("ОЛЕГ", "ОЛЕГА", "БАННЕР ОСТАТОК") for n in names)
        if not has_ost:
            self.clients.insert(0, {'name': 'БАННЕР ОСТАТОК', 'debt': '0', 'm_total': '75', 'm_remain': '75'})
        has_creditor = any(c.get('is_creditor') for c in self.clients)
        if not has_creditor:
            m_exists = False
            for c in self.clients:
                if c.get('name', '').upper() == 'МАЛЕВИЧ':
                    c['is_creditor'] = True
                    m_exists = True
                    break
            if not m_exists:
                self.clients.insert(1, {'name': 'МАЛЕВИЧ', 'debt': '0', 'is_creditor': True})
        names = [c.get('name', '').upper() for c in self.clients]
        if not any("БЕЛЫЙ" in n and "ОЛЕГ" not in n for n in names):
            self.clients.append({'name': 'БЕЛЫЙ БАНЕР', 'debt': '0'})
        if not any(("ЧЕРНЫЙ" in n or "ЧЁРНЫЙ" in n) and "ОЛЕГ" not in n for n in names):
            self.clients.append({'name': 'ЧЕРНЫЙ БАНЕР', 'debt': '0'})

    def get_totals(self):
        m_indices, o_idx, b_idx, c_idx = self.get_special_clients()
        tot_debt = my_debt = banner_deficit = 0.0
        for i, client in enumerate(self.clients):
            val = safe_float(client.get('debt', 0))
            if i in m_indices:
                my_debt += val
            elif i in (b_idx, c_idx):
                banner_deficit += val
            elif i != o_idx:
                tot_debt += val
        base_profit = round(tot_debt + safe_float(self.profit_correction), 2)
        real_profit = round(base_profit - banner_deficit, 2)
        if abs(real_profit) < 0.01:
            real_profit = 0.0
        return tot_debt, my_debt, banner_deficit, real_profit

    def _has_real_data(self):
        for c in self.clients:
            name = c.get('name', '').upper()
            is_default = name in ('БАННЕР ОСТАТОК', 'МАЛЕВИЧ', 'БЕЛЫЙ БАНЕР', 'ЧЕРНЫЙ БАНЕР', 'ЧЁРНЫЙ БАНЕР')
            if not is_default:
                return True
            if safe_float(c.get('debt', 0)) != 0:
                return True
            if c.get('history'):
                return True
            if c.get('purchase_log'):
                return True
        return False

    def _restore_from_backup(self):
        try:
            bdir = os.path.join(BASE_PATH, "backups")
            if not os.path.isdir(bdir):
                return False
            files = sorted(os.path.join(bdir, x) for x in os.listdir(bdir)
                           if x.startswith("business_data_") and x.endswith(".json"))
            for path in reversed(files):   # начиная с самой свежей копии
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("clients"):
                        if not isinstance(data, dict) or not isinstance(data.get("clients"), list):
                            raise ValueError("Неверный формат данных")
                        self._extra_data = dict(data)
                        self.clients = data.get("clients", [])
                        self.prices = data.get("prices", ["160", "200", "220", "250"])
                        self.plenka_prices = data.get("plenka_prices", ["250", "300", "350", "400"])
                        self.profit_correction = data.get("profit_correction", "0")
                        self.print_cost = data.get("print_cost", "55")
                        self.profit_log = data.get("profit_log", [])
                        self.rolls = data.get("rolls", [])
                        self._rolls_key_present = ("rolls" in data)
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def load_data(self):
        loaded = False
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or not isinstance(data.get("clients"), list):
                        raise ValueError("Неверный формат данных")
                    self._extra_data = dict(data)
                    self.clients = data.get("clients", [])
                    self.prices = data.get("prices", ["160", "200", "220", "250"])
                    self.plenka_prices = data.get("plenka_prices", ["250", "300", "350", "400"])
                    self.profit_correction = data.get("profit_correction", "0")
                    self.print_cost = data.get("print_cost", "55")
                    self.profit_log = data.get("profit_log", [])
                    self.rolls = data.get("rolls", [])
                    self._rolls_key_present = ("rolls" in data)
                    loaded = True
            except Exception:
                loaded = False
        if not loaded and os.path.exists(DATA_FILE):
            import shutil
            damaged = DATA_FILE + '.damaged'
            if not os.path.exists(damaged):
                shutil.copy2(DATA_FILE, damaged)
        if not loaded:
            # основной файл отсутствует или повреждён — пробуем свежую резервную копию,
            # и только если её нет — грузим пустую заготовку
            if not self._restore_from_backup():
                if os.path.exists(DATA_FILE) or os.path.isdir(os.path.join(BASE_PATH, "backups")):
                    raise RuntimeError("Данные повреждены. Исходные файлы сохранены; требуется восстановление")
                self.load_defaults()
        self.ensure_default_clients()
        self._migrate_rolls_if_needed()
        self.save_data()

    def _migrate_rolls_if_needed(self):
        # если ключа rolls в файле ещё не было — перенесём текущий остаток
        # (БАННЕР ОСТАТОК) как первый белый рулон 3.2, чтобы не потерять метры
        if getattr(self, '_rolls_key_present', False):
            return
        if not hasattr(self, 'rolls') or self.rolls is None:
            self.rolls = []
        if self.rolls:
            return
        _, o_idx, _, _ = self.get_special_clients()
        if o_idx is not None:
            rem = safe_float(self.clients[o_idx].get('m_remain', 0))
            tot = safe_float(self.clients[o_idx].get('m_total', 0))
            if rem > 0 or tot > 0:
                self.rolls.append({
                    'color': 'white',
                    'width': '3.2',
                    'total': format_num_simple(tot if tot > 0 else rem),
                    'remain': format_num_simple(rem)
                })
        self._rolls_key_present = True

    def load_defaults(self):
        self.clients = []
        self.prices, self.plenka_prices = ["160", "200", "220", "250"], ["250", "300", "350", "400"]
        self.profit_correction, self.print_cost = "0", "55"
        self.profit_log = []
        self.rolls = []
        self._rolls_key_present = False

    def _write_backup(self, text):
        try:
            if not self._has_real_data():
                return
            now = time.time()
            if now - getattr(self, '_last_backup_ts', 0) < 90:   # не чаще раза в ~1.5 мин
                return
            self._last_backup_ts = now
            bdir = os.path.join(BASE_PATH, "backups")
            os.makedirs(bdir, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(os.path.join(bdir, f"business_data_{stamp}.json"), "w", encoding="utf-8") as f:
                f.write(text)
            files = sorted(os.path.join(bdir, x) for x in os.listdir(bdir)
                           if x.startswith("business_data_") and x.endswith(".json"))
            for old in files[:-40]:   # держим последние 40 копий
                try:
                    os.remove(old)
                except Exception:
                    pass
        except Exception:
            pass

    def save_data(self):
        ensure_ids(self.clients)
        data = dict(getattr(self, '_extra_data', {}))
        data.update({"clients": self.clients, "prices": self.prices,
                     "plenka_prices": self.plenka_prices,
                     "profit_correction": self.profit_correction,
                     "print_cost": getattr(self, 'print_cost', "55"),
                     "profit_log": getattr(self, 'profit_log', []),
                     "rolls": getattr(self, 'rolls', [])})
        text = atomic_write(DATA_FILE, data)
        self._write_backup(text)
        return True


if __name__ == '__main__':
    BusinessApp().run()
