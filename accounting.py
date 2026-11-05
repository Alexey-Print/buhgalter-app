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
    values = (app.clients, app.profit_correction, app.profit_log, app.rolls,
              getattr(app, 'prices', []), getattr(app, 'plenka_prices', []), getattr(app, 'print_cost', '55'))
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
    (app.clients, app.profit_correction, app.profit_log, app.rolls,
     app.prices, app.plenka_prices, app.print_cost) = tuple(recover(v) for v in saved)


def commit(app, state, op=''):
    """Сохранить изменения; при любой ошибке вернуть память к снимку state."""
    app._op = op
    try:
        if app.save_data() is not True:
            raise OSError('Сохранение не подтверждено')
    except Exception as exc:
        restore(app, state)
        return False, 'Не сохранено, повторите: ' + str(exc)
    return True, 'Сохранено'


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
        app._op = 'удаление заказа: ' + str(item.get('desc', ''))
        if app.save_data() is not True:
            raise OSError('Сохранение не подтверждено')
    except Exception as exc:
        restore(app, state)
        return False, 'Не удалось сохранить; операция отменена: ' + str(exc)
    return True, 'Заказ удалён'


def _dec(value):
    return Decimal(money(value).replace(' ', ''))


def is_ordinary_client(app, client):
    """Обычный клиент: не исполнитель, не баннерный материал и не остаток баннера."""
    creditors, remainder, white, black = app.get_special_clients()
    idx = next((i for i, c in enumerate(app.clients) if c is client), None)
    return idx is not None and idx not in creditors and idx not in (remainder, white, black)


def payment_result(old_value, paid):
    """«Отдал» гасит долг в сторону нуля; положительный долг может уйти в переплату."""
    old, paid = _dec(old_value), _dec(paid)
    if old >= 0:
        return old - paid
    return min(Decimal('0'), old + paid)


def change_balance(app, client, new_value, name=None, op='правка долга'):
    """Изменить долг (и имя) одной транзакцией. Прибыль меняется только при росте
    положительной части долга; оплата, переплата и её возврат прибыль не меняют."""
    if not any(c is client for c in app.clients):
        return False, 'Клиент больше не существует'
    state = snapshot(app)
    try:
        old, new = _dec(client.get('debt')), _dec(new_value)
        zero = Decimal('0')
        if is_ordinary_client(app, client):
            delta = (old - new) + max(zero, max(zero, new) - max(zero, old))
            if delta:
                app.profit_correction = money(_dec(app.profit_correction) + delta)
        if name is not None:
            client['name'] = name
        client['debt'] = money(new)
        if new == 0:
            client['zakupka_total'] = '0'
        app._op = op
        if app.save_data() is not True:
            raise OSError('Сохранение не подтверждено')
    except Exception as exc:
        restore(app, state)
        return False, 'Не сохранено, повторите: ' + str(exc)
    return True, 'Сохранено'


def creditor_is_referenced(app, creditor):
    """Есть ли заказы клиентов (активные или архивные), связанные с этим исполнителем."""
    cid, name = creditor.get('cid'), creditor.get('name')
    for client in app.clients:
        if client is creditor:
            continue
        for h in client.get('history', []) + client.get('archived_history', []):
            if h.get('via_malevich') and ((cid and h.get('creditor_id') == cid) or
                                         (not h.get('creditor_id') and h.get('creditor_name') == name)):
                return True
    return bool(creditor.get('history') or creditor.get('archived_history')) and \
        any(h.get('source_oid') for h in creditor.get('history', []) + creditor.get('archived_history', []))


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
        app._op = 'закупка банера'
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


def prepare_android_storage(files_root):
    """Copy legacy data before first use; never replace current data or delete the old copy.

    UchetActivity unpacks to uchet_runtime, so the previous /files/app survives
    Android's asset cleanup. Business data lives outside both runtime directories.
    """
    import shutil
    destination = os.path.join(files_root, 'uchet_data')
    legacy = os.path.join(files_root, 'app')
    os.makedirs(destination, exist_ok=True)

    def preserve(source, target):
        if os.path.isfile(source) and not os.path.exists(target):
            fd, tmp = tempfile.mkstemp(prefix='.migrate-', dir=os.path.dirname(target))
            try:
                with os.fdopen(fd, 'wb') as out, open(source, 'rb') as inp:
                    shutil.copyfileobj(inp, out)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(tmp, target)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    preserve(os.path.join(legacy, 'business_data.json'), os.path.join(destination, 'business_data.json'))
    old_backups = os.path.join(legacy, 'backups')
    if os.path.isdir(old_backups):
        new_backups = os.path.join(destination, 'backups')
        os.makedirs(new_backups, exist_ok=True)
        for name in os.listdir(old_backups):
            if name.startswith('business_data_') and name.endswith('.json'):
                preserve(os.path.join(old_backups, name), os.path.join(new_backups, name))
    return destination


JOURNAL_LIMIT = 20000
PROFIT_KEY = '__profit__'


def journal_balances(app):
    """Текущие долги по постоянным cid и корректировка прибыли — основа журнала."""
    result = {c.get('cid'): (c.get('name', ''), money(c.get('debt'))) for c in app.clients if c.get('cid')}
    result[PROFIT_KEY] = ('ПРИБЫЛЬ (корректировка)', money(app.profit_correction))
    return result


