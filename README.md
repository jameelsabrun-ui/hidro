# 🌱 HidroKu — Dashboard Hidroponik Berbasis Web

Dashboard monitoring dan manajemen tanaman hidroponik sederhana menggunakan **Python 3 + Flask**. Ditulis khusus untuk pemula Python yang sedang belajar hidroponik, dengan kode mudah dibaca dan siap dikembangkan menjadi **IoT Farming** (integrasi sensor ESP32/Arduino).

---

## 🎯 Tujuan Proyek

1. **Alat bantu belajar** bagi pemula hidroponik: bisa memantau data sensor (pH, TDS, suhu, kelembaban, level air) dalam satu dashboard.
2. **Manajemen tanaman** sederhana: catat apa yang ditanam, kapan menanam, status tanaman.
3. **Pengingat jadwal perawatan**: checklist harian/mingguan (cek pH, ganti air, dll).
4. **Dasar pengembangan IoT**: menyediakan API endpoint siap pakai untuk menerima data dari perangkat mikrocontroller (ESP32, Arduino Wi-Fi, Raspberry Pi).

---

## ✨ Fitur Utama

### 📊 Dashboard Monitoring
- **5 Kartu Sensor Real-Time**: pH, TDS (nutrisi), Suhu Air, Kelembaban Udara, Level Air.
- Indikator status otomatis: **✓ Baik** (hijau) / **⚠ Perhatian** (kuning) / **✗ Bahaya** (merah) berdasarkan rentang ideal hidroponik.
- **Grafik Riwayat 24 jam** (line chart) untuk melihat tren data dari waktu ke waktu.
- **Simulasi Data Sensor** tombol untuk mencoba dashboard tanpa hardware sungguhan.
- **Auto Refresh**: data sensor update tiap 10 detik otomatis.

### 🌿 Kelola Tanaman
- Tambah/hapus data tanaman (nama, jenis: Sayur Daun/Buah/Herbal/Bunga, status, catatan).
- Tanggal tanam otomatis tercatat.
- Emoji otomatis berdasarkan jenis tanaman.

### 📅 Jadwal Perawatan
- Checklist jadwal rutin (Senin s/d Minggu) dengan jam.
- Klik centang untuk tandai selesai/belum.
- Ringkasan "sudah selesai X dari Y jadwal".

### 📖 Panduan Hidroponik
- 6 kartu panduan singkat untuk pemula: pH, TDS, Suhu, Ganti Air, Cahaya, IoT Integration.

### 🔌 API Siap IoT
Semua data bisa dibaca/ditulis lewat JSON API (lihat bagian **Contoh Penggunaan**):
- `GET  /api/sensor/latest`        → ambil data sensor terbaru
- `GET  /api/sensor/history`       → 20 data terakhir (untuk grafik)
- `POST /api/sensor`               → **kirim data dari ESP32 / IoT device**
- `POST /api/sensor/simulate`      → simulasi data random
- `GET  /api/plants`, `POST /api/plants`, `DELETE /api/plants/:id`
- `GET  /api/schedules`, `POST /api/schedules/:id/toggle`
- `POST /api/notif/test` → kirim pesan percobaan ke Telegram

### 🔒 Keamanan Dasar
- **API key opsional**: `POST /api/sensor` bisa dikunci dengan header `X-API-Key` (diatur lewat `API_KEY` di `.env`).
- **Rate limiting**: tiap IP dibatasi jumlah request data per menit (anti-spam, cegah disk penuh).
- **Batas ukuran request** 1 MB, sehingga payload raksasa otomatis ditolak.

> Ini proteksi dasar untuk pemakaian di **LAN rumah**. Untuk akses dari internet, tetap perlu **login + HTTPS** (lihat Tahap Deploy).

