"""Текущая прибыль: общая не меняется, текущая уменьшается на «ОТДАЛ», обнуляется, переживает перезапуск."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['KIVY_NO_ARGS'] = '1'
import main
from accounting import money


class CurrentProfitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_base, self.old_file = main.BASE_PATH, main.DATA_FILE
        main.BASE_PATH, main.DATA_FILE = self.tmp.name, self.tmp.name + '/business_data.json'
        self.app = main.BusinessApp()
        main.App._running_app = self.app
        self.app.load_data()
        self.app.clients.append({'name': 'САША', 'debt': '0', 'history': []})
        self.s = main.ClientsScreen(name='t')
        self.s.refresh_list = lambda: None
        self.s._stub_popup = lambda t, m: None
        self.app.save_data()
        self.idx = len(self.app.clients) - 1

    def tearDown(self):
        main.BASE_PATH, main.DATA_FILE = self.old_base, self.old_file
        self.tmp.cleanup()

    def order(self, amount):
        self.assertTrue(self.s._final_save(self.idx, money(amount) + ' руб', None, 'dop', order_desc='Допобработка'))

    def test_example(self):
        self.order(100)
        total0 = self.app.get_totals()[3]
        self.assertEqual(self.app.current_profit(), total0)
        ok, _ = self.app.take_profit('70')
        self.assertTrue(ok)
        self.assertEqual(self.app.get_totals()[3], total0)              # общая та же
        self.assertEqual(self.app.current_profit(), round(total0 - 70, 2))
        self.order(20)                                                  # новый заказ: обе растут
        self.assertEqual(self.app.get_totals()[3], total0 + 20)
        self.assertEqual(self.app.current_profit(), round(total0 - 50, 2))
        self.app.load_data()                                            # переживает перезапуск
        self.assertEqual(self.app.current_profit(), round(total0 - 50, 2))
        self.assertTrue(self.app.take_profit(reset=True)[0])
        self.assertEqual(self.app.current_profit(), 0)
        self.assertEqual(self.app.get_totals()[3], total0 + 20)
        self.assertEqual([t['kind'] for t in self.app.profit_takes], ['вычтено', 'обнулено'])

    def test_bad_amount_and_failure(self):
        self.order(100)
        cur = self.app.current_profit()
        self.assertFalse(self.app.take_profit('0')[0])
        self.assertFalse(self.app.take_profit('abc')[0])
        self.app.save_data = lambda: False
        self.assertFalse(self.app.take_profit('30')[0])
        self.assertEqual(self.app.current_profit(), cur)
        self.assertEqual(self.app.profit_takes, [])


class CurrentProfitEditTests(CurrentProfitTests):
    def test_note_set_and_undo(self):
        self.order(100)
        total = self.app.get_totals()[3]
        self.assertTrue(self.app.take_profit('30', note='Олегу за краску')[0])
        e = self.app.profit_takes[-1]
        self.assertEqual(e['note'], 'Олегу за краску')
        self.assertTrue(self.app.take_profit(set_to='50')[0])          # «СДЕЛАТЬ =»
        self.assertEqual(self.app.current_profit(), 50)
        self.assertTrue(self.app.undo_take(e)[0])                       # удалили «вычтено 30» — вернулось
        self.assertEqual(self.app.current_profit(), 80)
        self.assertEqual(self.app.get_totals()[3], total)
        self.assertFalse(self.app.undo_take(e)[0])                      # второй раз нельзя
        self.assertFalse(self.app.take_profit(set_to='')[0])


if __name__ == '__main__':
    unittest.main()
