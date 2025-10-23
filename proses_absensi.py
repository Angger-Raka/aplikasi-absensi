import pandas as pd
import re
import os # Digunakan untuk memeriksa ekstensi file
import sys

# --- Pemeriksaan Library Penting ---
# Cek apakah library untuk membaca file Excel sudah terinstal
try:
    import openpyxl
except ImportError:
    print("WARNING: Library 'openpyxl' tidak ditemukan. Diperlukan untuk membaca file .xlsx.")
    print("Silakan install dengan: pip install openpyxl")

try:
    import xlrd
except ImportError:
    print("WARNING: Library 'xlrd' tidak ditemukan. Diperlukan untuk membaca file .xls.")
    print("Silakan install dengan: pip install xlrd")

# -----------------------------------

def proses_absensi_dari_file(file_path):
    """
    Membaca file absensi (bisa .xls, .xlsx, atau .csv) dan mengekstrak data
    nama, departemen, jam masuk/pulang, jam lembur, dan waktu anomali.

    Args:
        file_path (str): Path lengkap menuju file absensi Anda.

    Returns:
        pandas.DataFrame: Sebuah DataFrame berisi data yang sudah bersih 
                          jika sukses, atau DataFrame kosong jika gagal.
    """
    
    # Menentukan kolom-kolom yang akan digunakan
    KOLOM_OUTPUT = [
        'No', 'Nama', 'Departemen', 'Jam Masuk', 'Jam Pulang', 
        'Masuk Lembur', 'Pulang Lembur', 'Waktu Anomali'
    ]

    # Memeriksa apakah file ada
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File tidak ditemukan di path: {file_path}")
        # Mengembalikan DataFrame kosong dengan struktur yang diharapkan
        return pd.DataFrame(columns=KOLOM_OUTPUT)

    df = None
    try:
        # Memisahkan nama file dan ekstensinya
        nama_file, ekstensi = os.path.splitext(file_path)
        ekstensi = ekstensi.lower()

        # --- Logika Cerdas untuk Membaca Berbagai Format ---
        if ekstensi in ['.xls', '.xlsx']:
            # Menggunakan pd.read_excel() yang otomatis memilih engine
            # (xlrd untuk .xls, openpyxl untuk .xlsx)
            df = pd.read_excel(file_path, header=None)
        
        elif ekstensi == '.csv':
            # Menggunakan pd.read_csv() untuk file CSV
            # 'latin1' adalah encoding yang umum untuk file non-standar
            df = pd.read_csv(file_path, header=None, encoding='latin1')
        
        else:
            print(f"❌ ERROR: Format file '{ekstensi}' tidak didukung. Harap gunakan .xls, .xlsx, atau .csv.")
            return pd.DataFrame(columns=KOLOM_OUTPUT)

    except ImportError as e:
        print(f"❌ ERROR: Library yang dibutuhkan hilang. {e}")
        print("Pastikan Anda sudah menginstal 'openpyxl' (untuk .xlsx) dan 'xlrd' (untuk .xls).")
        return pd.DataFrame(columns=KOLOM_OUTPUT)
    except Exception as e:
        print(f"❌ ERROR saat membaca file: {e}")
        return pd.DataFrame(columns=KOLOM_OUTPUT)

    # --- Logika Parsing Data (Sama seperti sebelumnya) ---
    records = []
    if df is not None:
        for i in range(len(df)):
            # Ubah seluruh baris menjadi sebuah string tunggal untuk pencarian
            # str(cell or '') menangani jika ada sel kosong (None)
            row_str = ' '.join(str(cell or '') for cell in df.iloc[i].values)

            # Kondisi untuk menemukan baris data utama karyawan
            if 'Work No' in row_str and 'Name' in row_str and 'Dept.' in row_str:
                # Pastikan ada baris berikutnya untuk data waktu
                if i + 1 < len(df):
                    try:
                        # Ambil data dari sel di posisi yang sesuai
                        work_no = int(df.iloc[i, 2])
                        name = str(df.iloc[i, 6])
                        department = str(df.iloc[i, 12])
                        
                        # Ambil data waktu dari baris berikutnya
                        time_cell = str(df.iloc[i+1, 1])
                        
                        # --- PERUBAHAN LOGIKA WAKTU ---
                        # Mencari semua format jam (HH:MM atau HH.MM)
                        # Regex '[:.]' berarti 'cocokkan dengan : ATAU .'
                        times = re.findall(r'\d{2}[:.]\d{2}', time_cell)
                        
                        # Alokasikan jam kerja dan jam lembur (4 waktu pertama)
                        clock_in = times[0] if len(times) > 0 else 'N/A'
                        clock_out = times[1] if len(times) > 1 else 'N/A'
                        overtime_in = times[2] if len(times) > 2 else 'N/A'
                        overtime_out = times[3] if len(times) > 3 else 'N/A'

                        # BARU: Alokasikan waktu anomali (semua waktu SETELAH 4 waktu pertama)
                        anomaly_times_list = times[4:] # Mengambil sisa waktu (jika ada)
                        anomaly_times = ", ".join(anomaly_times_list) if anomaly_times_list else 'N/A'

                        records.append([
                            work_no, name, department, clock_in, 
                            clock_out, overtime_in, overtime_out,
                            anomaly_times # Menambahkan data anomali
                        ])
                    
                    except (ValueError, IndexError, TypeError):
                        # Jika ada baris yang mirip data tapi formatnya rusak, lewati saja
                        continue

    # Membuat DataFrame akhir dari data yang terkumpul
    clean_df = pd.DataFrame(records, columns=KOLOM_OUTPUT)
    
    return clean_df

# ---------------------------------------------------------------------------
# --- CONTOH CARA MENGGUNAKAN FUNGSI INI ---
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Blok ini HANYA akan berjalan jika Anda menjalankan file ini
    # secara langsung (misal: python proses_absensi.py)
    
    print("--- Menjalankan Tes Fungsi ---")
    
    # Ganti ini dengan nama file Anda
    # Coba ganti dengan "10 OKT 2025_ABSENSI.xls" atau file .xlsx Anda
    # file_saya = "Attendance log (1)-Saveds.xlsx" 
    file_saya = "Anomali Log.xlsx" # Contoh jika Anda punya file ini
    # file_saya = "file_tidak_ada.xls" # Contoh untuk tes error

    # 1. Memanggil fungsi
    data_absensi_df = proses_absensi_dari_file(file_saya)

    # 2. Memeriksa hasil
    if data_absensi_df.empty:
        print("\n🟡 Hasil: Gagal memproses file atau file tidak mengandung data.")
    else:
        print(f"\n✅ SUKSES! Berhasil memproses {len(data_absensi_df)} data karyawan.")
        
        # 3. Menampilkan hasil (DataFrame)
        print("\n--- Tampilan Data (Tabel/DataFrame) ---")
        # Mengatur opsi display Pandas agar semua kolom terlihat
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print(data_absensi_df)
        
        # 4. Menampilkan hasil (Array)
        data_absensi_array = data_absensi_df.to_numpy()
        print("\n--- Tampilan Data (Array) ---")
        print(data_absensi_array)

    # --- Contoh cara menggunakan di file lain ---
    # Di file Python Anda yang lain (misal app.py), Anda bisa lakukan:
    #
    # from proses_absensi import proses_absensi_dari_file
    #
    # data = proses_absensi_dari_file("path/ke/file/anda.xlsx")
    # if not data.empty:
    print("Data berhasil didapat!")
    #     print(data)

