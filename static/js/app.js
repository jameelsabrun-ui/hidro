// ===== VARIABEL GLOBAL =====
let monitorChart = null;     // Objek grafik Chart.js
let _chartErrorShown = false; // (BUG-2 fix): flag supaya pesan error CDN muncul SEKALI saja
let _loadingSensor = false;  // (ERR-5 fix): flag supaya setInterval tidak menumpuk request


// ===== INISIALISASI SAAT HALAMAN DIMUAT =====
document.addEventListener('DOMContentLoaded', function() {
    showCurrentDate();
    setupNavigation();
    loadAllData();

    // Auto refresh data setiap 10 detik
    setInterval(loadSensorData, 10000);
    setInterval(loadPlants, 15000);
    setInterval(loadSchedules, 15000);
});


// ===== TAMPILKAN TANGGAL HARI INI =====
function showCurrentDate() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const now = new Date();
    document.getElementById('current-date').textContent = now.toLocaleDateString('id-ID', options);
}


// ===== NAVIGASI ANTAR SECTION =====
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.content-section');
    const pageTitle = document.getElementById('page-title');

    const titles = {
        dashboard: 'Dashboard Monitoring',
        plants: 'Kelola Tanaman',
        schedule: 'Jadwal Perawatan',
        guide: 'Panduan Hidroponik'
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const target = item.dataset.section;
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById('section-' + target).classList.add('active');
            pageTitle.textContent = titles[target] || 'Dashboard';
        });
    });
}


// ===== HELPER: AMBIL JSON DARI RESPONSE SECARA AMAN (#H) =====
// Jika server error 500 dgn HTML (bukan JSON), res.json() akan throw.
// Helper ini cegah crash dan tampilkan error ke user jika bisa.
async function safeJson(res) {
    const text = await res.text();
    try {
        return JSON.parse(text);
    } catch (e) {
        console.error('Response bukan JSON:', text.slice(0, 200));
        return null;
    }
}


