"""Итоги по правилам старой версии 1.0 (роль по имени) — для сравнения при переносе."""
import main


def legacy_totals(clients, profit_correction):
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
