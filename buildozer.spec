[app]

title = Uchet
package.name = uchet
package.domain = com.aleksey

source.dir = .
source.include_exts = py,png,jpg,jpeg,json
source.exclude_dirs = tests,backups,.git
source.exclude_patterns = business_data.json*,run_checks.py

version = 1.1

requirements = python3,kivy==2.3.1

icon.filename = %(source.dir)s/icon.png

orientation = portrait
fullscreen = 0

android.entrypoint = com.aleksey.uchet.UchetActivity
android.add_src = android_src

android.permissions =
android.archs = arm64-v8a
android.allow_backup = 1
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True

p4a.branch = develop
p4a.commit = 1c9a4b4f817847bd8505d972d1a0e6f965929a88

[buildozer]
log_level = 2
warn_on_root = 1
