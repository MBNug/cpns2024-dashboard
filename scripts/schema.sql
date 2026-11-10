-- ============================================================================
-- SSCASN CPNS 2024 3NF Normalized Schema
-- Database: cpns2024.db
-- ============================================================================

CREATE TABLE IF NOT EXISTS instansi (
    instansi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode_instansi VARCHAR(20) UNIQUE,
    nama_instansi TEXT NOT NULL,
    kategori_instansi VARCHAR(20) CHECK(kategori_instansi IN ('Pusat', 'Provinsi', 'Kabupaten/Kota')),
    tukin_min BIGINT DEFAULT 0,
    tukin_max BIGINT DEFAULT 0,
    regulasi_tukin TEXT
);

CREATE TABLE IF NOT EXISTS jurusan (
    jurusan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jenjang VARCHAR(20) NOT NULL,
    nama_jurusan TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS formasi (
    formasi_id VARCHAR(64) PRIMARY KEY,
    instansi_id INTEGER NOT NULL,
    jabatan_nm TEXT NOT NULL,
    lokasi_nm TEXT NOT NULL,
    jenis_formasi VARCHAR(50) DEFAULT 'UMUM',
    jumlah_formasi INTEGER NOT NULL DEFAULT 1,
    jumlah_pelamar INTEGER NOT NULL DEFAULT 0,
    rasio_kompetisi REAL NOT NULL DEFAULT 0.0,
    peluang_lolos_pct REAL NOT NULL DEFAULT 100.0,
    status_keketatan VARCHAR(30) DEFAULT 'Tanpa Pelamar',
    gaji_min BIGINT NOT NULL DEFAULT 0,
    gaji_max BIGINT NOT NULL DEFAULT 0,
    golongan_awal VARCHAR(10),
    gaji_pokok_cpns_80 BIGINT DEFAULT 0,
    pendidikan_raw TEXT,
    FOREIGN KEY (instansi_id) REFERENCES instansi(instansi_id)
);

CREATE TABLE IF NOT EXISTS formasi_jurusan (
    formasi_id VARCHAR(64) NOT NULL,
    jurusan_id INTEGER NOT NULL,
    PRIMARY KEY (formasi_id, jurusan_id),
    FOREIGN KEY (formasi_id) REFERENCES formasi(formasi_id) ON DELETE CASCADE,
    FOREIGN KEY (jurusan_id) REFERENCES jurusan(jurusan_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jurusan_nama ON jurusan(nama_jurusan);
CREATE INDEX IF NOT EXISTS idx_jurusan_jenjang ON jurusan(jenjang);
CREATE INDEX IF NOT EXISTS idx_formasi_instansi ON formasi(instansi_id);
CREATE INDEX IF NOT EXISTS idx_formasi_gaji ON formasi(gaji_min, gaji_max);
CREATE INDEX IF NOT EXISTS idx_formasi_rasio ON formasi(rasio_kompetisi);
CREATE INDEX IF NOT EXISTS idx_formasi_status_keketatan ON formasi(status_keketatan);
CREATE INDEX IF NOT EXISTS idx_formasi_pelamar ON formasi(jumlah_pelamar);
CREATE INDEX IF NOT EXISTS idx_fj_jurusan ON formasi_jurusan(jurusan_id);
CREATE INDEX IF NOT EXISTS idx_fj_formasi ON formasi_jurusan(formasi_id);