// ===== HELPER: ESCAPE HTML (SEC-3: CEGAH XSS) =====
// Semua input user yang ditampilkan via innerHTML WAJIB lewat fungsi ini.
// (CMPLX-5 fix): Tiap baris ada komentar agar pemula tahu apa yang terjadi.
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')   // Simbol &  -> &amp;  (entity HTML)
        .replace(/</g, '&lt;')    // Tag buka < -> &lt;
        .replace(/>/g, '&gt;')    // Tag tutup > -> &gt;
        .replace(/"/g, '&quot;')  // Tanda petik " -> &quot;
        .replace(/'/g, '&#039;'); // Tanda petik tunggal ' -> &#039;
}


// ===== MUAT SEMUA DATA SEKALIGUS =====
function loadAllData() {
    loadSensorData();
    loadSensorHistory();
    loadPlants();
    loadSchedules();
}


// ===== AMBIL DATA SENSOR TERBARU DARI API =====
async function loadSensorData() {
    // (ERR-5 fix): Jika request sebelumnya belum selesai, skip request baru
    if (_loadingSensor) return;
    _loadingSensor = true;
    try {
        const res = await fetch('/api/sensor/latest');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await safeJson(res);
        updateSensorCards(data || {});
    } catch (err) {
        console.error('Gagal memuat sensor:', err);
    } finally {
        _loadingSensor = false;
    }
}


// ===== PERBARUI KARTU SENSOR DI DASHBOARD =====
function updateSensorCards(data) {
    if (!data || Object.keys(data).length === 0) return;

    // --- pH ---
    document.getElementById('val-ph').textContent = data.ph?.toFixed(2) || '--';
    setSensorStatus('ph', data.ph, 5.8, 6.5);

    // --- TDS ---
    document.getElementById('val-tds').textContent = data.tds?.toFixed(0) || '--';
    setSensorStatus('tds', data.tds, 800, 1400);

    // --- Temperatur ---
    document.getElementById('val-temp').textContent = data.temperature?.toFixed(1) || '--';
    setSensorStatus('temp', data.temperature, 22, 28);

    // --- Kelembaban ---
    document.getElementById('val-hum').textContent = data.humidity?.toFixed(0) || '--';
    setSensorStatus('hum', data.humidity, 50, 70);

    // --- Level Air ---
    const water = data.water_level || 0;
    document.getElementById('water-fill').style.height = water + '%';
    document.getElementById('val-water').textContent = water.toFixed(0) + '%';
    setSensorStatus('water', water, 50, 100, true);

    // Update total data
    document.getElementById('total-data').textContent = data.id || '0';
}


// ===== TENTUKAN STATUS SENSOR (BAIK/WARNING/BAHAYA) =====
function setSensorStatus(type, value, min, max, inverse = false) {
    const el = document.getElementById('status-' + type);
    if (!value && value !== 0) {
        el.textContent = 'Memuat...';
        el.className = 'sensor-status';
        return;
    }

    // (BUG-3 fix): Logika diseragamkan.
    // - "Baik"      : di antara min dan max
    // - "Warning"   : 10% di luar batas (kurang / lebih)
    // - "Danger"    : lebih dari 10% di luar batas
    // Parameter `inverse` TIDAK LAGI mengubah logika perhitungan.
    // (Inverse dulu cuma bikin pusing pemula, sekarang cukup dipakai untuk
    //  level air — tapi perhitungan warning SAMA untuk semua kartu).
    let text, cls;
    const isGood = value >= min && value <= max;
    const warnLow  = min * 0.9;
    const warnHigh = max * 1.1;
    const isWarning = (value >= warnLow  && value < min) ||
                      (value >  max      && value <= warnHigh);

    if (isGood) {
        text = '✓ Kondisi Baik';
        cls = 'sensor-status status-good';
    } else if (isWarning) {
        text = '⚠ Perlu Perhatian';
        cls = 'sensor-status status-warning';
    } else {
        text = '✗ Diluar Batas!';
        cls = 'sensor-status status-danger';
    }

    el.textContent = text;
    el.className = cls;
}


// ===== MUAT RIWAYAT SENSOR UNTUK GRAFIK =====
async function loadSensorHistory() {
    try {
        const res = await fetch('/api/sensor/history');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await safeJson(res);
        renderChart(data || []);
    } catch (err) {
        console.error('Gagal muat riwayat:', err);
    }
}


// ===== RENDER GRAFIK DENGAN CHART.JS =====
function renderChart(data) {
    const canvas = document.getElementById('monitorChart');
    if (!canvas) return;

    // (BUG-2 + DOC-5 fix): Pastikan Chart.js tersedia. Jika tidak, TAMPILKAN ERROR HANYA SEKALI.
    if (typeof Chart === 'undefined') {
        if (!_chartErrorShown) {
            _chartErrorShown = true;
            console.error('Chart.js tidak termuat! Periksa koneksi atau script CDN.');
            canvas.parentElement.insertAdjacentHTML('beforeend',
                '<p style="color:#c62828;padding:15px;">⚠ Grafik gagal dimuat (Chart.js CDN tidak terhubung). Periksa koneksi internet.</p>');
        }
        return;
    }

    const ctx = canvas.getContext('2d');

    // (ERR-1 fix): Default 0 jika field null/undefined, agar Chart tidak NaN.
    const labels = data.map(d => d.timestamp || '');
    const phData = data.map(d => d.ph == null ? 0 : d.ph);
    // TDS dibagi 100 agar muat di skala grafik bersama pH, Suhu, Kelembaban.
    const tdsData = data.map(d => d.tds == null ? 0 : (d.tds / 100));
    const tempData = data.map(d => d.temperature == null ? 0 : d.temperature);
    const humData = data.map(d => d.humidity == null ? 0 : d.humidity);

    if (monitorChart) {
        monitorChart.data.labels = labels;
        monitorChart.data.datasets[0].data = phData;
        monitorChart.data.datasets[1].data = tdsData;
        monitorChart.data.datasets[2].data = tempData;
        monitorChart.data.datasets[3].data = humData;
        monitorChart.update();
        return;
    }

    monitorChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'pH',
                    data: phData,
                    borderColor: '#7e57c2',
                    backgroundColor: 'rgba(126, 87, 194, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2.5
                },
                {
                    label: 'TDS (÷100 ppm)',
                    data: tdsData,
                    borderColor: '#29b6f6',
                    backgroundColor: 'rgba(41, 182, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2.5
                },
                {
                    label: 'Suhu (°C)',
                    data: tempData,
                    borderColor: '#ef5350',
                    backgroundColor: 'rgba(239, 83, 80, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2.5
                },
                {
                    label: 'Kelembaban (%)',
                    data: humData,
                    borderColor: '#66bb6a',
                    backgroundColor: 'rgba(102, 187, 106, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2.5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: { size: 13 }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}


// ===== SIMULASI DATA SENSOR BARU =====
// Perbaikan #G: Endpoint sekarang pakai HTTP POST (bukan GET)
async function simulateSensor() {
    try {
        const res = await fetch('/api/sensor/simulate', { method: 'POST' });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const json = await safeJson(res);
        if (json && json.status === 'simulated') {
            loadSensorData();
            loadSensorHistory();
            showToast('✅ Data sensor baru berhasil dibuat!');
        } else {
            showToast('⚠ Server merespons tapi data tidak tersimpan');
        }
    } catch (err) {
        console.error(err);
        showToast('❌ Gagal simulasi data');
    }
}


// ===== TOAST (NOTIFIKASI SEMENTARA) =====
function showToast(message) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; top: 30px; right: 30px;
        background: #2e7d32; color: white;
        padding: 15px 25px; border-radius: 10px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        z-index: 9999; font-weight: 600;
        animation: fadeIn 0.3s;
    `;
    // message TIDAK pakai innerHTML (hindari XSS dari pesan error yang aneh)
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}


// ================== TANAMAN ==================

async function loadPlants() {
    try {
        const res = await fetch('/api/plants');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const plants = await safeJson(res);
        renderPlants(plants || []);
    } catch (err) {
        console.error('Gagal muat tanaman:', err);
    }
}

function renderPlants(plants) {
    const container = document.getElementById('plants-list');
    document.getElementById('total-plants').textContent = plants.length;

    const warningCount = plants.filter(p => p.status === 'Perlu perhatian').length;
    document.getElementById('total-warning').textContent = warningCount;

    if (plants.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div style="font-size: 60px;">🌱</div>
                <p>Belum ada tanaman. Klik "Tambah Tanaman" untuk memulai!</p>
            </div>
        `;
        return;
    }

    const emojiMap = {
        'Sayur Daun': '🥬',
        'Buah': '🍅',
        'Herbal': '🌿',
        'Bunga': '🌺'
    };

    // Perbaikan SEC-3: SEMUA field user input (name, type, status, notes, plant_date)
    // HARUS dilewatkan escapeHtml() sebelum innerHTML.
    // p.id aman (integer from DB), tapi lebih baik tetap escape meskipun.
    container.innerHTML = plants.map(p => {
        const emoji = escapeHtml(emojiMap[p.type] || '🌱');
        const statusClass = p.status === 'Perlu perhatian' ? 'status-warning' : 'status-good';
        const cardClass = p.status === 'Perlu perhatian' ? 'plant-card warning' : 'plant-card';
        return `
            <div class="${cardClass}">
                <button class="delete-btn" onclick="deletePlant(${Number(p.id) || 0})" title="Hapus">✕</button>
                <div class="plant-emoji">${emoji}</div>
                <div class="plant-name">${escapeHtml(p.name)}</div>
                <div class="plant-type">${escapeHtml(p.type)}</div>
                <span class="plant-status ${statusClass}">${escapeHtml(p.status)}</span>
                <div class="plant-date">📅 Tanam: ${escapeHtml(p.plant_date)}</div>
                ${p.notes ? `<div class="plant-notes">📝 ${escapeHtml(p.notes)}</div>` : ''}
            </div>
        `;
    }).join('');
}

