[app]

title = Uchet
package.name = uchet
package.domain = com.aleksey

source.dir = .
source.include_exts = py,png,jpg,jpeg,json

version = 1.0

requirements = python3,kivy

icon.filename = %(source.dir)s/icon.png

orientation = portrait
fullscreen = 0

android.permissions =
android.archs = arm64-v8a
android.allow_backup = 1
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
