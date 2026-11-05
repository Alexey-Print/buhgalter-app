"""Order reversals and persistence helpers; no UI and no automatic balance rebuild."""
import copy
import json
import math
import os
import tempfile
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def number(value, default=0.0):
    try:
        result = float(str(value).replace(' ', '').replace('\u00a0', '').replace(',', '.'))
        return result if math.isfinite(result) else default
    except (ValueError, TypeError):
        return default


def money(value):
    try:
        d = Decimal(str(value).replace(' ', '').replace('\u00a0', '').replace(',', '.'))
        if not d.is_finite():
            return '0'
        d = d.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return '0'
    if not d:
        return '0'
    return format(d, ',.2f').replace(',', ' ').rstrip('0').rstrip('.')


def ensure_ids(clients):
    used = set()
    for client in clients:
        cid = client.get('cid')
        if not cid or cid in used:
            cid = uuid.uuid4().hex
            client['cid'] = cid
        used.add(cid)


def snapshot(app):
    values = (app.clients, app.profit_correction, app.profit_log, app.rolls)
    originals = {}
    def collect(value):
        if isinstance(value, (dict, list)) and id(value) not in originals:
            originals[id(value)] = value
            for child in (value.values() if isinstance(value, dict) else value):
                collect(child)
    for value in values:
        collect(value)
    memo = {}
    saved = copy.deepcopy(values, memo)
    pairs = {id(memo[key]): original for key, original in originals.items()}
    return saved, pairs


def restore(app, state):
    saved, pairs = state
    visited = set()
    def recover(value):
        if not isinstance(value, (dict, list)):
            return value
        target = pairs.get(id(value), value)
        if id(value) in visited:
            return target
        visited.add(id(value))
        if isinstance(value, dict):
            content = {k: recover(v) for k, v in value.items()}
            target.clear()
            target.update(content)
        else:
            target[:] = [recover(v) for v in value]
        return target
    app.clients, app.profit_correction, app.profit_log, app.rolls = tuple(recover(v) for v in saved)


def atomic_write(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=4, allow_nan=False)
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.business-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return text


def reverse_order(app, client, item):
    """Validate all links before changing anything. Return (success, Russian message)."""
    if not any(c is client for c in app.clients):
        return False, 'Клиент больше не существует'
    history = client.get('history', [])
    if sum(h is item for h in history) != 1:
        return False, 'Заказ уже удалён или история изменилась'
    if item.get('source_oid'):
        return False, 'Удалите исходный заказ клиента: долг исполнителя изменится вместе с ним'
    oid = item.get('oid')
    if oid and sum(h.get('oid') == oid for c in app.clients for h in c.get('history', [])) != 1:
        return False, 'Повторный номер заказа: требуется проверка данных'
    cost = number(item.get('print_cost'))
    val = number(item.get('sum'))
    linked = None
    if item.get('via_malevich') and cost > 0:
        # Name fallback is for the earlier guarded branch only. Never guess a legacy order link.
        candidates = [c for c in app.clients if c.get('is_creditor') and
                      (c.get('cid') == item['creditor_id'] if item.get('creditor_id')
                       else c.get('name') == item.get('creditor_name'))]
        if len(candidates) != 1 or not oid:
            return False, 'Не удалось однозначно найти исполнителя старого заказа'
        creditor = candidates[0]
        matches = [(hist, h) for hist in (creditor.get('history', []), creditor.get('archived_history', []))
                   for h in hist if h.get('source_oid') == oid]
        if len(matches) != 1 or abs(number(matches[0][1].get('sum')) - cost) > .001:
            return False, 'У старого заказа нет точной связи с исполнителем. Долги не изменены'
        linked = creditor, matches[0][0], matches[0][1]
    elif client.get('is_creditor') and not oid:
        return False, 'Старая запись исполнителя: удалите исходный заказ клиента'
    _, _, white, black = app.get_special_clients()
    refunds = []
    for key, idkey, target in (
        ('banner_deduction', 'banner_deduction_id', white if 'banner_white' in item.get('mode', '') else black),
        ('banner_deduction2', 'banner_deduction2_id', black if 'banner_white' in item.get('mode', '') else white)):
        amount = number(item.get(key))
        if amount <= 0:
            continue
        if item.get(idkey):
            found = [c for c in app.clients if c.get('cid') == item[idkey]]
            if len(found) != 1:
                return False, 'Материал заказа не найден. Долги не изменены'
            target_client = found[0]
        elif target is not None:
            # Old secondary index is deliberately ignored: list positions are not identities.
            target_client = app.clients[target]
        else:
            return False, 'Материал старого заказа не найден'
        refunds.append((target_client, amount))
    logs = [p for p in app.profit_log if oid and p.get('oid') == oid]
    if len(logs) > 1:
        return False, 'Повторная запись прибыли: требуется проверка данных'
    if not oid:
        possible = [p for p in app.profit_log if p.get('name') == client.get('name') and p.get('date') == item.get('date')]
        if possible:
            return False, 'У старого заказа нет точной связи с прибылью. Данные не изменены'
    state = snapshot(app)
    try:
        history.pop(next(i for i, h in enumerate(history) if h is item))
        client['debt'] = money(number(client.get('debt')) - val)
        app.profit_correction = money(number(app.profit_correction) + cost)
        if linked:
            creditor, chistory, charge = linked
            creditor['debt'] = money(number(creditor.get('debt')) - cost)
            chistory.remove(charge)
        for material, amount in refunds:
            material['debt'] = money(number(material.get('debt')) + amount)
            app.profit_correction = money(number(app.profit_correction) + amount)
        app.profit_log[:] = [p for p in app.profit_log if not (oid and p.get('oid') == oid)]
        if app.save_data() is not True:
            raise OSError('Сохранение не подтверждено')
    except Exception as exc:
        restore(app, state)
        return False, 'Не удалось сохранить; операция отменена: ' + str(exc)
    return True, 'Заказ удалён'


