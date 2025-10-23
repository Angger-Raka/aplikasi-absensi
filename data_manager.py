import sqlite3
import pandas as pd
from proses_absensi import proses_absensi_dari_file # Impor fungsi dari file kita sebelumnya
from database_setup import NAMA_DATABASE # Impor nama DB agar konsisten

class DataManager:
    """
    Kelas ini bertindak sebagai 'mesin' atau 'otak' aplikasi.
    Semua logika untuk memindahkan data dari file ke database,
    atau mengambil data dari database untuk ditampilkan ke UI,
    ada di sini.
    """
    def __init__(self, db_file=NAMA_DATABASE):
        """
        Membuka koneksi ke database saat objek DataManager dibuat.
        """
        try:
            self.conn = sqlite3.connect(db_file)
            # Menggunakan Row Factory agar hasil SELECT bisa diakses seperti dictionary
            self.conn.row_factory = sqlite3.Row 
            # Mengaktifkan foreign key
            self.conn.execute("PRAGMA foreign_keys = ON;")
            print(f"DataManager terhubung ke {db_file}")
        except sqlite3.Error as e:
            print(f"Error koneksi ke database: {e}")
            self.conn = None

    def close(self):
        """
        Menutup koneksi database.
        """
        if self.conn:
            self.conn.close()
            print("Koneksi DataManager ditutup.")

    def _get_or_create_departemen(self, nama_dept):
        """
        Fungsi helper untuk memeriksa/membuat departemen.
        Mengembalikan (dept_id).
        """
        if not nama_dept:
            return None
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT dept_id FROM Departemen WHERE nama_departemen = ?", (nama_dept,))
        hasil = cursor.fetchone()
        
        if hasil:
            return hasil['dept_id'] # Kembalikan ID jika sudah ada
        else:
            # Jika tidak ada, buat baru
            cursor.execute("INSERT INTO Departemen (nama_departemen) VALUES (?)", (nama_dept,))
            return cursor.lastrowid # Kembalikan ID yang baru dibuat

    def _sync_karyawan(self, work_no, nama, dept_id):
        """
        Fungsi helper untuk sinkronisasi data karyawan.
        Jika baru -> INSERT. Jika lama -> UPDATE (untuk jaga-jaga jika nama/dept ganti).
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM Karyawan WHERE work_no = ?", (work_no,))
        hasil = cursor.fetchone()
        
        if hasil:
            # Karyawan sudah ada, lakukan UPDATE
            cursor.execute("""
                UPDATE Karyawan 
                SET nama_karyawan = ?, dept_id = ? 
                WHERE work_no = ?
            """, (nama, dept_id, work_no))
        else:
            # Karyawan baru, lakukan INSERT
            cursor.execute("""
                INSERT INTO Karyawan (work_no, nama_karyawan, dept_id) 
                VALUES (?, ?, ?)
            """, (work_no, nama, dept_id))

    def _upsert_catatan_absensi(self, data_absensi):
        """
        Fungsi helper untuk INSERT atau UPDATE (Upsert) catatan absensi.
        Ini mencegah duplikasi data jika file yang sama di-upload 2x.
        """
        cursor = self.conn.cursor()
        # Cek apakah sudah ada data untuk karyawan ini di tanggal ini
        cursor.execute("""
            SELECT record_id FROM CatatanAbsensi 
            WHERE work_no = ? AND tanggal_absensi = ?
        """, (data_absensi['work_no'], data_absensi['tanggal_absensi']))
        
        hasil = cursor.fetchone()
        
        # Data yang akan di-insert atau di-update
        # Mengganti 'N/A' dengan None agar kompatibel dengan database
        data_tuple = (
            data_absensi['work_no'],
            data_absensi['tanggal_absensi'],
            data_absensi['jam_masuk'] if data_absensi['jam_masuk'] != 'N/A' else None,
            data_absensi['jam_pulang'] if data_absensi['jam_pulang'] != 'N/A' else None,
            data_absensi['lembur_masuk'] if data_absensi['lembur_masuk'] != 'N/A' else None,
            data_absensi['lembur_pulang'] if data_absensi['lembur_pulang'] != 'N/A' else None,
            data_absensi['waktu_anomali'] if data_absensi['waktu_anomali'] != 'N/A' else None,
            'PENDING' # Status default saat pertama kali di-upload
        )

        if hasil:
            # SUDAH ADA: Lakukan UPDATE
            record_id = hasil['record_id']
            cursor.execute("""
                UPDATE CatatanAbsensi
                SET jam_masuk = ?, jam_pulang = ?, lembur_masuk = ?, 
                    lembur_pulang = ?, waktu_anomali = ?, status_validasi = 'PENDING'
                WHERE record_id = ?
            """, (data_tuple[2], data_tuple[3], data_tuple[4], data_tuple[5], data_tuple[6], record_id))
        else:
            # BELUM ADA: Lakukan INSERT
            cursor.execute("""
                INSERT INTO CatatanAbsensi 
                (work_no, tanggal_absensi, jam_masuk, jam_pulang, lembur_masuk, lembur_pulang, waktu_anomali, status_validasi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data_tuple)
            record_id = cursor.lastrowid
        
        return record_id

    def import_data_from_log(self, file_path, tanggal_absensi):
        """
        FUNGSI UTAMA UNTUK UI:
        1. Memproses file log.
        2. Sinkronisasi master data (Karyawan, Departemen).
        3. Memasukkan data absensi ke database.
        """
        print(f"Memulai impor dari {file_path} untuk tanggal {tanggal_absensi}...")
        try:
            # 1. Proses file log menggunakan fungsi kita sebelumnya
            df_absensi = proses_absensi_dari_file(file_path)
            
            if df_absensi.empty:
                print("Tidak ada data yang ditemukan di file log.")
                return False

            jumlah_sukses = 0
            # 2. Iterasi setiap baris data di DataFrame
            for _, row in df_absensi.iterrows():
                # 3. Sinkronisasi Master Data
                dept_id = self._get_or_create_departemen(row['Departemen'])
                self._sync_karyawan(row['No'], row['Nama'], dept_id)
                
                # 4. Siapkan data absensi
                data_absensi = {
                    'work_no': row['No'],
                    'tanggal_absensi': tanggal_absensi,
                    'jam_masuk': row['Jam Masuk'],
                    'jam_pulang': row['Jam Pulang'],
                    'lembur_masuk': row['Masuk Lembur'],
                    'lembur_pulang': row['Pulang Lembur'],
                    'waktu_anomali': row['Waktu Anomali']
                }
                
                # 5. Masukkan data absensi (UPSERT)
                self._upsert_catatan_absensi(data_absensi)
                jumlah_sukses += 1

            # 6. Commit semua perubahan ke database
            self.conn.commit()
            print(f"✅ Impor berhasil: {jumlah_sukses} baris data diproses.")
            return True

        except Exception as e:
            # Jika terjadi error, batalkan semua perubahan
            self.conn.rollback()
            print(f"❌ Impor GAGAL: {e}")
            return False

    def get_absensi_data_for_ui(self, start_date, end_date):
        """
        FUNGSI UTAMA UNTUK UI:
        Mengambil data absensi yang sudah digabung dengan nama karyawan
        untuk ditampilkan di tabel UI.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                C.record_id,
                C.tanggal_absensi,
                C.work_no,
                K.nama_karyawan,
                D.nama_departemen,
                C.jam_masuk,
                C.jam_pulang,
                C.lembur_masuk,
                C.lembur_pulang,
                C.waktu_anomali,
                C.status_validasi,
                C.catatan_editor
            FROM CatatanAbsensi C
            JOIN Karyawan K ON C.work_no = K.work_no
            LEFT JOIN Departemen D ON K.dept_id = D.dept_id
            WHERE C.tanggal_absensi BETWEEN ? AND ?
            ORDER BY C.tanggal_absensi, K.nama_karyawan
        """, (start_date, end_date))
        
        # Mengubah hasil (list of rows) menjadi list of dictionaries
        data = [dict(row) for row in cursor.fetchall()]
        return data

    # -----------------------------------------------------------------
    # --- FUNGSI BARU UNTUK REPORTING (LAPORAN) ---
    # -----------------------------------------------------------------

    def get_rekap_absensi(self, start_date, end_date):
        """
        FUNGSI UNTUK LAPORAN:
        Membuat rekapitulasi absensi per karyawan (Total hari masuk)
        dalam rentang tanggal yang ditentukan.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                K.work_no,
                K.nama_karyawan,
                D.nama_departemen,
                COUNT(C.record_id) AS total_hari_masuk,
                SUM(CASE WHEN C.status_validasi = 'PENDING' THEN 1 ELSE 0 END) AS total_pending,
                SUM(CASE WHEN C.waktu_anomali IS NOT NULL THEN 1 ELSE 0 END) AS total_anomali
            FROM CatatanAbsensi C
            JOIN Karyawan K ON C.work_no = K.work_no
            LEFT JOIN Departemen D ON K.dept_id = D.dept_id
            WHERE C.tanggal_absensi BETWEEN ? AND ?
            GROUP BY K.work_no, K.nama_karyawan, D.nama_departemen
            ORDER BY K.nama_karyawan
        """, (start_date, end_date))
        
        data = [dict(row) for row in cursor.fetchall()]
        return data

    def get_laporan_pelanggaran(self, start_date, end_date):
        """
        FUNGSI UNTUK LAPORAN:
        Mengambil semua catatan pelanggaran dalam rentang tanggal
        untuk dilaporkan.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                P.pelanggaran_id,
                C.tanggal_absensi,
                K.nama_karyawan,
                D.nama_departemen,
                P.waktu_mulai,
                P.waktu_selesai,
                P.catatan_pelanggaran
            FROM Pelanggaran P
            JOIN CatatanAbsensi C ON P.record_id = C.record_id
            JOIN Karyawan K ON C.work_no = K.work_no
            LEFT JOIN Departemen D ON K.dept_id = D.dept_id
            WHERE C.tanggal_absensi BETWEEN ? AND ?
            ORDER BY C.tanggal_absensi, K.nama_karyawan
        """, (start_date, end_date))
        
        data = [dict(row) for row in cursor.fetchall()]
        return data


