import sys
import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QFormLayout, QPushButton, QDateEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox
)
from PySide6.QtCore import QDate, Qt

from data_manager import DataManager # Impor 'mesin' kita
from database_setup import NAMA_DATABASE # Untuk pengecekan file DB

class App(QMainWindow):
    """
    Kelas utama untuk Aplikasi UI Absensi, dibangun dengan PySide6.
    """
    def __init__(self):
        super().__init__()
        
        self.title = "Manajemen Absensi Karyawan (PySide6)"
        self.geometry = (1200, 700)
        
        # Inisialisasi 'mesin' DataManager
        self.manager = DataManager()
        if not self.manager.conn:
            # Tampilkan error sebelum jendela utama dibuat
            QMessageBox.critical(None, "Error Database", "Gagal terhubung ke database. Aplikasi akan ditutup.")
            sys.exit(1) # Keluar jika DB gagal konek

        self.initUI()
        
        # Muat data awal saat aplikasi dibuka
        self.muat_data_absensi()

    def initUI(self):
        """
        Membuat semua komponen UI (tombol, tabel, layout).
        """
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, self.geometry[0], self.geometry[1])
        
        # Widget utama sebagai 'pusat' dari QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout utama
        main_layout = QVBoxLayout(central_widget)

        # --- 1. Frame Kontrol Atas (Upload & Filter) ---
        kontrol_layout = QHBoxLayout()
        
        # --- Bagian Upload ---
        upload_box = QGroupBox("Upload Log Absensi")
        upload_layout = QFormLayout()
        
        self.tgl_upload = QDateEdit(calendarPopup=True)
        self.tgl_upload.setDate(QDate.currentDate())
        self.tgl_upload.setDisplayFormat('yyyy-MM-dd')
        
        self.btn_pilih_file = QPushButton("Pilih File & Upload")
        self.btn_pilih_file.clicked.connect(self.upload_log_file)
        
        upload_layout.addRow("Tanggal Log:", self.tgl_upload)
        upload_layout.addRow(self.btn_pilih_file)
        upload_box.setLayout(upload_layout)

        # --- Bagian Filter ---
        filter_box = QGroupBox("Filter Tampilan Data")
        filter_layout = QFormLayout()

        self.tgl_mulai = QDateEdit(calendarPopup=True)
        self.tgl_mulai.setDate(QDate.currentDate().addDays(-QDate.currentDate().day() + 1)) # Tgl 1 bulan ini
        self.tgl_mulai.setDisplayFormat('yyyy-MM-dd')

        self.tgl_selesai = QDateEdit(calendarPopup=True)
        self.tgl_selesai.setDate(QDate.currentDate()) # Hari ini
        self.tgl_selesai.setDisplayFormat('yyyy-MM-dd')
        
        self.btn_muat_data = QPushButton("Muat Data")
        self.btn_muat_data.clicked.connect(self.muat_data_absensi)
        
        filter_layout.addRow("Dari:", self.tgl_mulai)
        filter_layout.addRow("Sampai:", self.tgl_selesai)
        filter_layout.addRow(self.btn_muat_data)
        filter_box.setLayout(filter_layout)

        kontrol_layout.addWidget(upload_box)
        kontrol_layout.addWidget(filter_box)
        kontrol_layout.addStretch(1) # Tambahkan spasi di kanan
        
        main_layout.addLayout(kontrol_layout)

        # --- 2. Tabel Data (Tabel Utama) ---
        self.tabel_data = QTableWidget()
        self.kolom_tabel_map = {
            'record_id': 'ID',
            'tanggal_absensi': 'Tanggal',
            'work_no': 'No.Kerja',
            'nama_karyawan': 'Nama Karyawan',
            'nama_departemen': 'Departemen',
            'jam_masuk': 'Masuk',
            'jam_pulang': 'Pulang',
            'lembur_masuk': 'Lembur Masuk',
            'lembur_pulang': 'Lembur Pulang',
            'waktu_anomali': 'Anomali',
            'status_validasi': 'Status',
            'catatan_editor': 'Catatan'
        }
        
        self.kolom_db = list(self.kolom_tabel_map.keys()) # Urutan kolom dari DB
        self.kolom_tabel = list(self.kolom_tabel_map.values()) # Judul yang tampil di UI
        
        self.tabel_data.setColumnCount(len(self.kolom_tabel))
        self.tabel_data.setHorizontalHeaderLabels(self.kolom_tabel)
        
        # Pengaturan tampilan tabel
        self.tabel_data.verticalHeader().setVisible(False)
        self.tabel_data.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Tidak bisa diedit
        self.tabel_data.setAlternatingRowColors(True)
        self.tabel_data.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        header = self.tabel_data.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.kolom_db.index('nama_karyawan'), QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.kolom_db.index('catatan_editor'), QHeaderView.ResizeMode.Stretch)

        main_layout.addWidget(self.tabel_data)

    def muat_data_absensi(self):
        """
        Menghubungi DataManager untuk mengambil data absensi
        dan menampilkannya di QTableWidget.
        """
        # 1. Hapus data lama di tabel
        self.tabel_data.setRowCount(0)
            
        # 2. Ambil tanggal filter dari UI
        tgl_mulai = self.tgl_mulai.date().toString('yyyy-MM-dd')
        tgl_selesai = self.tgl_selesai.date().toString('yyyy-MM-dd')
        
        # 3. Panggil 'mesin' untuk ambil data
        try:
            data_absensi = self.manager.get_absensi_data_for_ui(tgl_mulai, tgl_selesai)
            
            # 4. Masukkan data baru ke tabel
            self.tabel_data.setRowCount(len(data_absensi))
            
            for row_idx, catatan in enumerate(data_absensi):
                for col_idx, nama_kolom_db in enumerate(self.kolom_db):
                    # Ganti None dengan string kosong
                    nilai = catatan.get(nama_kolom_db, '')
                    if nilai is None:
                        nilai = ''
                    
                    item = QTableWidgetItem(str(nilai))
                    
                    # Beri warna pada status
                    if nama_kolom_db == 'status_validasi':
                        if nilai == 'PENDING':
                            item.setBackground(Qt.GlobalColor.yellow)
                        elif nilai == 'VALID':
                            item.setBackground(Qt.GlobalColor.green)
                    
                    self.tabel_data.setItem(row_idx, col_idx, item)
                
        except Exception as e:
            QMessageBox.critical(self, "Error Pengambilan Data", f"Gagal mengambil data dari database: {e}")

    def upload_log_file(self):
        """
        Membuka dialog pilih file, kemudian memanggil 'mesin'
        untuk memproses dan mengimpor file tersebut.
        """
        # 1. Buka dialog untuk memilih file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih file log absensi",
            "", # Direktori awal
            "File Excel/CSV (*.xls *.xlsx *.csv);;All files (*.*)"
        )
        
        if not file_path:
            return # User membatalkan dialog

        # 2. Ambil tanggal absensi dari UI
        tanggal_log = self.tgl_upload.date().toString('yyyy-MM-dd')
        
        # 3. Konfirmasi kepada user
        konfirmasi_box = QMessageBox(self)
        konfirmasi_box.setIcon(QMessageBox.Icon.Question)
        konfirmasi_box.setWindowTitle("Konfirmasi Upload")
        konfirmasi_box.setText(f"Anda akan meng-upload file:\n{file_path}\n\nUntuk tanggal absensi:\n{tanggal_log}\n\nLanjutkan?")
        konfirmasi_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        konfirmasi_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if konfirmasi_box.exec() == QMessageBox.StandardButton.No:
            return

        # 4. Panggil 'mesin' untuk impor data
        try:
            sukses = self.manager.import_data_from_log(file_path, tanggal_log)
            
            if sukses:
                QMessageBox.information(self, "Sukses", "Data dari file log berhasil diimpor ke database.")
                # Refresh tabel untuk menampilkan data baru
                self.muat_data_absensi()
            else:
                QMessageBox.warning(self, "Gagal Impor", "Impor data gagal. Periksa konsol untuk detail error.")
        except Exception as e:
            QMessageBox.critical(self, "Error Kritis Impor", f"Terjadi error saat impor: {e}")

    def closeEvent(self, event):
        """
        Fungsi yang dipanggil saat jendela aplikasi ditutup (override).
        """
        konfirmasi = QMessageBox.question(self, "Keluar", "Apakah Anda yakin ingin keluar?")
        
        if konfirmasi == QMessageBox.StandardButton.Yes:
            # Tutup koneksi database sebelum keluar
            self.manager.close()
            event.accept() # Izinkan jendela ditutup
        else:
            event.ignore() # Batalkan penutupan

if __name__ == "__main__":
    # Pastikan database sudah dibuat
    try:
        f = open(NAMA_DATABASE)
        f.close()
    except FileNotFoundError:
        QMessageBox.critical(None, "Error Database", f"File database '{NAMA_DATABASE}' tidak ditemukan!\n\nJalankan 'python database_setup.py' terlebih dahulu.")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())

