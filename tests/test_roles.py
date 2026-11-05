"""Шаг 3 плана: роли служебных карточек постоянны, имя на роль и итоги не влияет."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main


def legacy_totals(clients, profit_correction):
    """Итоги по правилам старой версии (определение ролей по имени)."""
    m, o, b, k = [], None, None, None
    for i, c in enumerate(clients):
        n = c.get('name', '').lower().strip()
        if c.get('is_creditor') or n == "малевич":
            m.append(i)
        elif n in ("олега", "олег", "баннер остаток"):
            o = i
        elif "белый" in n and "олег" not in n:
            b = i
        elif ("черный" in n or "чёрный" in n) and "олег" not in n:
            k = i
    tot = my = deficit = 0.0
    for i, c in enumerate(clients):
        v = main.safe_float(c.get('debt'))
        if i in m:
            my += v
        elif i in (b, k):
            deficit += v
        elif i != o:
            tot += v
    profit = round(round(tot + main.safe_float(profit_correction), 2) - deficit, 2)
    return tot, my, deficit, 0.0 if abs(profit) < .01 else profit


class RoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def load(self, clients=None, profit='0'):
        if clients is not None:
            Path(main.DATA_FILE).write_text(json.dumps(
                {'clients': clients, 'profit_correction': profit, 'rolls': []}, ensure_ascii=False))
        app = main.BusinessApp()
        main.App._running_app = app
        app.load_data()
        return app

    def legacy_base(self):
        return [
            {'name': 'БАННЕР ОСТАТОК', 'debt': '0', 'm_total': '75', 'm_remain': '40'},
            {'name': 'ОЛЕГ', 'debt': '1200', 'is_creditor': True},
            {'name': 'Малевич', 'debt': '300'},
            {'name': 'НАСТЯ', 'debt': '500'},
            {'name': 'САША', 'debt': '331 593.4'},
            {'name': 'БЕЛЫЙ БАНЕР', 'debt': '2000'},
            {'name': 'ЧЕРНЫЙ БАНЕР', 'debt': '700'},
        ]

    def test_unambiguous_legacy_base_totals_unchanged(self):
        base = self.legacy_base()
        expected = legacy_totals(base, '1500')
        app = self.load(base, '1500')
        self.assertEqual(app.get_totals(), expected)
        roles = {c['name']: c.get('role') for c in app.clients}
        self.assertEqual(roles['БАННЕР ОСТАТОК'], 'remainder')
        self.assertEqual(roles['БЕЛЫЙ БАНЕР'], 'white')
        self.assertEqual(roles['ЧЕРНЫЙ БАНЕР'], 'black')
        self.assertTrue(app.clients[2]['is_creditor'])  # «Малевич» — исполнитель, как раньше
        self.assertEqual(app.role_warning, [])
        self.assertEqual(len(app.clients), len(base))  # лишних карточек нет

    def test_special_words_in_ordinary_names(self):
        app = self.load(self.legacy_base())
        before = app.get_totals()
        for name in ('Черный Сергей', 'Белый дом', 'Олег'):
            with self.subTest(name=name):
                app.clients.append({'name': name, 'debt': '1000'})
                tot, my, deficit, profit = app.get_totals()
                self.assertEqual((tot, my, deficit), (before[0] + 1000, before[1], before[2]))
                app.clients.pop()

    def test_rename_does_not_change_role_or_totals(self):
        app = self.load(self.legacy_base())
        app.clients.append({'name': 'Сергей', 'debt': '1000'})
        before = app.get_totals()
        app.clients[-1]['name'] = 'Черный Сергей'
        self.assertEqual(app.get_totals(), before)
        app.clients[0]['name'] = 'Остаток плёнки'
        _, o, b, k = app.get_special_clients()
        self.assertIs(app.clients[o], app.clients[0])
        self.assertEqual(app.get_totals(), before)

    def test_reload_and_repeated_migration_keep_roles(self):
        app = self.load(self.legacy_base())
        app.clients.append({'name': 'Черный Сергей', 'debt': '1000'})
        app.save_data()
        roles = [(c['name'], c.get('role')) for c in app.clients]
        totals = app.get_totals()
        for _ in range(2):
            again = self.load()
            again.migrate_roles()
            again.ensure_default_clients()
            self.assertEqual([(c['name'], c.get('role')) for c in again.clients], roles)
            self.assertEqual(again.get_totals(), totals)

    def test_ambiguous_base_not_guessed_and_totals_unchanged(self):
        base = [{'name': 'БАННЕР ОСТАТОК', 'debt': '0'},
                {'name': 'ОЛЕГ', 'debt': '0', 'is_creditor': True},
                {'name': 'Белый рулон', 'debt': '100'},
                {'name': 'Белый дом', 'debt': '1000'},
                {'name': 'ЧЕРНЫЙ БАНЕР', 'debt': '0'}]
        expected = legacy_totals(base, '0')
        app = self.load(base)
        self.assertEqual(sorted(app.role_warning), ['Белый дом', 'Белый рулон'])
        self.assertFalse(any(c.get('role') == 'white' for c in app.clients))
        self.assertEqual(app.get_totals(), expected)
        self.assertEqual(len(app.clients), len(base))

    def test_fresh_install_creates_cards_with_roles(self):
        app = self.load()
        roles = sorted(c.get('role') for c in app.clients if c.get('role'))
        self.assertEqual(roles, ['black', 'remainder', 'white'])
        self.assertEqual(sum(1 for c in app.clients if c.get('is_creditor')), 1)


if __name__ == '__main__':
    unittest.main()
