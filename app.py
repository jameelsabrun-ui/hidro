from flask import Flask, render_template, request, jsonify
from datetime import datetime, date
import sqlite3
import random
import os
import time

# Baca konfigurasi dari file .env (jika ada).
# Kalau python-dotenv belum diinstall, aplikasi tetap jalan pakai nilai default.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ==================== KONFIGURASI ====================
app = Flask(__name__)

# --- Pengaturan yang bisa diubah lewat file .env (lihat .env.example) ---
HOST = os.environ.get('FLASK_HOST', '0.0.0.0')       # 0.0.0.0 = bisa diakses dari LAN
PORT = int(os.environ.get('FLASK_PORT', '5000'))     # Port server web
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'    # Debug: 0=mati, 1=nyala

# Path file database SQLite (ada di folder proyek).
# Bisa diganti lewat .env. Berguna saat testing: pakai DB sementara
# supaya data asli di hidroponik.db tidak terganggu.
DB_PATH = os.path.join(
    os.path.dirname(__file__),
    os.environ.get('DB_PATH', 'hidroponik.db')
)

# --- Pengaturan keamanan (Tahap 2) ---

# Kunci rahasia untuk perangkat IoT (OPSIONAL).
# - Jika DIISI di .env  -> endpoint POST /api/sensor wajib kirim header X-API-Key.
# - Jika DIKOSONGKAN    -> proteksi dimatikan (cukup untuk pemakaian di LAN rumah).
API_KEY = os.environ.get('API_KEY', '')

# Batas jumlah request data per MENIT untuk satu alamat IP (anti-spam).
RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '60'))

# Batasi ukuran body request maksimal 1 MB (data sensor JSON sangat kecil,
# jadi 1 MB sudah sangat longgar — ini mencegah payload raksasa).
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024

# Daftar nilai yang DIWOJALKAN (whitelist) untuk validasi input.
# (ERR-4, VAL-3, VAL-4) menghindari user mengetik string sembarangan.
VALID_PLANT_TYPES = ['Sayur Daun', 'Buah', 'Herbal', 'Bunga']
VALID_PLANT_STATUSES = ['Sehat', 'Perlu perhatian', 'Baru ditanam']

# Rentang sensor YANG MASUK AKAL untuk hidroponik (VAL-5).
# Lebih ketat dari batas fisik (0-14), agar data sensor tidak "ngawur".
SENSOR_RANGES = {
    'ph':          (3.0,  10.0),
    'tds':         (50.0, 3000.0),
    'temperature': (0.0,  50.0),
    'humidity':    (0.0,  100.0),
    'water_level': (0.0,  100.0),
}

# CATATAN KEAMANAN (SEC-1, SEC-5):
# - Jangan jalankan server ini di jaringan publik tanpa autentikasi.
# - Untuk development pribadi / LAN tertutup (rumah/kos) sudah cukup.
# - Jika ekspos ke internet nanti: pakai Nginx + HTTPS + sistem login (Flask-Login).
# - Mode debug DINONAKTIFKAN untuk menghindari RCE via Werkzeug debugger.


# ==================== PENGAMANAN SEDERHANA (Tahap 2) ====================

# Catatan waktu request per alamat IP: {ip: [waktu1, waktu2, ...]}
# Disimpan di memori saja, jadi otomatis kosong lagi saat server di-restart.
_riwayat_request = {}


def cek_api_key():
    """
    Memeriksa header X-API-Key pada request.
    - Jika API_KEY belum diatur (kosong) -> proteksi dimatikan, selalu True.
    - Jika API_KEY diatur di .env     -> header harus sama persis.
    """
    if not API_KEY:
        return True
    return request.headers.get('X-API-Key', '') == API_KEY


def kena_rate_limit(ip, batas_per_menit):
    """
    Mencegah satu IP mengirim terlalu banyak request dalam 1 menit.
    Mengembalikan True jika IP sudah melewati batas.
    """
    sekarang = time.time()
    daftar = _riwayat_request.get(ip, [])
    # Buang catatan yang umurnya lebih dari 60 detik
    daftar = [t for t in daftar if sekarang - t < 60]
    if len(daftar) >= batas_per_menit:
        _riwayat_request[ip] = daftar
        return True
    daftar.append(sekarang)
    _riwayat_request[ip] = daftar
    return False


# ==================== FUNGSI DATABASE HELPER ====================

