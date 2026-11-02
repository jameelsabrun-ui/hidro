"""
Test otomatis untuk aplikasi HidroKu.

Cara menjalankan (dari folder proyek):
    python -m pytest -v

Setiap test memakai database SEMENTARA (file di folder temp),
jadi data asli di hidroponik.db tidak akan terganggu.
"""
import os
import tempfile
import pytest

import app as app_module


@pytest.fixture
def client():
    """Menyiapkan aplikasi + database sementara untuk satu test."""
    # 1. Buat file database kosong di folder sementara
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()

    # 2. Simpan pengaturan asli, lalu atur kondisi bersih untuk test
    api_key_asli = app_module.API_KEY
    token_asli = app_module.TELEGRAM_BOT_TOKEN
    chat_id_asli = app_module.TELEGRAM_CHAT_ID
    app_module.API_KEY = ''               # default test: proteksi API key dimatikan
    app_module.TELEGRAM_BOT_TOKEN = ''    # default test: notifikasi Telegram dimatikan
    app_module.TELEGRAM_CHAT_ID = ''
    app_module._riwayat_request.clear()   # reset catatan rate limit
    app_module._terakhir_notif.clear()    # reset catatan cooldown notifikasi

    # 3. Arahkan aplikasi ke database sementara, lalu isi data awal
    app_module.DB_PATH = tmp.name
    app_module.init_db()

    # 4. TESTING=True -> jika ada error, langsung tampil (bukan halaman HTML)
    app_module.app.config['TESTING'] = True

    # 5. Berikan "client" ke test, lalu bersihkan setelah test selesai
    with app_module.app.test_client() as c:
        yield c

    # Kembalikan pengaturan asli + bersihkan file database (dan WAL/SHM-nya)
    app_module.API_KEY = api_key_asli
    app_module.TELEGRAM_BOT_TOKEN = token_asli
    app_module.TELEGRAM_CHAT_ID = chat_id_asli
    app_module._riwayat_request.clear()
    app_module._terakhir_notif.clear()
    for path in (tmp.name, tmp.name + '-wal', tmp.name + '-shm'):
        if os.path.exists(path):
            os.remove(path)


# ==================== TEST HALAMAN WEB ====================

def test_halaman_utama_terbuka(client):
    """GET / harus mengembalikan halaman HTML (status 200)."""
    r = client.get('/')
    assert r.status_code == 200
    assert b'<html' in r.data.lower()


# ==================== TEST API SENSOR ====================

def test_sensor_terbaru_lengkap(client):
    """GET /api/sensor/latest mengembalikan data sensor lengkap."""
    r = client.get('/api/sensor/latest')
    assert r.status_code == 200
    data = r.get_json()
    assert 'ph' in data
    assert 'tds' in data
    assert 'temperature' in data


def test_riwayat_sensor_berisi_seed(client):
    """GET /api/sensor/history mengembalikan data awal (minimal 10)."""
    r = client.get('/api/sensor/history')
    assert r.status_code == 200
    assert len(r.get_json()) >= 10


def test_kirim_sensor_valid(client):
    """POST /api/sensor dengan data benar -> 201 Created."""
    payload = {'ph': 6.2, 'tds': 1000, 'temperature': 25,
               'humidity': 60, 'water_level': 80}
    r = client.post('/api/sensor', json=payload)
    assert r.status_code == 201
    assert r.get_json()['status'] == 'success'


def test_kirim_sensor_diluar_rentang_ditolak(client):
    """pH di luar rentang masuk akal -> 400 Bad Request."""
    payload = {'ph': 999, 'tds': 1000, 'temperature': 25,
               'humidity': 60, 'water_level': 80}
    r = client.post('/api/sensor', json=payload)
    assert r.status_code == 400
    assert len(r.get_json()['errors']) >= 1


def test_kirim_sensor_body_kosong_ditolak(client):
    """Body kosong harus ditolak 400, bukan membuat server error."""
    r = client.post('/api/sensor', json={})
    assert r.status_code == 400


def test_kirim_sensor_bukan_json_ditolak(client):
    """Kirim teks biasa (bukan JSON) -> 400, bukan 500."""
    r = client.post('/api/sensor', data='bukan json', content_type='text/plain')
    assert r.status_code == 400


def test_simulate_harus_pakai_post(client):
    """Simulasi data harus POST; jika dipanggil GET -> 405."""
    assert client.get('/api/sensor/simulate').status_code == 405
    assert client.post('/api/sensor/simulate').status_code == 200


# ==================== TEST API TANAMAN ====================

def test_tambah_tanaman_valid(client):
    """Menambah tanaman dengan data benar -> 201."""
    r = client.post('/api/plants', json={'name': 'Kangkung', 'type': 'Sayur Daun'})
    assert r.status_code == 201
    assert r.get_json()['data']['name'] == 'Kangkung'


def test_tambah_tanaman_nama_terlalu_pendek(client):
    """Nama kurang dari 2 karakter -> 400."""
    r = client.post('/api/plants', json={'name': 'A', 'type': 'Sayur Daun'})
    assert r.status_code == 400


def test_tambah_tanaman_jenis_tidak_dikenal(client):
    """Jenis di luar daftar yang diizinkan -> 400."""
    r = client.post('/api/plants', json={'name': 'Kangkung', 'type': 'Jenis Ngaco'})
    assert r.status_code == 400


def test_status_tidak_dikenal_diganti_default(client):
    """Status tidak dikenal -> otomatis jadi 'Sehat' (tetap 201)."""
    r = client.post('/api/plants', json={'name': 'Kangkung', 'type': 'Sayur Daun',
                                         'status': 'Status Aneh'})
    assert r.status_code == 201
    assert r.get_json()['data']['status'] == 'Sehat'