### 📱 Notifikasi Telegram
- Kirim peringatan otomatis ke HP saat pH/TDS/suhu/kelembaban/level air keluar dari rentang ideal.
- Tombol **🔔 Tes Notifikasi** di dashboard untuk memastikan setup sudah benar.
- **Anti-spam**: masalah yang sama hanya dikirim sekali per `NOTIF_COOLDOWN_MINUTES` menit.
- Tanpa library tambahan (memakai modul bawaan Python).

---

## 📂 Struktur Folder

```
hidro/
├── app.py                      # Backend Flask + API + Database (inti aplikasi)
├── requirements.txt            # Daftar library Python yang dibutuhkan
├── .env.example                # Contoh konfigurasi (host, port, database)
├── .env                        # Konfigurasi pribadi (copy dari .env.example, tidak ikut GitHub)
├── hidroponik.db               # (Auto-generated) File database SQLite
├── templates/
│   └── index.html              # Halaman web utama (HTML)
├── static/
│   ├── css/
│   │   └── style.css           # Styling, warna, layout (tampilan cantik)
│   └── js/
│       └── app.js              # Interaksi user, grafik, panggil API
└── tests/
    └── test_app.py             # Test otomatis dengan pytest
```

| File | Peran untuk Pemula |
|---|---|
| `app.py` | "Otak" server → baca/tulis database, kirim data ke browser. |
| `templates/index.html` | "Kerangka wajah" website → struktur tombol, kartu, menu. |
| `static/css/style.css` | "Kosmetik" → warna hijau tema hidroponik, bentuk kartu, responsif HP. |
| `static/js/app.js` | "Saraf" → tombol klik, auto refresh data, gambar grafik. |
| `hidroponik.db` | "Catatan" → semua data tersimpan disini, bisa dibuka dengan [DB Browser for SQLite](https://sqlitebrowser.org/). |
| `.env` | "Panel pengaturan" → ubah host, port, mode debug tanpa edit `app.py`. |
| `tests/test_app.py` | "Petugas pemeriksa" → otomatis mengetes apakah semua fitur masih jalan. |

---

## 🛠️ Cara Install

> **Butuh Python 3.8+**. Cek di terminal: `python --version`

### Langkah 1: Masuk ke folder proyek
```bash
cd /home/memorygroups/Documents/trae_projects/hidro
```

### Langkah 2: Install library yang dibutuhkan
```bash
pip install -r requirements.txt
```

Jika `pip` error permission di Linux, coba salah satu:
```bash
pip install --user -r requirements.txt   # install untuk user ini saja
# ATAU (direkomendasikan)
python -m venv venv             # buat virtual environment
source venv/bin/activate        # aktifkan virtual env
pip install -r requirements.txt # install di dalam venv
```

Isi `requirements.txt`: **Flask** (web), **python-dotenv** (baca file `.env`), dan **pytest** (untuk test). `sqlite3` (database) sudah *bawaan Python* — tidak perlu install. ✅

### Langkah 3: (Opsional) Buat file konfigurasi
Aplikasi sudah jalan tanpa ini, tapi kalau ingin mengubah port/host:
```bash
cp .env.example .env
```
Lalu buka `.env` dan sesuaikan. Isinya:

| Pengaturan | Default | Arti |
|---|---|---|
| `FLASK_HOST` | `0.0.0.0` | `0.0.0.0` = bisa diakses HP/IoT di Wi-Fi yang sama. `127.0.0.1` = komputer ini saja. |
| `FLASK_PORT` | `5000` | Port server. Ubah jika bentrok dengan program lain. |
| `FLASK_DEBUG` | `0` | `0` = aman (disarankan). `1` = mode belajar (jangan dipakai di jaringan publik). |
| `DB_PATH` | `hidroponik.db` | Nama file database. |
| `API_KEY` | *(kosong)* | Kunci rahasia IoT. Jika diisi, `POST /api/sensor` wajib kirim header `X-API-Key`. |
| `RATE_LIMIT_PER_MINUTE` | `60` | Batas request data per menit untuk satu alamat IP (anti-spam). |
| `TELEGRAM_BOT_TOKEN` | *(kosong)* | Token bot Telegram. Kosong = notifikasi mati. |
| `TELEGRAM_CHAT_ID` | *(kosong)* | Chat ID tujuan notifikasi Telegram. |
| `NOTIF_COOLDOWN_MINUTES` | `30` | Jeda minimal antar notifikasi untuk masalah yang sama (menit). |

> File `.env` **tidak akan ikut ter-upload ke GitHub** (sudah diblokir lewat `.gitignore`), jadi aman untuk pengaturan pribadi.

### Langkah 4: (Opsional) Aktifkan Notifikasi Telegram
Supaya HP menerima peringatan otomatis saat pH/TDS/suhu keluar dari rentang ideal.

**1. Buat bot Telegram**
- Buka Telegram, cari **@BotFather** → kirim pesan `/newbot`
- Ikuti instruksinya (isi nama & username bot)
- BotFather akan memberi **token** seperti `123456789:AAHxxxxxxxxxxxxxxxx` → copy

**2. Dapatkan Chat ID Anda**
- Cari **@userinfobot** → kirim pesan apa saja
- Bot membalas **Id** Anda, misalnya `987654321` → copy angka itu

**3. Isi file `.env`**
```bash
cp .env.example .env   # kalau file .env belum ada
```
Lalu isi dua baris ini:
```
TELEGRAM_BOT_TOKEN=123456789:AAHxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=987654321
```

**4. Tes**
- Restart server (`Ctrl+C`, lalu `python app.py` lagi)
- Buka dashboard → klik tombol **🔔 Tes Notifikasi** di kanan atas
- Pesan tes harus masuk ke chat Telegram Anda

> Notifikasi otomatis dikirim saat data sensor masuk lewat `POST /api/sensor` dan ada nilai di luar rentang **ideal** (`IDEAL_RANGES` di [app.py](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L77-L83)). Masalah yang sama hanya dikirim sekali per `NOTIF_COOLDOWN_MINUTES` menit agar tidak spam.

---

## 🚀 Cara Menjalankan

### Cara utama (pakai python langsung)
```bash
python app.py
```

Tunggu sampai muncul output seperti ini:
```
 * Serving Flask app 'app'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.10:5000    <- IP LAN (gunakan untuk HP/ESP32 di Wi-Fi sama)
Press CTRL+C to quit
```

### Buka di browser
- **Di komputer yang sama**:  http://127.0.0.1:5000  atau  http://localhost:5000
- **Di HP / perangkat lain (Wi-Fi sama)**:  http://IP_KOMPUTER_ANDA:5000  (contoh `http://192.168.1.10:5000`)

**CATATAN KEAMANAN**: Server berjalan di `0.0.0.0` = bisa diakses perangkat lain di jaringan LAN yang sama. **JANGAN buka port 5000 ke internet** (port forwarding router) sebelum menambahkan sistem login dan autentikasi API.

### Matikan server
Tekan `Ctrl + C` di terminal.

---

## 💡 Contoh Penggunaan

### 🖱️ Penggunaan Manual (lewat website)
1. Jalankan `python app.py` → buka http://localhost:5000
2. **Dashboard**: Klik tombol **🔄 Simulasi Data Sensor** pojok kanan atas untuk generate data baru dan lihat kartu + grafik berubah.
3. **🌿 Tanaman**: Klik `➕ Tambah Tanaman` → isi form → Simpan → kartu tanaman muncul. Klik `✕` di pojok kartu untuk menghapus.
4. **📅 Jadwal**: Klik kotak persegi di kiri tiap jadwal untuk menandai selesai.
5. **📖 Panduan**: Baca 6 panduan singkat hidroponik dasar.

### 🔌 Kirim Data Sensor dari ESP32 / IoT (contoh kode)

Kirim **HTTP POST** dengan body `JSON` ke alamat endpoint `/api/sensor`. Contoh kode Python (simulasi perangkat IoT):

```python
# simpan sebagai contoh_kirim_iot.py
import requests
import random

data_sensor = {
    "ph":          round(random.uniform(5.5, 6.8), 2),
    "tds":         round(random.uniform(800, 1400), 1),
    "temperature": round(random.uniform(23, 28), 1),
    "humidity":    round(random.uniform(55, 70), 1),
    "water_level": round(random.uniform(60, 95), 1)
}

# Ganti IP sesuai komputer yang menjalankan Flask
url = "http://127.0.0.1:5000/api/sensor"

# Jika API_KEY diisi di .env, header ini WAJIB ada.
# Kalau API_KEY dikosongkan (default), header ini boleh tidak dikirim.
headers = {"X-API-Key": "kunci-rahasia-anda"}

r = requests.post(url, json=data_sensor, headers=headers)
print("Status:", r.status_code)
print("Response:", r.json())
```

Jalankan: `python contoh_kirim_iot.py`, lalu refresh dashboard → data akan muncul.

Contoh untuk ESP32 (Arduino) menggunakan `HTTPClient` dan `ArduinoJson`:
```cpp
// (Pseudocode — sesuaikan pin sensor Anda)
#include <HTTPClient.h>
#include <ArduinoJson.h>

void kirim_data() {
  HTTPClient http;
  http.begin("http://192.168.1.10:5000/api/sensor"); // IP server Flask
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", "kunci-rahasia-anda"); // wajib jika API_KEY diisi di .env

  StaticJsonDocument<200> doc;
  doc["ph"]          = 6.20;
  doc["tds"]         = 1023.5;
  doc["temperature"] = 25.3;
  doc["humidity"]    = 63.0;
  doc["water_level"] = 78.0;

  String body; serializeJson(doc, body);
  int status = http.POST(body);
  Serial.printf("Status HTTP: %d\n", status);
  http.end();
}
```

### 🧪 Cek API langsung dengan CURL
Buka terminal lain (Flask harus tetap berjalan):
```bash
# Lihat data sensor terbaru:
curl -s http://localhost:5000/api/sensor/latest | python -m json.tool

# Tambah data sensor manual
# (tambahkan  -H 'X-API-Key: kunci-rahasia-anda'  jika API_KEY diaktifkan di .env)
curl -X POST http://localhost:5000/api/sensor \
  -H 'Content-Type: application/json' \
  -d '{"ph":6.1,"tds":1100,"temperature":26,"humidity":65,"water_level":82}'
```

---

## ✅ Cara Test

### A. Test Otomatis (pakai pytest) — direkomendasikan
Semua skenario test sudah tersimpan di [tests/test_app.py](file:///home/memorygroups/Documents/trae_projects/hidro/tests/test_app.py). Jalankan:

```bash
python -m pytest -v
```

Hasil yang diharapkan (semua hijau):
```
tests/test_app.py::test_halaman_utama_terbuka PASSED
tests/test_app.py::test_sensor_terbaru_lengkap PASSED
tests/test_app.py::test_kirim_sensor_diluar_rentang_ditolak PASSED
... (total 26 test)
============================== 26 passed in 9.35s ===============================
```

> Test memakai **database sementara** di folder temp, jadi data asli di `hidroponik.db` **tidak akan terhapus/terganggu**.

### B. Test Manual Langkah demi Langkah
| Langkah | Yang Dilakukan | Hasil yang Diharapkan |
|---|---|---|
| 1 | Buka http://localhost:5000 | Dashboard muncul dengan 5 kartu sensor, 1 grafik, 4 summary |
| 2 | Klik menu 🌿 Tanaman → Tambah Tanaman | Form muncul, isi data → kartu tanaman baru tampil |
| 3 | Hapus tanaman dengan klik ✕ di kartu | Kartu hilang, total tanaman berkurang |
| 4 | Klik menu 📅 Jadwal → klik kotak ceklis jadwal pertama | Ceklis berwarna hijau bergambar ✓ |
| 5 | Kembali ke Dashboard → klik **🔄 Simulasi Data Sensor** | Kartu nilai berubah, grafik bertambah 1 titik data, ada toast notifikasi |
| 6 | Tunggu 10-15 detik di halaman Dashboard | Data sensor auto refresh tanpa reload halaman |
| 7 | Buka di browser HP (pada Wi-Fi yang sama) → `http://IP:5000` | Tampilan responsif menyesuaikan layar HP |
| 8 | Send POST `/api/sensor` dengan `ph=15` (via curl) | Response status **400** (ditolak — validasi bekerja) |

---

## 🔧 Masalah Umum dan Solusi

| # | Gejala | Penyebab | Solusi |
|---|---|---|---|
| **1** | `ModuleNotFoundError: No module named 'flask'` | Library belum diinstall | Jalankan `pip install -r requirements.txt`. Jika masih error: coba `pip3 install -r requirements.txt` atau buat virtual environment (lihat bagian **Cara Install**). |
| **2** | `Address already in use :::5000` atau `Port 5000 is in use` | Ada program lain pakai port 5000 (atau server Flask lama belum mati) | Tutup terminal lama (Ctrl+C). Atau ubah `FLASK_PORT` di file `.env` (contoh `.env.example`), atau langsung di [app.py:664](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L664) → `PORT` jadi `5001`. |
| **3** | Buka `http://IP:5000` dari HP **tidak bisa dibuka** | Firewall komputer / beda jaringan | Pastikan HP dan komputer **terhubung Wi-Fi yang SAMA**. Cek `ufw status` / firewall Linux → izinkan port 5000 (`sudo ufw allow 5000` sementara). Matikan VPN. |
| **4** | Semua kartu sensor menampilkan **`--`** dan bertuliskan "Memuat..." | Frontend gagal memanggil API / DB kosong | Buka DevTools → Console (F12 di browser) untuk lihat error. Pastikan Flask server sedang berjalan. Jika DB kosong: restart server dengan `python app.py` (auto seed). |
| **5** | **Grafik tidak muncul** (hanya tulisan judul) | CDN Chart.js tidak termuat (offline / diblokir internet / DNS) | Pastikan komputer punya akses internet (CDN Chart.js di-load dari jsdelivr). Jika offline permanen: download `chart.umd.min.js` secara lokal, taruh di `static/js/`, lalu ubah `<script src=...>` di [index.html:20](file:///home/memorygroups/Documents/trae_projects/hidro/templates/index.html#L20) menjadi file lokal. |
| **6** | Setelah kirim data dari ESP32 → response **400 Bad Request** | Ada field yang salah (ph diluar 3-10, tds < 50, dst) | Lihat field `errors` di response JSON → perbaiki nilai sensor atau ubah rentang di konstanta `SENSOR_RANGES` [app.py:66-72](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L66-L72). |
| **7** | Tombol **Simulasi Data Sensor** diklik → toast **❌ Gagal simulasi** | Endpoint method salah atau error server | Pastikan server di-restart setelah edit app.py. Simulate harus pakai **POST** (bukan GET). |
| **8** | `OperationalError: database is locked` (saat deploy gunicorn / banyak akses) | SQLite mode default tidak cocok untuk concurrency tinggi | **Sudah ditangani**: aplikasi otomatis mengaktifkan **WAL mode** di fungsi `get_db()` [app.py:215-223](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L215-L223). Jika masih muncul pada trafik sangat tinggi → pertimbangkan migrasi ke PostgreSQL. |
| **9** | Menjalankan via `flask --app app run` → **data tanaman/jadwal kosong** | Karena init_db() dipindahkan ke blok `if __name__` (hindari DB lock worker) | Jalankan via `python app.py` (direkomendasikan). ATAU buka komentar `# init_db()` di [app.py:335](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L335). |
| **10** | Data sensor tidak berubah walau ESP32 kirim tiap detik | **Auto refresh frontend 10 detik** / limit history 20 data terakhir | Ubah angka di `setInterval(loadSensorData, 10000)` [app.js:14](file:///home/memorygroups/Documents/trae_projects/hidro/static/js/app.js#L14) menjadi `3000` (3 detik) atau sesuai kebutuhan. |
| **11** | Menambah jenis tanaman baru (misal "Umbi") tapi tidak opsi di select | HTML form + whitelist Python harus sinkron | Edit `<option value="Umbi">Umbi</option>` di [index.html:228-234](file:///home/memorygroups/Documents/trae_projects/hidro/templates/index.html#L228-L234) **DAN** tambahkan ke `VALID_PLANT_TYPES` di [app.py:61](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L61) + tambahkan emoji di `emojiMap` [app.js:394](file:///home/memorygroups/Documents/trae_projects/hidro/static/js/app.js#L394). |
| **12** | Ingin reset semua data bersih (mulai dari nol) | Database sudah terisi banyak data percobaan | **Hapus file `hidroponik.db`** → restart server → database baru + seed awal dibuat ulang. |
| **13** | Kirim data dari IoT → response **401 Unauthorized** | `API_KEY` diisi di `.env`, tapi header `X-API-Key` tidak dikirim atau salah | Kirim header `X-API-Key` dengan nilai persis sama seperti di `.env`. Atau kosongkan `API_KEY` untuk mematikan proteksi. |
| **14** | Response **429 Too Many Requests** | Mengirim lebih dari batas request per menit (default 60) | Tunggu 1 menit, atau naikkan `RATE_LIMIT_PER_MINUTE` di `.env`. |
| **15** | Klik **Tes Notifikasi** → muncul pesan *"Telegram belum dikonfigurasi"* | `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` masih kosong di `.env` | Isi keduanya di `.env`, lalu **restart server** (perubahan `.env` baru terbaca setelah restart). |
| **16** | Klik **Tes Notifikasi** → pesan *"Gagal mengirim"* | Token/chat ID salah, atau Anda belum pernah memulai chat dengan bot | Cek ulang token dari @BotFather & chat ID dari @userinfobot. Pastikan Anda sudah kirim `/start` ke bot tersebut. |
| **17** | Setup Telegram benar tapi notifikasi tidak pernah masuk | Nilai sensor masih dalam rentang ideal, atau masih dalam masa cooldown | Notifikasi hanya dikirim bila ada nilai di luar `IDEAL_RANGES` [app.py](file:///home/memorygroups/Documents/trae_projects/hidro/app.py#L77-L83). Cek juga `NOTIF_COOLDOWN_MINUTES`. |

---

## 📚 Sumber Belajar Tambahan (Dokumentasi Resmi)

- **Flask (Backend)**:   https://flask.palletsprojects.com/
- **SQLite (Database)**: https://www.sqlite.org/datatype3.html
- **Chart.js (Grafik)**: https://www.chartjs.org/docs/4.4.1/
- **Subresource Integrity (keamanan CDN)**: https://developer.mozilla.org/id/docs/Web/Security/Subresource_Integrity
- **HTTP Methods (REST idempoten)**: https://developer.mozilla.org/id/docs/Glossary/Idempotent

---

> 🚀 **Tahap selanjutnya untuk IoT Farming**:
> 1. Beli sensor pH, EC/TDS (meteran nutrisi), DS18B20 (suhu air), DHT22 (kelembaban udara), ultrasonic (level air).
> 2. Pasang semua sensor ke ESP32.
> 3. Kirim data tiap 5 menit ke `POST /api/sensor`.
> 4. Tambahkan endpoint `POST /api/pompa` + relay untuk ON/OFF pompa dari dashboard.
> 5. Tambahkan notifikasi Telegram jika pH/TDS di luar batas aman.