def journal_entries(base, now, op):
    """Строки журнала «было → стало» для всех изменившихся сумм."""
    if base is None:
        return []
    from datetime import datetime
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entries = []
    for key in list(base) + [k for k in now if k not in base]:
        was, cur = base.get(key), now.get(key)
        was_sum = was[1] if was else None
        cur_sum = cur[1] if cur else None
        if was_sum != cur_sum:
            label = op
            if was is None and op == 'изменение':
                label = 'новая карточка'
            elif cur is None and op == 'изменение':
                label = 'карточка удалена'
            entries.append({'t': stamp, 'op': label, 'cid': key, 'name': (cur or was)[0],
                            'was': was_sum, 'now': cur_sum})
    return entries


def check_integrity(app):
    """Автоматическая перепроверка базы. Возвращает список понятных замечаний (пустой — всё сходится)."""
    problems = []
    cids = [c.get('cid') for c in app.clients]
    if len(set(cids)) != len(cids):
        problems.append('Повторяются номера карточек клиентов')
    orders = {}
    for c in app.clients:
        for h in c.get('history', []) + c.get('archived_history', []):
            if h.get('oid'):
                orders.setdefault(h['oid'], []).append((c, h))
    for oid, found in orders.items():
        if len(found) > 1:
            problems.append(f'Заказ записан дважды: {found[0][0].get("name", "")}')
    charges = {}
    for c in app.clients:
        if not c.get('is_creditor'):
            continue
        for h in c.get('history', []) + c.get('archived_history', []):
            if h.get('source_oid'):
                charges.setdefault(h['source_oid'], []).append((c, h))
    for oid, found in charges.items():
        creditor, charge = found[0]
        if len(found) > 1:
            problems.append(f'{creditor.get("name", "")}: начисление за печать записано дважды')
        if oid not in orders:
            problems.append(f'{creditor.get("name", "")}: начисление {money(charge.get("sum"))} без заказа клиента')
    by_cid = {c.get('cid'): c for c in app.clients}
    for oid, found in orders.items():
        client, order = found[0]
        if order.get('via_malevich') and order.get('creditor_id') and number(order.get('print_cost')) > 0:
            linked = charges.get(oid, [])
            if len(linked) != 1:
                problems.append(f'{client.get("name", "")}: у заказа нет начисления исполнителю')
            elif abs(number(linked[0][1].get('sum')) - number(order.get('print_cost'))) > .001:
                problems.append(f'{client.get("name", "")}: сумма печати не совпадает у исполнителя')
            elif linked[0][0].get('cid') != order['creditor_id']:
                problems.append(f'{client.get("name", "")}: начисление записано другому исполнителю')
        for idkey in ('banner_deduction_id', 'banner_deduction2_id'):
            if order.get(idkey) and order[idkey] not in by_cid:
                problems.append(f'{client.get("name", "")}: материал заказа не найден')
    last = {}
    for e in getattr(app, 'journal', []) or []:
        last[e.get('cid')] = e.get('now')
    current = journal_balances(app)
    for key, value in last.items():
        if value is not None and key in current and current[key][1] != value:
            problems.append(f'{current[key][0]}: сумма изменена мимо журнала '
                            f'(по журналу {value}, сейчас {current[key][1]})')
    return problems


def _norm_name(name):
    return ' '.join(str(name or '').lower().replace('ё', 'е').split())


def link_partners(app):
    """Связать обычного клиента и исполнителя с одинаковым именем (один и тот же человек).
    Связь постоянная (по cid) и не зависит от последующего переименования."""
    by_cid = {c.get('cid'): c for c in app.clients}
    for client in app.clients:
        if client.get('is_creditor') or not is_ordinary_client(app, client):
            continue
        partner = by_cid.get(client.get('partner_cid'))
        if partner is not None and partner.get('is_creditor'):
            continue
        same = [c for c in app.clients if c.get('is_creditor') and c is not client
                and _norm_name(c.get('name')) == _norm_name(client.get('name'))
                and by_cid.get(c.get('partner_cid')) in (None, client)]
        if len(same) == 1:
            client['partner_cid'] = same[0].get('cid')
            same[0]['partner_cid'] = client.get('cid')


def net_partners(app):
    """Автоматический взаимозачёт: долг человека мне и мой долг ему гасятся друг о друга.
    Итог: остаётся только одна сторона. Прибыль не меняется (как при оплате)."""
    link_partners(app)
    by_cid = {c.get('cid'): c for c in app.clients}
    changed = False
    for client in app.clients:
        creditor = by_cid.get(client.get('partner_cid'))
        if client.get('is_creditor') or creditor is None or not creditor.get('is_creditor'):
            continue
        if creditor.get('partner_cid') != client.get('cid') or not is_ordinary_client(app, client):
            continue
        mine, theirs = _dec(client.get('debt')), _dec(creditor.get('debt'))
        position = mine - theirs          # > 0 — он должен мне, < 0 — я должен ему
        zero = Decimal('0')
        new_mine, new_theirs = (position, zero) if position >= 0 else (zero, -position)
        if new_mine != mine or new_theirs != theirs:
            app.profit_correction = money(_dec(app.profit_correction) + (mine - new_mine))
            client['debt'] = money(new_mine)
            creditor['debt'] = money(new_theirs)
            changed = True
    return changed