def get_db():
    """Membuka koneksi ke database SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Biar hasil query bisa diakses seperti dictionary
    # WAL mode (Write-Ahead Logging): lebih tahan saat database diakses
    # bersamaan — misalnya alat IoT mengirim data sambil dashboard dibuka.
    # Mencegah error "database is locked".
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def init_db():
    """Membuat tabel dan isi data awal (jalankan sekali saat app mulai)"""
    conn = get_db()
    c = conn.cursor()

    # Tabel data sensor
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        ph REAL,
        tds REAL,
        temperature REAL,
        humidity REAL,
        water_level REAL
    )''')

    # Tabel tanaman
    c.execute('''CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
        plant_date TEXT,
        status TEXT,
        notes TEXT
    )''')

    # Tabel jadwal
    c.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        day TEXT,
        time TEXT,
        done INTEGER DEFAULT 0
    )''')

    conn.commit()

    # (BUG-1 fix): Cek tiap tabel SECARA TERPIAH, seed tabel yang KOSONG SAJA.
    # Tidak ada lagi "if pass" yang membingungkan pemula.
    c.execute('SELECT COUNT(*) FROM sensor_data')
    need_sensor = c.fetchone()[0] == 0
    c.execute('SELECT COUNT(*) FROM plants')
    need_plants = c.fetchone()[0] == 0
    c.execute('SELECT COUNT(*) FROM schedules')
    need_schedules = c.fetchone()[0] == 0

    if need_sensor or need_plants or need_schedules:
        _seed_dummy_data(conn,
                         fill_sensor=need_sensor,
                         fill_plants=need_plants,
                         fill_schedules=need_schedules)

    conn.close()


def _seed_dummy_data(conn, fill_sensor=True, fill_plants=True, fill_schedules=True):
    """Isi data contoh untuk tampilan awal (hanya tabel yang kosong)"""
    c = conn.cursor()
    now = datetime.now()

    if fill_sensor:
        # Perbaikan #D: jaga loop range(10) agar minute=i*6 maksimum 54 (i=9)
        # Catatan: sesuaikan range() dengan hati-hati, minute harus 0-59
        for i in range(10):
            minute_val = i * 6
            if minute_val > 59:
                minute_val = 59
            try:
                t = now.replace(minute=minute_val, second=0).strftime('%H:%M:%S')
            except ValueError:
                t = now.strftime('%H:%M:%S')
            c.execute('''INSERT INTO sensor_data
                (timestamp, ph, tds, temperature, humidity, water_level)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (t,
                 round(random.uniform(5.5, 7.0), 2),
                 round(random.uniform(800, 1500), 1),
                 round(random.uniform(22, 30), 1),
                 round(random.uniform(50, 80), 1),
                 round(random.uniform(60, 100), 1)))

    if fill_plants:
        # Perbaikan #I: simpan tanggal sebagai ISO YYYY-MM-DD (bisa disort benar oleh SQLite)
        today = date.today().isoformat()  # YYYY-MM-DD
        plants = [
            ('Selada Hijau', 'Sayur Daun', today, 'Sehat', 'Tumbuh subur'),
            ('Bayam Merah', 'Sayur Daun', today, 'Sehat', 'Daun mulai lebar'),
            ('Tomat Cherry', 'Buah', today, 'Perlu perhatian', 'Perlu pupuk tambahan')
        ]
        c.executemany('''INSERT INTO plants (name, type, plant_date, status, notes)
                          VALUES (?, ?, ?, ?, ?)''', plants)

    if fill_schedules:
        schedules = [
            ('Cek pH larutan', 'Senin', '07:00', 0),
            ('Ganti air nutrisi', 'Rabu', '08:00', 0),
            ('Cek pompa air', 'Jumat', '18:00', 0),
            ('Pantau hama', 'Minggu', '09:00', 0)
        ]
        c.executemany('''INSERT INTO schedules (task, day, time, done)
                          VALUES (?, ?, ?, ?)''', schedules)

    conn.commit()


# CATATAN (ERR-6): init_db() DIPANGGIL di BAWAH, di dalam blok `if __name__ == '__main__'`.
# Tujuannya: jika aplikasi di-load oleh gunicorn / flask CLI / worker lain,
# kita tidak langsung menulis ke DB saat modul di-import (hindari DB terkunci).
# Jika Anda pakai `flask --app app run` tanpa python app.py, uncomment 1 baris di bawah:
# init_db()


# ==================== VALIDASI INPUT (SEC-2, CMPLX-1 fix) ====================

def validate_sensor_value(name, value, min_val, max_val):
    """
    Pastikan nilai sensor adalah angka dan berada dalam rentang masuk akal.
    Mengembalikan (is_valid, cleaned_value, error_message)
    """
    if value is None:
        return False, None, f"Field '{name}' wajib diisi"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False, None, f"Field '{name}' harus berupa angka"
    if num < min_val or num > max_val:
        return False, None, f"Field '{name}' harus antara {min_val} dan {max_val}"
    return True, num, None


# ==================== FUNGSI KONVERSI ROW KE DICT ====================

def _format_date_id(iso_date_str):
    """
    (CMPLX-4) Ubah format tanggal:
    - DISIMPAN di DB sebagai ISO  YYYY-MM-DD  (agar SQLite bisa SORT dengan BENAR)
    - DITAMPILKAN ke user  sebagai  DD-MM-YYYY  (format Indonesia)
    """
    try:
        d = datetime.strptime(iso_date_str, '%Y-%m-%d')
        return d.strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        return iso_date_str or ''


def sensor_to_dict(row):
    return {
        'id': row['id'],
        'timestamp': row['timestamp'],
        'ph': row['ph'],
        'tds': row['tds'],
        'temperature': row['temperature'],
        'humidity': row['humidity'],
        'water_level': row['water_level']
    }


def plant_to_dict(row):
    return {
        'id': row['id'],
        'name': row['name'],
        'type': row['type'],
        'plant_date': _format_date_id(row['plant_date']),  # Tampil DD-MM-YYYY ke user
        'status': row['status'],
        'notes': row['notes']
    }


def schedule_to_dict(row):
    return {
        'id': row['id'],
        'task': row['task'],
        'day': row['day'],
        'time': row['time'],
        'done': bool(row['done'])
    }


# ==================== ROUTES (HALAMAN WEB) ====================

@app.route('/')
def dashboard():
    return render_template('index.html')


# ==================== API ENDPOINTS (DATA INTERAKTIF) ====================

# --- SENSOR ---

# Ambil data sensor TERBARU
@app.route('/api/sensor/latest')
def get_latest_sensor():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM sensor_data ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    return jsonify(sensor_to_dict(row) if row else {})


# Ambil 20 riwayat data sensor (untuk grafik)
@app.route('/api/sensor/history')
def get_sensor_history():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM sensor_data ORDER BY id ASC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    return jsonify([sensor_to_dict(r) for r in rows])


# Tambah data sensor (bisa dipanggil perangkat IoT nanti)
@app.route('/api/sensor', methods=['POST'])
def add_sensor_data():
    # Keamanan: endpoint ini khusus perangkat IoT -> wajib API key (jika diaktifkan)
    if not cek_api_key():
        return jsonify({'status': 'error', 'error': 'API key salah atau tidak ada'}), 401

    # Anti-spam: batasi jumlah request per menit dari satu IP
    if kena_rate_limit(request.remote_addr, RATE_LIMIT_PER_MINUTE):
        return jsonify({'status': 'error', 'error': 'Terlalu banyak permintaan, coba lagi nanti'}), 429

    body = request.get_json(silent=True) or {}

    # (CMPLX-1, ERR-3 fix): Validasi FIELD SATU PER SATU secara inline.
    # Tidak pakai list comprehension tuple. Pemula bisa membaca baris demi baris.
    # Juga memakai SENSOR_RANGES dari konfigurasi atas (VAL-5).
    errors = []

    ok_ph, ph, err = validate_sensor_value('ph', body.get('ph'), *SENSOR_RANGES['ph'])
    if not ok_ph: errors.append(err)

    ok_tds, tds, err = validate_sensor_value('tds', body.get('tds'), *SENSOR_RANGES['tds'])
    if not ok_tds: errors.append(err)

    ok_temp, temperature, err = validate_sensor_value('temperature', body.get('temperature'), *SENSOR_RANGES['temperature'])
    if not ok_temp: errors.append(err)

    ok_hum, humidity, err = validate_sensor_value('humidity', body.get('humidity'), *SENSOR_RANGES['humidity'])
    if not ok_hum: errors.append(err)

    ok_water, water_level, err = validate_sensor_value('water_level', body.get('water_level'), *SENSOR_RANGES['water_level'])
    if not ok_water: errors.append(err)

    if errors:
        return jsonify({'status': 'error', 'errors': errors}), 400

    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%H:%M:%S')
    c.execute('''INSERT INTO sensor_data
        (timestamp, ph, tds, temperature, humidity, water_level)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (now, ph, tds, temperature, humidity, water_level))
    conn.commit()
    new_id = c.lastrowid
    c.execute('SELECT * FROM sensor_data WHERE id = ?', (new_id,))
    row = c.fetchone()
    conn.close()
    return jsonify({'status': 'success', 'data': sensor_to_dict(row)}), 201


# Simulasi: buat data sensor random
# Perbaikan #G: Ubah dari GET ke POST (GET harus idempotent = tidak ubah state)
@app.route('/api/sensor/simulate', methods=['POST'])
def simulate_sensor():
    # Anti-spam: tombol simulasi juga dibatasi agar tidak disalahgunakan
    if kena_rate_limit(request.remote_addr, RATE_LIMIT_PER_MINUTE):
        return jsonify({'status': 'error', 'error': 'Terlalu banyak permintaan, coba lagi nanti'}), 429

    conn = get_db()
    c = conn.cursor()
    now = datetime.now().strftime('%H:%M:%S')
    new_data = (
        now,
        round(random.uniform(5.5, 7.0), 2),
        round(random.uniform(800, 1500), 1),
        round(random.uniform(22, 30), 1),
        round(random.uniform(50, 80), 1),
        round(random.uniform(60, 100), 1)
    )
    c.execute('''INSERT INTO sensor_data
        (timestamp, ph, tds, temperature, humidity, water_level)
        VALUES (?, ?, ?, ?, ?, ?)''', new_data)
    conn.commit()
    new_id = c.lastrowid
    c.execute('SELECT * FROM sensor_data WHERE id = ?', (new_id,))
    row = c.fetchone()
    conn.close()
    return jsonify({'status': 'simulated', 'data': sensor_to_dict(row)})


# --- TANAMAN ---

# Ambil semua tanaman
@app.route('/api/plants')
def get_plants():
    conn = get_db()
    c = conn.cursor()
    # Perbaikan #I: pakai ORDER BY plant_date DESC (ISO format bisa disort benar)
    c.execute('SELECT * FROM plants ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return jsonify([plant_to_dict(r) for r in rows])


# Tambah tanaman baru
@app.route('/api/plants', methods=['POST'])
def add_plant():
    body = request.get_json(silent=True) or {}
    name = (body.get('name') or '').strip()
    type_ = (body.get('type') or '').strip()
    status = (body.get('status') or 'Sehat').strip() or 'Sehat'
    notes = (body.get('notes') or '').strip()

    # (VAL-2 fix): minimal 2 karakter agar input tidak aneh / kosong spasi
    errors = []
    if len(name) < 2:
        errors.append('Nama tanaman minimal 2 karakter')
    if len(name) > 100:
        errors.append('Nama tanaman maksimal 100 karakter')
    if not type_:
        errors.append('Jenis tanaman wajib dipilih')
    elif len(type_) > 50:
        errors.append('Jenis tanaman maksimal 50 karakter')

    # (VAL-3, VAL-4 fix): whitelist agar user tidak kirim string sembarang
    if type_ and type_ not in VALID_PLANT_TYPES:
        errors.append(f"Jenis tanaman harus salah satu: {', '.join(VALID_PLANT_TYPES)}")
    if status not in VALID_PLANT_STATUSES:
        status = 'Sehat'  # Fallback jika kirim status ngaco (tidak error, pilih default)

    # (VAL-1 fix): batasi panjang notes dan status
    if len(status) > 20:
        errors.append('Status maksimal 20 karakter')
    if len(notes) > 500:
        errors.append('Catatan maksimal 500 karakter')

    if errors:
        # Gabungkan error menjadi 1 kalimat agar mudah toast di frontend
        return jsonify({'status': 'error', 'error': ' | '.join(errors)}), 400

    conn = get_db()
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute('''INSERT INTO plants (name, type, plant_date, status, notes)
                 VALUES (?, ?, ?, ?, ?)''',
              (name, type_, today, status, notes))
    conn.commit()
    new_id = c.lastrowid
    c.execute('SELECT * FROM plants WHERE id = ?', (new_id,))
    row = c.fetchone()
    conn.close()
    return jsonify({'status': 'success', 'data': plant_to_dict(row)}), 201


# Hapus tanaman
@app.route('/api/plants/<int:plant_id>', methods=['DELETE'])
def delete_plant(plant_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM plants WHERE id = ?', (plant_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'status': 'error', 'error': 'Tanaman tidak ditemukan'}), 404
    c.execute('DELETE FROM plants WHERE id = ?', (plant_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})


# --- JADWAL ---

# Ambil semua jadwal
@app.route('/api/schedules')
def get_schedules():
    conn = get_db()
    c = conn.cursor()
    # (BUG-7 fix): Tentukan urutan dengan ORDER BY, biar tidak acak
    c.execute('SELECT * FROM schedules ORDER BY id ASC')
    rows = c.fetchall()
    conn.close()
    return jsonify([schedule_to_dict(r) for r in rows])


# Toggle jadwal (selesai/belum)
@app.route('/api/schedules/<int:schedule_id>/toggle', methods=['POST'])
def toggle_schedule(schedule_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT done FROM schedules WHERE id = ?', (schedule_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'not found'}), 404
    new_done = 0 if row['done'] else 1
    c.execute('UPDATE schedules SET done = ? WHERE id = ?', (new_done, schedule_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'updated', 'done': bool(new_done)})


# ==================== JALANKAN SERVER ====================
if __name__ == '__main__':
    # (ERR-6 fix): Init DB HANYA ketika server dijalankan via python app.py,
    # bukan ketika modul di-import oleh WSGI worker lain.
    try:
        init_db()
    except Exception as e:
        print(f"[PERINGATAN] Gagal init database: {e}")

    # Host, port, dan debug diambil dari konfigurasi (.env / nilai default).
    app.run(debug=DEBUG, host=HOST, port=PORT)
