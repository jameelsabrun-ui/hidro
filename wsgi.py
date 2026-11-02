"""
Entry point untuk SERVER PRODUKSI (gunicorn).

File ini hanya dipakai saat deploy di VPS / server. Saat belajar di komputer
sendiri, tetap jalankan `python app.py` seperti biasa.

Cara pakai (dari folder proyek):
    gunicorn --workers 2 --bind 127.0.0.1:8000 --preload wsgi:app

Penjelasan singkat:
- `wsgi:app`  -> ambil variabel bernama `app` dari file wsgi.py ini.
- `--preload` -> aplikasi dimuat SEKALI di proses induk sebelum worker dibuat,
                 sehingga init_db() di bawah hanya berjalan satu kali.
"""
from app import app, init_db

# Pastikan tabel database sudah dibuat saat server produksi mulai.
# Dengan `--preload`, baris ini hanya dijalankan sekali (aman untuk multi-worker).
init_db()
