"""Экспорт и импорт всей базы «Учёта» одним JSON-файлом.

Экспорт: копия базы в общую папку «Документы/Учёт» (на Android — через MediaStore, без разрешений).
Импорт: выбор файла, проверка формата, показ итогов было/станет, обязательная проверенная
резервная копия текущей базы, атомарная замена и откат при любой ошибке.
"""
import copy
import json
import os
from datetime import datetime

from accounting import atomic_write, money

ON_ANDROID = bool(os.environ.get('ANDROID_ARGUMENT'))


def export_name():
    return 'Учёт_база_' + datetime.now().strftime('%Y%m%d_%H%M') + '.json'


def export_text(app):
    return json.dumps(app._current_data(), ensure_ascii=False, indent=4, allow_nan=False)


def export_to_file(app, folder):
    """Записать копию базы в папку (используется и на Android как промежуточный файл)."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, export_name())
    text = export_text(app)
    atomic_write(path, json.loads(text))
    with open(path, 'r', encoding='utf-8') as f:
        if f.read() != text:
            raise OSError('Копия не совпадает с базой')
    return path


def export_database(app, base_path):
    """Вернуть понятное описание, куда сохранена копия."""
    if not ON_ANDROID:
        return export_to_file(app, os.path.join(base_path, 'exports'))
    from androidstorage4kivy import SharedStorage
    storage = SharedStorage()
    private = export_to_file(app, storage.get_cache_dir())
    shared = storage.copy_to_shared(private)   # Документы/<название приложения>/файл
    os.unlink(private)
    if not shared:
        raise OSError('Android не разрешил сохранить файл в «Документы»')
    return 'Документы/' + storage.get_app_title() + '/' + os.path.basename(private)


def read_import(path):
    """Прочитать и проверить файл базы. Ошибка — понятным текстом."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as exc:
        raise ValueError('Файл не читается как база «Учёта»: ' + str(exc))
    if not isinstance(data, dict) or not isinstance(data.get('clients'), list) or not data['clients']:
        raise ValueError('В файле нет списка клиентов — это не база «Учёта»')
    for c in data['clients']:
        if not isinstance(c, dict) or not isinstance(c.get('name', ''), str):
            raise ValueError('В файле повреждена карточка клиента')
    return data


def summarize(app_class, data):
    """Итоги базы из файла теми же правилами, что и в программе (без записи на диск)."""
    tmp = app_class.__new__(app_class)   # без запуска второго приложения Kivy
    tmp.clients = copy.deepcopy(data['clients'])
    tmp.profit_correction = data.get('profit_correction', '0')
    tmp._extra_data = {k: v for k, v in data.items() if k in ('roles_version', 'profit_model')}
    tmp.profit_log = copy.deepcopy(data.get('profit_log', []))
    tmp.migrate_roles()
    tmp.migrate_profit_model()
    return tmp.get_totals()


def describe_totals(totals):
    debts, mine, deficit, profit = totals
    return (f'Мне должны: {money(debts)} р\nЯ должен: {money(mine)} р\n'
            f'Банер (минус): {money(deficit)} р\nПрибыль: {money(profit)} р')


def apply_import(app, data, data_file):
    """Заменить базу данными из файла. Сначала — проверенная копия текущей базы.
    Если новая база не открывается — возвращаем прежнюю. Возвращает путь копии."""
    backup = app.write_verified_backup()
    with open(backup, 'r', encoding='utf-8') as f:
        previous = json.load(f)
    try:
        atomic_write(data_file, data)
        app._journal_base = None
        app.load_data()
    except Exception:
        atomic_write(data_file, previous)
        app._journal_base = None
        app.load_data()
        raise
    return backup


def choose_import_file(on_path):
    """Android: системное окно выбора файла; on_path(путь_во_временной_папке) на главном потоке."""
    from kivy.clock import Clock
    from androidstorage4kivy import Chooser, SharedStorage

    def picked(uris):
        def handle(dt):
            if uris:
                path = SharedStorage().copy_from_shared(uris[0])
                on_path(path)
        Clock.schedule_once(handle, 0)

    chooser = Chooser(picked)
    chooser.choose_content('*/*')
    return chooser
