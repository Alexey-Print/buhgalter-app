[app]

# Название приложения (под иконкой)
title = Учёт

# Имя пакета (латиница, без пробелов)
package.name = uchet
package.domain = com.aleksey

# Откуда брать исходники
source.dir = .
source.include_exts = py,png,jpg,jpeg,json

# Версия
version = 1.0

# Зависимости
requirements = python3,kivy

# Иконка приложения (файл icon.png должен лежать рядом)
icon.filename = %(source.dir)s/icon.png

# Ориентация экрана
orientation = portrait
fullscreen = 0

# Разрешения (приложению хранилище не нужно — данные в своей папке)
android.permissions =

# Архитектура (современные телефоны)
android.archs = arm64-v8a

# Разрешить резервную копию системой
android.allow_backup = 1

[buildozer]

log_level = 2
warn_on_root = 1