def test_hapus_tanaman(client):
    """Hapus tanaman yang ada -> 200; yang tidak ada -> 404."""
    plants = client.get('/api/plants').get_json()
    id_ada = plants[0]['id']
    assert client.delete(f'/api/plants/{id_ada}').status_code == 200
    assert client.delete('/api/plants/9999999').status_code == 404


# ==================== TEST API JADWAL ====================

def test_jadwal_urut_dan_berisi_seed(client):
    """Jadwal harus urut berdasarkan id dan berisi data awal."""
    r = client.get('/api/schedules')
    assert r.status_code == 200
    ids = [s['id'] for s in r.get_json()]
    assert ids == sorted(ids)
    assert len(ids) >= 4


def test_toggle_jadwal(client):
    """Toggle jadwal yang ada -> 200 dan status 'done' berubah."""
    jadwal = client.get('/api/schedules').get_json()
    id_ada = jadwal[0]['id']
    r = client.post(f'/api/schedules/{id_ada}/toggle')
    assert r.status_code == 200
    assert r.get_json()['done'] is True


def test_toggle_jadwal_tidak_ditemukan(client):
    """Toggle id yang tidak ada -> 404."""
    assert client.post('/api/schedules/9999999/toggle').status_code == 404


# ==================== TEST KEAMANAN API (Tahap 2) ====================

def test_api_key_nonaktif_jika_kosong(client):
    """Jika API_KEY kosong, POST /api/sensor tetap bisa tanpa header."""
    payload = {'ph': 6.2, 'tds': 1000, 'temperature': 25,
               'humidity': 60, 'water_level': 80}
    assert client.post('/api/sensor', json=payload).status_code == 201


def test_api_key_wajib_saat_diaktifkan(client):
    """Jika API_KEY diatur, header X-API-Key wajib dan harus benar."""
    app_module.API_KEY = 'rahasia123'
    payload = {'ph': 6.2, 'tds': 1000, 'temperature': 25,
               'humidity': 60, 'water_level': 80}

    # Tanpa header -> 401
    assert client.post('/api/sensor', json=payload).status_code == 401
    # Header salah -> 401
    r = client.post('/api/sensor', json=payload, headers={'X-API-Key': 'salah'})
    assert r.status_code == 401
    # Header benar -> 201
    r = client.post('/api/sensor', json=payload, headers={'X-API-Key': 'rahasia123'})
    assert r.status_code == 201


def test_rate_limit_menolak_kelebihan_request(client):
    """Setelah melewati batas per menit, request ditolak dengan 429."""
    batas_asli = app_module.RATE_LIMIT_PER_MINUTE
    app_module.RATE_LIMIT_PER_MINUTE = 5   # kecilkan agar test cepat
    app_module._riwayat_request.clear()
    try:
        for _ in range(5):
            assert client.post('/api/sensor/simulate').status_code == 200
        # Request ke-6 harus ditolak
        assert client.post('/api/sensor/simulate').status_code == 429
    finally:
        app_module.RATE_LIMIT_PER_MINUTE = batas_asli


def test_body_terlalu_besar_ditolak(client):
    """Body request lebih dari 1 MB -> 413 Request Entity Too Large."""
    body_besar = 'x' * (2 * 1024 * 1024)  # 2 MB
    r = client.post('/api/sensor', data=body_besar,
                    content_type='application/json')
    assert r.status_code == 413


# ==================== TEST NOTIFIKASI TELEGRAM (Tahap 4) ====================

def test_telegram_nonaktif_jika_kosong(client):
    """telegram_aktif() harus False kalau token/chat id belum diisi."""
    assert app_module.telegram_aktif() is False


def test_kirim_telegram_tidak_error_saat_mati(client):
    """kirim_telegram() mengembalikan False (bukan error) saat belum dikonfigurasi."""
    assert app_module.kirim_telegram('pesan tes') is False


def test_cek_sensor_aman_saat_notif_mati(client):
    """cek_sensor_dan_notif() tidak error walau nilai di luar rentang ideal."""
    data = {'ph': 9.0, 'tds': 20, 'temperature': 40,
            'humidity': 10, 'water_level': 5}
    assert app_module.cek_sensor_dan_notif(data) is None


def test_cooldown_notifikasi(client):
    """Masalah yang sama tidak boleh dikirim dua kali dalam masa cooldown."""
    app_module._terakhir_notif.clear()
    assert app_module.boleh_kirim_notif('ph') is True    # pertama kali: boleh
    assert app_module.boleh_kirim_notif('ph') is False   # langsung kedua: diblokir


def test_tidak_kirim_notif_saat_nilai_normal(client):
    """Semua nilai dalam rentang ideal -> tidak ada notifikasi yang dikirim."""
    app_module.TELEGRAM_BOT_TOKEN = 'token-palsu'
    app_module.TELEGRAM_CHAT_ID = '12345'
    app_module._terakhir_notif.clear()

    data = {'ph': 6.0, 'tds': 1000, 'temperature': 25,
            'humidity': 60, 'water_level': 80}
    app_module.cek_sensor_dan_notif(data)

    # Tidak ada masalah -> tidak ada catatan cooldown
    assert app_module._terakhir_notif == {}


def test_endpoint_tes_notif_tolak_saat_belum_dikonfigurasi(client):
    """POST /api/notif/test tanpa konfigurasi -> 400 dengan pesan jelas."""
    r = client.post('/api/notif/test')
    assert r.status_code == 400
    assert 'belum dikonfigurasi' in r.get_json()['error'].lower()