# --- Contoh Penggunaan ---
if __name__ == '__main__':
    """
    Bagian ini untuk menguji 'mesin' kita secara manual.
    UI Anda nanti akan memanggil fungsi-fungsi ini.
    """
    
    # Inisialisasi DataManager
    manager = DataManager()

    if manager.conn:
        # --- Skenario 1: Uji coba impor data ---
        # Ganti dengan path file Anda yang valid
        # GANTI '10 OKT 2025_ABSENSI.xls' dengan nama file Anda
        # GANTI '2025-10-10' dengan tanggal yang sesuai
        
        # file_log = "10 OKT 2025_ABSENSI.xls" 
        # tanggal_log = "2025-10-10"
        # manager.import_data_from_log(file_log, tanggal_log)
        
        # print("\n--- Menjalankan ulang impor (uji coba anti-duplikasi) ---")
        # manager.import_data_from_log(file_log, tanggal_log)


        # --- Skenario 2: Uji coba mengambil data untuk UI ---
        print("\n--- Mengambil data untuk rentang tanggal '2025-10-01' s/d '2025-10-31' ---")
        data_laporan = manager.get_absensi_data_for_ui('2025-10-01', '2025-10-31')
        
        if data_laporan:
            print(f"Ditemukan {len(data_laporan)} catatan absensi:")
            for catatan in data_laporan:
                print(f"  > {catatan['tanggal_absensi']} - {catatan['nama_karyawan']} ({catatan['status_validasi']})")
        else:
            print("Tidak ada data ditemukan untuk rentang tanggal tersebut.")

        # Tutup koneksi
        manager.close()

        # --- Skenario 3: Uji coba fungsi laporan ---
        print("\n--- Mengambil Laporan Rekap Absensi (Bulanan) ---")
        manager_laporan = DataManager()
        if manager_laporan.conn:
            rekap_absensi = manager_laporan.get_rekap_absensi('2025-10-01', '2025-10-31')
            if rekap_absensi:
                print(f"Ditemukan {len(rekap_absensi)} rekap karyawan:")
                for rekap in rekap_absensi:
                    print(f"  > {rekap['nama_karyawan']} - Masuk: {rekap['total_hari_masuk']} hari, Anomali: {rekap['total_anomali']}")
            
            print("\n--- Mengambil Laporan Pelanggaran (Bulanan) ---")
            laporan_pelanggaran = manager_laporan.get_laporan_pelanggaran('2025-10-01', '2025-10-31')
            if laporan_pelanggaran:
                print(f"Ditemukan {len(laporan_pelanggaran)} catatan pelanggaran:")
                for pelanggaran in laporan_pelanggaran:
                    print(f"  > {pelanggaran['tanggal_absensi']} - {pelanggaran['nama_karyawan']}: {pelanggaran['catatan_pelanggaran']}")

            manager_laporan.close()