// Tampilkan modal tambah tanaman
function showPlantModal() {
    document.getElementById('plantModal').classList.add('show');
    document.getElementById('plantForm').reset();
}

// Sembunyikan modal
function hidePlantModal() {
    document.getElementById('plantModal').classList.remove('show');
}

// (BUG-5 fix): Tutup modal ketika user klik area LUAR modal (backdrop abu-abu)
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('plantModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            // e.target = elemen YANG DIKLIK. Jika sama dengan elemen .modal (bukan anaknya)
            // berarti user klik area backdrop.
            if (e.target === modal) {
                hidePlantModal();
            }
        });
    }

    // (BUG-5 tambahan): Tekan tombol ESC juga menutup modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            hidePlantModal();
        }
    });
});

// Simpan tanaman baru
async function addPlant(e) {
    e.preventDefault();
    // Input dari elemen form (bukan dari innerHTML) -> aman dari XSS selama
    // kita tidak memasukkan ke innerHTML langsung. Tapi untuk berjaga-jaga,
    // nanti backend yang akan menyimpan, dan frontend tetap escape saat render.
    const body = {
        name: document.getElementById('plantName').value.trim(),
        type: document.getElementById('plantType').value,
        status: document.getElementById('plantStatus').value,
        notes: document.getElementById('plantNotes').value.trim()
    };

    try {
        const res = await fetch('/api/plants', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const json = await safeJson(res);
        if (res.ok && json && json.status === 'success') {
            hidePlantModal();
            loadPlants();
            showToast('🌱 Tanaman berhasil ditambahkan!');
        } else if (json && json.error) {
            showToast('⚠ ' + json.error);
        } else {
            showToast('❌ Gagal menyimpan');
        }
    } catch (err) {
        console.error(err);
        showToast('❌ Gagal menyimpan (jaringan error)');
    }
}

// Hapus tanaman
async function deletePlant(id) {
    if (!confirm('Yakin ingin menghapus tanaman ini?')) return;
    try {
        const res = await fetch('/api/plants/' + (Number(id) || 0), { method: 'DELETE' });
        if (res.ok) {
            loadPlants();
            showToast('🗑️ Tanaman dihapus');
        } else {
            showToast('❌ Tanaman tidak ditemukan');
        }
    } catch (err) {
        console.error(err);
        showToast('❌ Gagal menghapus');
    }
}


// ================== JADWAL ==================

async function loadSchedules() {
    try {
        const res = await fetch('/api/schedules');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const schedules = await safeJson(res);
        renderSchedules(schedules || []);
    } catch (err) {
        console.error('Gagal muat jadwal:', err);
    }
}

function renderSchedules(schedules) {
    const container = document.getElementById('schedule-list');

    const doneCount = schedules.filter(s => s.done).length;
    document.getElementById('total-done').textContent = doneCount + '/' + schedules.length;

    if (schedules.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>Tidak ada jadwal.</p>
            </div>
        `;
        return;
    }

    const dayOrder = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'];
    // (BUG-4 fix): Hari yang tidak dikenali (misal typo "senin" / "Selase") indexOf = -1.
    // Kita ubah menjadi indeks 999 (setelah Minggu=6) supaya urut PALING AKHIR.
    schedules.sort((a, b) => {
        let ia = dayOrder.indexOf(a.day);
        let ib = dayOrder.indexOf(b.day);
        if (ia === -1) ia = 999;
        if (ib === -1) ib = 999;
        return ia - ib;
    });

    // Perbaikan SEC-3: s.task, s.day, s.time berasal dari DB (user input seed saat ini),
    // tapi jika nanti ditambah fitur edit jadwal via form user -> wajib escape.
    container.innerHTML = schedules.map(s => `
        <div class="schedule-item">
            <div class="schedule-check ${s.done ? 'done' : ''}" onclick="toggleSchedule(${Number(s.id) || 0})">
                ${s.done ? '✓' : ''}
            </div>
            <div class="schedule-info">
                <div class="schedule-task ${s.done ? 'done' : ''}">${escapeHtml(s.task)}</div>
                <div class="schedule-meta">
                    <span>📅 ${escapeHtml(s.day)}</span>
                    <span>⏰ ${escapeHtml(s.time)}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Tandai jadwal selesai/belum
async function toggleSchedule(id) {
    try {
        const res = await fetch('/api/schedules/' + (Number(id) || 0) + '/toggle', { method: 'POST' });
        if (res.ok) {
            loadSchedules();
        }
    } catch (err) {
        console.error(err);
    }
}