def purchase_banner(app, color, amount, width='', length=0):
    amount = number(amount)
    length = number(length)
    if amount <= 0 or color not in ('white', 'black') or length < 0:
        return False, 'Введите положительную сумму закупки'
    _, _, white, black = app.get_special_clients()
    index = white if color == 'white' else black
    if index is None:
        return False, 'Материал не найден'
    state = snapshot(app)
    try:
        client = app.clients[index]
        debt = number(client.get('debt'))
        total = number(client.get('zakupka_total', max(0, debt)))
        client['debt'] = money(debt + amount)
        client['zakupka_total'] = money(total + amount)
        from datetime import datetime
        client.setdefault('purchase_log', []).append({'date': datetime.now().strftime('%d.%m.%y %H:%M'), 'sum': money(amount)})
        if length > 0:
            app.rolls.append({'color': color, 'width': str(width).strip() or '0', 'total': money(length), 'remain': money(length)})
        if app.save_data() is not True:
            raise OSError('Сохранение не подтверждено')
    except Exception as exc:
        restore(app, state)
        return False, 'Закупка не сохранена: ' + str(exc)
    return True, 'Закупка сохранена'


def clear_history(app, client):
    state = snapshot(app)
    try:
        history = client.setdefault('history', [])
        oids = {h.get('oid') for h in history if h.get('oid')}
        client.setdefault('archived_history', []).extend(history)
        history.clear()
        app.profit_log[:] = [p for p in app.profit_log if p.get('oid') not in oids]
        if app.save_data() is not True:
            raise OSError('Сохранение не подтверждено')
    except Exception as exc:
        restore(app, state)
        return False, 'История не очищена: ' + str(exc)
    return True, 'История очищена'


def period_totals(app, in_period):
    creditors, remainder, white, black = app.get_special_clients()
    excluded = set(creditors + [remainder, white, black])
    revenue = printing = purchases = 0.0
    for i, client in enumerate(app.clients):
        if i in (white, black):
            purchases += sum(number(h.get('sum')) for h in client.get('purchase_log', []) if in_period(h.get('date')))
        if i in excluded:
            continue
        for h in client.get('archived_history', []) + client.get('history', []):
            if h and in_period(h.get('date')):
                revenue += number(h.get('sum'))
                printing += number(h.get('print_cost'))
    return tuple(round(v, 2) for v in (revenue, printing, purchases, revenue - printing - purchases))
