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
        self.assertEqual(self.app.rolls[-1]['color'], 'plenka')   # рулон плёнки в остатках
        g = [e for e in self.app._extra_data['roll_log'] if e.get('note') == 'закупка'][-1]   # закупка в истории (4.2)
        self.assertEqual((g['kind'], g['note'], g['m'], g['color']), ('новый', 'закупка', 50, 'plenka'))
        self.screen.show_rolls_log()
        self.assertEqual(self.app.get_totals()[0], 2500)  # «ПЛЁНКА» не считается долгом клиента
        self.assertTrue(reverse_order(self.app, self.sasha, first)[0])
        self.assertEqual(self.plenka()['debt'], '1 500')
        self.assertEqual(main.check_integrity(self.app), [])

    def test_client_material_does_not_touch_rolls(self):
        self.assertTrue(purchase_banner(self.app, 'black', 1000)[0])
        self.assertTrue(purchase_banner(self.app, 'plenka', 1000)[0])
        self.order(800, mode='client_material')               # своя печать на материале клиента
        self.assertEqual(self.profit(), 800)
        self.assertEqual((self.black()['debt'], self.plenka()['debt']), ('1 000', '1 000'))
        oleg = {'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True, 'history': []}
        self.app.clients.append(oleg)
        idx = next(i for i, c in enumerate(self.app.clients) if c is self.sasha)
        cr = len(self.app.clients) - 1
        self.assertTrue(self.screen._final_save(idx, '3 000 руб', None, 'client_material', print_cost=2000,
                                                via_malevich=True, creditor_idx=cr, order_desc='10м2'))
        self.assertEqual(self.profit(), 1800)                 # 3000 − 2000 Олегу
        self.assertEqual(oleg['debt'], '2 000')
        self.assertEqual(main.check_integrity(self.app), [])

    def test_current_since(self):
        self.assertIsNone(self.app.current_since())
        self.order(1000)
        self.assertTrue(self.app.take_profit(reset=True)[0])
        self.assertTrue(self.app.current_since())

    def test_roll_writeoff_log(self):
        made = []
        orig = main.RoundedButton.__init__

        def rec(btn, **kw):
            orig(btn, **kw); made.append(btn)
        main.RoundedButton.__init__ = rec
        try:
            self.app.rolls = [{'color': 'black', 'width': '3.2', 'total': '50', 'remain': '30'}]
            self.screen._roll_edit_popup(0, None)
            from kivy.uix.textinput import TextInput
            save_btns = [b for b in made if b.text == 'СОХРАНИТЬ']
            self.assertTrue(save_btns)
            # находим поле «расход» в том же окне
            root = save_btns[-1].parent
            fields = [w for w in root.walk() if isinstance(w, TextInput) and w.hint_text.startswith('расход')]
            fields[0].text = '8'
            plus50 = [b for b in made if b.text == '+50 м'][-1]
            plus50.dispatch('on_release')                     # пришёл рулон 50 м: 30 + 50 − 8
            save_btns[-1].dispatch('on_release')
        finally:
            main.RoundedButton.__init__ = orig
        roll = self.app.rolls[0]
        self.assertEqual(roll['remain'], '72')
        self.assertEqual(roll['total'], '100')
        g = self.app._extra_data['roll_log'][-2:]                # общий журнал (4.1): две строки
        self.assertEqual([(e['kind'], e['m']) for e in g], [('добавлено', 50), ('списано', 8)])
        self.assertEqual(g[0]['left'], 80)
        self.screen.show_rolls_log()
        self.assertEqual(roll['log'][-1]['kind'], 'списано')
        self.assertEqual(roll['log'][-1]['m'], 8)

    def test_sign_field_flips(self):
        from kivy.uix.textinput import TextInput
        ti = TextInput(text='3500')
        row = main._sign_field(ti)
        btn = [w for w in row.walk() if isinstance(w, main.RoundedButton)][0]
        btn.dispatch('on_release'); self.assertEqual(ti.text, '-3500')
        btn.dispatch('on_release'); self.assertEqual(ti.text, '3500')

    def test_printed_meters_since_purchase(self):
        from accounting import printed_meters, roll_length
        from datetime import datetime, timedelta
        self.assertEqual(roll_length(5.43, 2.5), 5.53)          # +5 см полей с каждой стороны
        self.assertEqual(roll_length(3, 2, 2), 4.2)
        self.assertEqual(roll_length(4, 4), 5.25)
        from accounting import pack_length                                  # 4.4: мелкие рядом с большим
        self.assertEqual(pack_length([(5.13, 2.35, 1), (0.6, 0.85, 5)]), 5.23)
        self.assertEqual(roll_length(0.6, 0.85, 5), 1.4)
        self.assertEqual(roll_length(1, 1, 10), 5.5)
        idx = next(i for i, c in enumerate(self.app.clients) if c is self.sasha)
        self.app.clients.append({'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True, 'history': []})
        main.ensure_ids(self.app.clients)
        oleg = len(self.app.clients) - 1
        for desc in ('5.43x2.5 x1шт', '3x2 x2шт'):
            self.assertTrue(self.screen._final_save(idx, '1 000 руб', None, 'banner_black', order_desc=desc,
                                                    via_malevich=True, creditor_idx=oleg))
        self.screen._final_save(idx, '500 руб', None, 'banner_white', order_desc='1x1 x1шт')
        self.assertEqual(printed_meters(self.app, 'black'), (9.73, 2))
        self.assertEqual(printed_meters(self.app, 'black', datetime.now() + timedelta(hours=1)), (0, 0))
        made = []
        orig = main.RoundedButton.__init__

        def rec(btn, **kw):
            orig(btn, **kw); made.append(btn)
        main.RoundedButton.__init__ = rec
        try:
            self.screen.show_rolls_log()
            [b for b in made if isinstance(b, main.EditButton)][0].dispatch('on_release')   # чёрный
            from kivy.uix.textinput import TextInput
            save = [b for b in made if b.text == 'СОХРАНИТЬ'][-1]
            inp = [w for w in save.parent.walk() if isinstance(w, TextInput)][0]
            inp.text = '12'
            save.dispatch('on_release')
        finally:
            main.RoundedButton.__init__ = orig
        adj = self.app._extra_data['printed_adj']['black']
        self.assertEqual(adj['m'], round(12 - 9.73, 2))

    def test_order_writes_off_roll_meters(self):
        from accounting import purchase_banner as pb
        self.app.rolls = [{'color': 'black', 'width': '3.2', 'total': '50', 'remain': '13.5'}]
        idx = next(i for i, c in enumerate(self.app.clients) if c is self.sasha)
        self.app.clients.append({'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True, 'history': []})
        main.ensure_ids(self.app.clients)
        oleg = len(self.app.clients) - 1
        own = self.screen._final_save
        self.assertTrue(own(idx, '1 000 руб', None, 'banner_black', order_desc='4x3 x1шт'))   # «Свой рулон»
        self.assertEqual(self.app.rolls[0]['remain'], '13.5')                                 # — метры не трогает

        def via(i, t, b, mode, order_desc=None, via_malevich=True):
            return own(i, t, b, mode, order_desc=order_desc, via_malevich=via_malevich, creditor_idx=oleg if via_malevich else None)
        self.screen._final_save = via
        self.assertTrue(self.screen._final_save(idx, '5 400 руб', None, 'banner_black', order_desc='4.5x3 x2шт'))
        first = self.sasha['history'][-1]
        self.assertEqual(first['roll_m'], 9.2)                      # 2 × (4.5+0.1), ширина 3.1 влезает
        self.assertEqual(self.app.rolls[0]['remain'], '4.3')
        self.assertTrue(self.screen._final_save(idx, '2 132 руб', None, 'banner_black', order_desc='2.6x4.1 x1шт'))
        self.assertEqual(self.app.rolls[0]['remain'], '0.1')         # 2.7 поперёк, длина 4.2
        self.assertTrue(self.screen._final_save(idx, '3 600 руб', None, 'banner_black', order_desc='6x3 x1шт'))
        self.assertEqual(self.app.rolls[0]['remain'], '-6')          # в минус — до нового рулона
        self.assertTrue(pb(self.app, 'black', 9000, '3.2', 50)[0])  # закупка с метрами — в тот же рулон
        self.assertEqual(len([r for r in self.app.rolls if r['color'] == 'black']), 1)
        self.assertEqual(self.app.rolls[0]['remain'], '44')
        self.assertTrue(reverse_order(self.app, self.sasha, first)[0])
        self.assertEqual(self.app.rolls[0]['remain'], '53.2')        # отмена заказа вернула метры
        self.assertTrue(self.screen._final_save(idx, '500 руб', None, 'banner_white', order_desc='1x1 x1шт'))
        self.assertEqual([r['color'] for r in self.app.rolls], ['black', 'white'])   # белого не было — заведён
        self.assertEqual(self.app.rolls[1]['remain'], '-1.1')
        self.screen._final_save = own
        self.assertEqual(main.check_integrity(self.app), [])
        self.screen.show_rolls_log()
        self.screen.show_rolls_inventory()

    def test_migration_writes_off_2311_once(self):
        import json
        data = {'clients': [
            {'name': 'САША', 'debt': '20000', 'cid': 's', 'history': [
                {'oid': 'a', 'date': '23.11.26 12:10', 'desc': '6x3 x3шт', 'sum': '10800', 'mode': 'banner_black', 'via_malevich': True, 'creditor_id': 'o', 'creditor_name': 'ОЛЕГ', 'print_cost': 0},
                {'oid': 'b', 'date': '23.11.26 12:11', 'desc': '4.5x3 x2шт', 'sum': '5400', 'mode': 'banner_black', 'via_malevich': True, 'creditor_id': 'o', 'creditor_name': 'ОЛЕГ', 'print_cost': 0},
                {'oid': 'c', 'date': '23.11.26 12:12', 'desc': '2.6x4.1 x1шт', 'sum': '2132', 'mode': 'banner_black', 'via_malevich': True, 'creditor_id': 'o', 'creditor_name': 'ОЛЕГ', 'print_cost': 0},
                {'oid': 'd', 'date': '22.11.26 12:12', 'desc': '1x1 x1шт', 'sum': '200', 'mode': 'banner_black', 'via_malevich': True, 'creditor_id': 'o', 'creditor_name': 'ОЛЕГ', 'print_cost': 0},
                {'oid': 'e', 'date': '23.11.26 12:13', 'desc': '3x6 x1шт', 'sum': '2700', 'mode': 'banner_white', 'via_malevich': True, 'creditor_id': 'o', 'creditor_name': 'ОЛЕГ', 'print_cost': 0}]},
            {'name': 'МАЛЕВИЧ', 'debt': '1808', 'cid': 'm', 'history': [
                {'oid': 'f', 'date': '23.11.26 13:30', 'desc': '5.13x2.35 x1шт', 'sum': '1808', 'mode': 'banner_white',
                 'via_malevich': True, 'creditor_name': 'ОЛЕГ', 'creditor_id': 'o', 'print_cost': 0}]},
            {'name': 'МАЛЕВИЧ', 'debt': '0', 'cid': 'mk', 'is_creditor': True, 'history': []},
            {'name': 'ОЛЕГ', 'debt': '0', 'cid': 'o', 'is_creditor': True, 'history': []}],
            'profit_correction': '0', 'roles_version': 1, 'profit_model': 2,
            'rolls': [{'color': 'white', 'width': '3.2', 'total': '75', 'remain': '18'},
                      {'color': 'black', 'width': '3.2', 'total': '50', 'remain': '13.5'}]}
        with open(main.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        app = main.BusinessApp(); main.App._running_app = app
        app.load_data()
        rem = {r['color']: r['remain'] for r in app.rolls}
        self.assertEqual(rem, {'black': '-18.2', 'white': '6.67'})   # белый: 3x6 Саши и 5.13x2.35 Малевича — по отдельности
        app.save_data()
        app2 = main.BusinessApp(); main.App._running_app = app2
        app2.load_data()
        self.assertEqual({r['color']: r['remain'] for r in app2.rolls}, rem)   # второй раз не списывает

    def test_zero_writeoff_is_logged(self):
        self.app.rolls = [{'color': 'white', 'width': '3.2', 'total': '50', 'remain': '18'}]
        idx = next(i for i, c in enumerate(self.app.clients) if c is self.sasha)
        self.app.clients.append({'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True, 'history': []})
        main.ensure_ids(self.app.clients)
        oleg = len(self.app.clients) - 1
        for d in ('5.13x2.35 x1шт', '0.85x0.6 x5шт'):
            self.assertTrue(self.screen._final_save(idx, '1 000 руб', None, 'banner_white', order_desc=d,
                                                    via_malevich=True, creditor_idx=oleg))
        self.assertEqual(self.app.rolls[0]['remain'], '12.77')          # мелкие встали рядом с большим (тот же клиент)
        last = self.app._extra_data['roll_log'][-1]
        self.assertEqual((last['m'], last['note']), (0.0, 'рядом'))
        self.app.clients.append({'name': 'СЕРЕГА', 'debt': '0', 'history': []})       # другой клиент — отдельно
        main.ensure_ids(self.app.clients)
        self.assertTrue(self.screen._final_save(len(self.app.clients) - 1, '510 руб', None, 'banner_white',
                                                order_desc='0.85x0.6 x5шт', via_malevich=True, creditor_idx=oleg))
        self.assertEqual(self.app.rolls[0]['remain'], '11.37')          # 3 в ряд, 2 ряда по 0.7
        self.screen.show_rolls_log()

    def test_migration_per_client_recounts_zero(self):
        import json
        data = {'clients': [
            {'name': 'СЕРЕГА', 'debt': '510', 'cid': 's2', 'history': [
                {'oid': 'g', 'date': '23.11.26 14:00', 'desc': '0.85x0.6 x5шт', 'sum': '510', 'mode': 'banner_white',
                 'via_malevich': True, 'creditor_id': 'o', 'creditor_name': 'ОЛЕГ', 'print_cost': 0,
                 'roll_m': 0.0, 'roll_rid': 'w1'}]},
            {'name': 'МАЛЕВИЧ', 'debt': '0', 'cid': 'mk', 'is_creditor': True, 'history': []},
            {'name': 'ОЛЕГ', 'debt': '0', 'cid': 'o', 'is_creditor': True, 'history': []}],
            'profit_correction': '0', 'roles_version': 1, 'profit_model': 2, 'roll_writeoff_2311b': True,
            'rolls': [{'color': 'white', 'width': '3.2', 'total': '75', 'remain': '6.67', 'rid': 'w1'}]}
        with open(main.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        app = main.BusinessApp(); main.App._running_app = app
        app.load_data()
        self.assertEqual(app.rolls[0]['remain'], '5.27')                 # 6.67 − 1.4

    def test_payback_via_executor_uses_margin(self):
        self.assertTrue(purchase_banner(self.app, 'black', 6000)[0])
        self.app.clients.append({'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True, 'history': []})
        main.ensure_ids(self.app.clients)
        idx = next(i for i, c in enumerate(self.app.clients) if c is self.sasha)
        self.assertTrue(self.screen._final_save(idx, '1 000 руб', None, 'banner_black', print_cost=550,
                                                via_malevich=True, creditor_idx=len(self.app.clients) - 1,
                                                order_desc='1x1 x1шт'))
        self.assertEqual(self.black()['debt'], '5 550')      # в рулон — только 450, что остаётся мне
        self.assertEqual(self.profit(), 0)                   # прибыль стоит, в минус не уходит

    def test_roll_window_paid_goes_to_minus(self):
        made = []
        orig = main.RoundedButton.__init__

        def rec(btn, **kw):
            orig(btn, **kw); made.append(btn)
        main.RoundedButton.__init__ = rec
        try:
            self.app.rolls = [{'color': 'black', 'width': '3.2', 'total': '50', 'remain': '-5'}]
            self.screen._roll_edit_popup(0, None)
            from kivy.uix.textinput import TextInput
            save = [b for b in made if b.text == 'СОХРАНИТЬ'][-1]
            [b for b in made if b.text == '+75 м'][-1].dispatch('on_release')
            pay = [w for w in save.parent.walk() if isinstance(w, TextInput) and w.hint_text == '0'][0]
            pay.text = '13000'
            save.dispatch('on_release')
        finally:
            main.RoundedButton.__init__ = orig
        self.assertEqual(self.app.rolls[0]['remain'], '70')
        self.assertEqual(self.black()['debt'], '13 000')
        self.assertEqual(self.profit(), 0)

    def test_purchase_menu_opens_roll_window(self):
        made = []
        orig = main.RoundedButton.__init__

        def rec(btn, **kw):
            orig(btn, **kw); made.append(btn)
        main.RoundedButton.__init__ = rec
        try:
            self.app.rolls = [{'color': 'white', 'width': '3.2', 'total': '75', 'remain': '-2'}]
            self.screen._open_purchase_roll('white')
            from kivy.uix.textinput import TextInput
            save = [b for b in made if b.text == 'СОХРАНИТЬ'][-1]
            [b for b in made if b.text == '+75 м'][-1].dispatch('on_release')
            pay = [w for w in save.parent.walk() if isinstance(w, TextInput) and w.hint_text == '0'][0]
            pay.text = '12000'
            save.dispatch('on_release')
        finally:
            main.RoundedButton.__init__ = orig
        self.assertEqual(len(self.app.rolls), 1)
        self.assertEqual(self.app.rolls[0]['remain'], '73')
        white = self.app.clients[self.app.get_special_clients()[2]]
        self.assertEqual(white['debt'], '12 000')

    def test_payer_oleg_adds_to_my_debt(self):
        made = []
        orig = main.RoundedButton.__init__

        def rec(btn, **kw):
            orig(btn, **kw); made.append(btn)
        main.RoundedButton.__init__ = rec
        self.app.clients.append({'name': 'ОЛЕГ', 'debt': '6665', 'is_creditor': True, 'history': []})
        main.ensure_ids(self.app.clients)
        oleg = self.app.clients[-1]
        try:
            self.app.rolls = [{'color': 'black', 'width': '3.2', 'total': '50', 'remain': '-18.2'}]
            self.screen._open_purchase_roll('black')
            from kivy.uix.textinput import TextInput
            save = [b for b in made if b.text == 'СОХРАНИТЬ'][-1]
            [b for b in made if b.text == '+50 м'][-1].dispatch('on_release')
            [b for b in made if b.text == 'ОЛЕГ'][-1].dispatch('on_release')
            pay = [w for w in save.parent.walk() if isinstance(w, TextInput) and w.hint_text == '0'][0]
            pay.text = '11760'
            save.dispatch('on_release')
        finally:
            main.RoundedButton.__init__ = orig
        self.assertEqual(oleg['debt'], '18 425')                       # мой долг Олегу вырос
        self.assertEqual(self.black()['debt'], '11 760')               # рулон окупается
        self.assertEqual(self.app.rolls[0]['remain'], '31.8')
        self.assertEqual(self.profit(), 0)
        self.assertTrue(any('заплатил ОЛЕГ' in str(j.get('op')) for j in self.app.journal))

    def test_migration_oleg_black_2311(self):
        import json
        data = {'clients': [
            {'name': 'ЧЕРНЫЙ БАНЕР', 'debt': '11760', 'role': 'black', 'cid': 'b'},
            {'name': 'МАЛЕВИЧ', 'debt': '0', 'cid': 'mk', 'is_creditor': True},
            {'name': 'ОЛЕГ', 'debt': '6665', 'cid': 'o', 'is_creditor': True}],
            'profit_correction': '0', 'roles_version': 1, 'profit_model': 2,
            'roll_writeoff_2311b': True, 'roll_writeoff_2311c': True,
            'journal': [{'t': '2026-11-23 19:50:00', 'op': 'закупка банера', 'cid': 'b', 'name': 'ЧЕРНЫЙ БАНЕР',
                         'was': '0', 'now': '11760'}]}
        with open(main.DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        for _ in range(2):                                              # второй запуск не прибавляет снова
            app = main.BusinessApp(); main.App._running_app = app
            app.load_data()
            oleg = next(c for c in app.clients if c.get('name') == 'ОЛЕГ')
            self.assertEqual(oleg['debt'], '18 425')
        self.assertTrue(any('ОЛЕГ' in str(j.get('op')) and j.get('cid') == 'o' for j in app.journal))

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
