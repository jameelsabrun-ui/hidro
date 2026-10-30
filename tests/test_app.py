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

    # 2. Arahkan aplikasi ke database sementara, lalu isi data awal
    app_module.DB_PATH = tmp.name
    app_module.init_db()

    # 3. TESTING=True -> jika ada error, langsung tampil (bukan halaman HTML)
    app_module.app.config['TESTING'] = True

    # 4. Berikan "client" ke test, lalu bersihkan setelah test selesai
    with app_module.app.test_client() as c:
        yield c

    # Bersihkan file database + file WAL/SHM pendampingnya
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
