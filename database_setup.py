import sqlite3
from sqlite3 import Error

# Nama file untuk database SQLite Anda
NAMA_DATABASE = "absensi.db"

def buat_koneksi(db_file):
    """ 
    Membuat koneksi ke database SQLite.
    Jika file db tidak ada, file tersebut akan dibuat.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"Koneksi SQLite berhasil ke versi {sqlite3.version}")
        return conn
    except Error as e:
        print(f"Error saat koneksi ke database: {e}")
    
    return conn

def buat_tabel(conn, sql_perintah_buat_tabel):
    """ 
    Membuat tabel dari string SQL
    """
    try:
        c = conn.cursor()
        c.execute(sql_perintah_buat_tabel)
    except Error as e:
        print(f"Error saat membuat tabel: {e}")

def inisialisasi_database(nama_db):
    """
    Fungsi utama untuk membuat database dan semua tabel di dalamnya.
    """
    
    # SQL untuk membuat tabel Departemen
    sql_tabel_departemen = """
    CREATE TABLE IF NOT EXISTS Departemen (
        dept_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama_departemen VARCHAR(100) NOT NULL UNIQUE
    );
    """

    # SQL untuk membuat tabel Karyawan
    sql_tabel_karyawan = """
    CREATE TABLE IF NOT EXISTS Karyawan (
        work_no INTEGER PRIMARY KEY,
        nama_karyawan VARCHAR(255) NOT NULL,
        dept_id INTEGER,
        status_aktif BOOLEAN DEFAULT 1,
        FOREIGN KEY (dept_id) REFERENCES Departemen (dept_id)
            ON DELETE SET NULL ON UPDATE CASCADE
    );
    """

    # SQL untuk membuat tabel CatatanAbsensi
    sql_tabel_catatan_absensi = """
    CREATE TABLE IF NOT EXISTS CatatanAbsensi (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_no INTEGER NOT NULL,
        tanggal_absensi DATE NOT NULL,
        jam_masuk TIME,
        jam_pulang TIME,
        lembur_masuk TIME,
        lembur_pulang TIME,
        waktu_anomali VARCHAR(255),
        status_validasi VARCHAR(50) DEFAULT 'PENDING',
        catatan_editor TEXT,
        FOREIGN KEY (work_no) REFERENCES Karyawan (work_no)
            ON DELETE CASCADE ON UPDATE CASCADE
    );
    """

    # SQL untuk membuat tabel Pelanggaran
    sql_tabel_pelanggaran = """
    CREATE TABLE IF NOT EXISTS Pelanggaran (
        pelanggaran_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        waktu_mulai TIME,
        waktu_selesai TIME,
        catatan_pelanggaran TEXT,
        FOREIGN KEY (record_id) REFERENCES CatatanAbsensi (record_id)
            ON DELETE CASCADE ON UPDATE CASCADE
    );
    """
    
    # -- Mulai proses --
    conn = buat_koneksi(nama_db)

    if conn is not None:
        # Mengaktifkan Foreign Key constraint
        # (Sangat penting untuk integritas data)
        conn.execute("PRAGMA foreign_keys = ON;")

        # Membuat tabel-tabel
        print("Mencoba membuat tabel Departemen...")
        buat_tabel(conn, sql_tabel_departemen)
        
        print("Mencoba membuat tabel Karyawan...")
        buat_tabel(conn, sql_tabel_karyawan)
        
        print("Mencoba membuat tabel CatatanAbsensi...")
        buat_tabel(conn, sql_tabel_catatan_absensi)
        
        print("Mencoba membuat tabel Pelanggaran...")
        buat_tabel(conn, sql_tabel_pelanggaran)
        
        print("\n✅ Inisialisasi database selesai.")
        
        conn.close()
    else:
        print("❌ ERROR: Tidak dapat membuat koneksi ke database.")

# --- Bagian ini akan berjalan jika Anda menjalankan file ini ---
if __name__ == '__main__':
    """
    Jalankan file ini secara langsung (python database_setup.py)
    HANYA SEKALI untuk membuat file absensi.db Anda.
    """
    print(f"--- Memulai Setup Database '{NAMA_DATABASE}' ---")
    inisialisasi_database(NAMA_DATABASE)
