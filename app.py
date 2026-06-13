import sys
import sqlite3
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from PyQt5 import QtWidgets, QtCore, QtGui

# Variabel global untuk menandai apakah login sukses atau tidak
LOGIN_SUCCESS = False

# MENYAMAKAN JUDUL FILE DATABASE DENGAN YANG KAMU BUAT DI FOLDER
DB_LOGIN_PATH = "manajemen_akses.db"
DB_ANALISIS_PATH = "logistik_hortikultura.db"


# ==============================================================================
# FUNCTION ANTI-GAGAL: MENGUBAH DATA BASE64 LOGO MENJADI QPIXMAP (PYQT5)
# ==============================================================================
def dapatkan_ikon_logo():
    """Fungsi ini menyimpan data string biner dari logo lingkaran hijau pertanianmu.
    Memastikan logo selalu bisa dipanggil di PC mana pun tanpa takut file hilang."""
    base64_data = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAACXBIWXMAAAsTAAALEwEAmpwYAAAG"
        "QWlUWHRYbXDynamicQY29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6"
        "TlRjemtjOWQiPz4KPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWG1wIENvcmUg"
        "OS4xLWMwMDEgNzkuYjExZTYzYSwgMjAyNC／0My8wOS0xODoyMDozNyAgICAgICAgIj4KIDxyZGY6UkRGIHhtbG5zOnJkZj0i"
        "aHR0cDovL3d3dy53My5vcmcvMTk5OS8wMi8yMi1cmRmLXN5bnRheC1ucyMiPgogIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFi"
        "b3V0PSIiCiAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iCiAgICB4bWxuczp4bXBNTT0iaHR0"
        "cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIKICAgIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8i"
        "LjAvc0RhdGEvSGlzdG9yeS8iCiAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgICB4"
        "bXBNTTpPcmlnaW5hbERvY3VtZW50SUQ9InhtcC5kaWQ6YWZlOTAwMTgtNzJiMS00NmZlLTg2YzUtNzAxNGE1ZmRkOWMwIgog"
        "ICAgeG1wTU06RG9jdW1lbnRJRD0ieG1wLmRpZDozRTZDMjU0MEVCMTExMUVFOTU2Q0U2REU5QUQxMEMwRCIKICAgIHhtcE1N"
        "OlVuaXF1ZUlEPSJ4bXAuZGlkOjNFNkMyNTQwRUJGMTExRUU5NTZDRTZERTlBRDEwQzBEIgogICAgeG1wOkNyZWF0b3JUb29s"
        "PSJBZG9iZSBQaG90b3Nob3AgMjQuMCAoV2luZG93cykiPgogICA8eG1wTU06RGVyaXZlZEZyb20gcmRmOnBhcnNlVHlwZT0i"
        "UmVzb3VyY2UiPgogICAgPHN0UmVmOmluc3RhbmNlSUQ9InhtcC5paWQ6YWY5ZWNjNTYtYWE4Mi00MThmLThkOTctOTBlNmEx"
        "YmI3ODU3Ii8+CiAgICA8c3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDphZmU5MDAxgtNzJiMS00NmZlLTg2YzUtNzAxNGE1"
        "ZmRkOWMwIi8+CiAgIDwveG1wTU06RGVyaXZlZEZyb20+CiAgIDxkYzp0aXRsZT4KICAgIDxyZGY6QWx0PgogICAgIDxyZGY6"
        "bGkgeG1sOmxhbmc9IngtZGVmYXVsdCI+UGVydGFuaWFuIExvZ2lzdGlrPC9yZGY6bGk+CiAgICA8L3JkZjpBbHQ+CiAgIDwv"
        "ZGM6dGl0bGU+CiAgPC9yZGY6RGVzY3JpcHRpb24+CiA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgo8P3hwYWNrZXQgZW5kPSJ3"
        "Ij8+22HhQgAACbVJREFUeJzt3XtsU9cdwPHvPfZzY8fOixAnb/IuAsS8S9MWeVCIpYwV6DoNo9NInbSpbVvVNm3S/pE27Z9W"
        "m6ZNpU3XpE0bW9OmpS0vS9uY0Gg7KFAgBAgECCFAAhAIecmxn+fuj8uN3YTEid849v0u6S9fXpzzu8fXv7vPuefce6yw"
        "sLCwOCAsTo9gZz6fTxUKhUilUrAsC7PZjMvlIhaLwW63Y7VacblcsFgs8Hg88Hg8CIKAw+GArusgCMAwjA0fhmHAbrfz/X4b"
        "hmGAsf7bLJZlcRxHhmGQYRh0XV97bxgGURw9w7Z/b8f9/YvjOEiShCzLe75HkiS/328mEonAsiwwDIOmaSSTSSiKAsuyyGQy"
        "UBQFhmFsGLZ/ZlmWdF1fS9/Yw9N1fS99hmGQpmlrf0uShCRJa7+RZZkEQdgr3bIsyLKMJEmQZfkvD8MwSJK056fX60W32+G4"
        "Xw3O+7VAEETo9XpWFAVp29wWw7IsciKRECRJgqIocByvBsuybCQSkffv/wXncy89r0eO+9Yge+YdZ/u/YRiEw2EQBAGCIAAm"
        "E9hsAEmCgskEmEwgiSIURoPCoAAFE8CgIDNoUCDDAEUx9G9DoFAUDZgAgAEmE6DRgEkEwAASYAKAmPfvAYCiAAVoNIDGAFEw"
        "gWBygAgTmEAgAiaAAYIJIKgAjAqiCsAAnAnAqAAKIIAmgGACCIAAggkABmBCgAEEDCCAQIIBGAwggAgEEwAGABhAgInMoAEB"
        "BhBoAI0GIswAGg0YNGDRgEEDRjNoNGDQgEEDRhNIDBpNIDFoDNBgAoMGAhoIaCCggYAGAmggMGAgAwYCAwYCDCDAAAIBBhAI"
        "MIDAgIEMGAgwoMEDBh4A"
        "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEgAACxIB0t1+/AAA"
        "ABx0RVh0U29mdHdhcmUAQWRvYmUgRmlyZXdvcmtzIENTNui8sowAAAAWdEVYdENyZWF0aW9uIFRpbWUKMDkvMjEvMTfSUt0N"
        "AAADb0lEQVR4nO2bS2hcVRSGv30m09S0SZO0SZO0pS0+wEexYgUfVBTBjeCDoCg+wEepID6wKkWwKkWwKkVwUfBBpSg+wEep"
        "ID7QR9vSJrVJ0zSZOclcmYvThGlm7tzHzDl38v9gs8mZf66Z/8w599wz9wJKSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJSUlJ"
        "SUlJSUlJSclgAnvofA9wD/AYUAdagS6wDTgInAKeLp+nAtgB7AF+Bq7L9pXy7w65fgtYAlreH6vNfX6XfP5WtlXv7Z6vA9v7"
        "/K3v+Z/b/O9uA3v8b27/f+m6+1f7MvW+T9f9q+836V98f09gU+XzVf7M92fVwz6b+u6q97t8zGNDX6bbt3/v+SrtC6X7N/g6"
        "9T36/l7f37P6Fw/9mXpfU2Bf8bFmveY68AnwPvAAsD3PdwKzwAngetnWAfQA9wI/AtfKdpV9N/V8DXgZWAZaoz3AInANeIdq"
        "rBw/AseB96mO/Xm/vR47Nf06v8wR6rHeVPafeozX1GP8b8f8Mscd6/VpZf78rGPGz3Xp9vPr9uWq9wK7qMaYpBrj/fK4BjwP"
        "vAnMAA3fXwdmgfNlfV29PwYcoToW5/1O2R4D3gfmgUbP/fUAs1TfUdfvDwEnqY7Fef8G1bHYZ//9p8wfqPclBfar3psC+wS2"
        "A3vL4xrVeA6wHeO39f4G1X93R2D/pXof8D7Vf/bS/X0uH+O+v3Gq377T7fsh8BfVb/b0vN31gGrM9+r7e3VvDqS/V70vKbDv"
        "ofv/C/zI9dfI9wF7ZfsX6f83D9gn25eU8vK9wAnvX9C91K977v8D7wN7BnyDqfcH9B57Fj8E/gC+BzZl+yrwIfXv/lXp/mP5"
        "Pgzc6zXq7fVzXwbuA96V7f77b8h1YEq2b8p7G7hHtkfk+xrwsXxeLf9/Atwp2wfeX5XrALbJ569le9rv77eU7f+v/p6vYm8F"
        "XgZekvXp9+eAr4BzwD9eX3/XpZSTwA/AF8Bl4B/gJvB3KfcB38jmPtlckfUv899wEviauU/f7vnaWwJuAjeAb6R8lXKfL6X/"
        "/wL9u7T+D4vLfwS2bSreS0pKSkpKSkpKSkpKSkpKSkpKSkpKSkpKSkpKStoX/AOfN9IbeA5bDwAAAABJRU5CYII="
    )
    # Hapus prefix header data URI jika terbawa agar bisa di-decode oleh QByteArray
    if "," in base64_data:
        base64_data = base64_data.split(",")[1]
    
    byte_array = QtCore.QByteArray.fromBase64(base64_data.encode())
    pixmap = QtGui.QPixmap()
    pixmap.loadFromData(byte_array, "PNG")
    return pixmap


# ==============================================================================
# 1. BAGIAN PYQT5: LOGIN & SIGN UP (DENGAN LOGO PERMANEN & DATABASE)
# ==============================================================================

class LoginWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.resize(536, 851)
        
        # Mengatur warna latar belakang aplikasi PyQt5 menjadi abu-abu terang serasi dengan dashboard
        self.setStyleSheet("background-color: #f3f3f3;")

        self.centralwidget = QtWidgets.QWidget()
        self.setCentralWidget(self.centralwidget)

        # KOMPONEN BARU: Menampilkan Logo Kelompok Tepat di Tengah Atas Form
        self.lbl_logo = QtWidgets.QLabel(self.centralwidget)
        self.lbl_logo.setGeometry(213, 60, 110, 110)  # Diposisikan tepat di tengah horisontal (536 - 110)/2 = 213
        self.lbl_logo.setPixmap(dapatkan_ikon_logo())
        self.lbl_logo.setScaledContents(True)

        # Judul Aplikasi teks tambahan di bawah logo
        self.lbl_title = QtWidgets.QLabel("Aplikasi Hortikultura", self.centralwidget)
        self.lbl_title.setGeometry(50, 185, 431, 35)
        self.lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-family: sans-serif; font-size: 18px; font-weight: bold; color: #333333;")

        self.username = QtWidgets.QLineEdit(self.centralwidget)
        self.username.setGeometry(50, 280, 421, 71)
        self.username.setPlaceholderText("Username")
        self.username.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; border-radius: 4px; padding-left: 10px; font-size: 14px;")

        self.password = QtWidgets.QLineEdit(self.centralwidget)
        self.password.setGeometry(50, 400, 421, 71)
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; border-radius: 4px; padding-left: 10px; font-size: 14px;")

        self.btn_login = QtWidgets.QPushButton("LOG IN", self.centralwidget)
        self.btn_login.setGeometry(170, 510, 181, 51)
        self.btn_login.setStyleSheet("background-color: #1976d2; color: white; font-weight: bold; font-size: 14px; border-radius: 4px;")

        self.btn_signup = QtWidgets.QPushButton("Create Account", self.centralwidget)
        self.btn_signup.setGeometry(300, 638, 100, 25)
        self.btn_signup.setStyleSheet("color: #1976d2; border: none; font-weight: bold; text-align: left; background: transparent;")

        # Teks label pemanis di sebelah tombol create account
        self.lbl_hint = QtWidgets.QLabel("Have not account?", self.centralwidget)
        self.lbl_hint.setGeometry(180, 638, 115, 25)
        self.lbl_hint.setStyleSheet("color: #555555; background: transparent;")

        self.btn_login.clicked.connect(self.login)
        self.btn_signup.clicked.connect(self.open_signup)

    def open_signup(self):
        self.signup_window = SignupWindow()
        self.signup_window.show()
        self.close()

    def login(self):
        global LOGIN_SUCCESS
        username = self.username.text()
        password = self.password.text()

        try:
            conn = sqlite3.connect(DB_LOGIN_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (username, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                QtWidgets.QMessageBox.information(self, "Berhasil", "Login Berhasil")
                LOGIN_SUCCESS = True
                self.close()
            else:
                QtWidgets.QMessageBox.warning(self, "Gagal", "Username atau Password Salah")
        except sqlite3.OperationalError:
            QtWidgets.QMessageBox.critical(
                self, "Error Database", 
                f"File '{DB_LOGIN_PATH}' bermasalah.\nPastikan nama tabel 'data_pengguna' dan strukturnya benar."
            )


class SignupWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sign Up")
        self.resize(535, 849)
        self.setStyleSheet("background-color: #f3f3f3;")

        self.centralwidget = QtWidgets.QWidget()
        self.setCentralWidget(self.centralwidget)

        # KOMPONEN BARU: Menampilkan Logo Kelompok Tepat di Tengah Atas Form Sign Up
        self.lbl_logo = QtWidgets.QLabel(self.centralwidget)
        self.lbl_logo.setGeometry(212, 50, 110, 110)
        self.lbl_logo.setPixmap(dapatkan_ikon_logo())
        self.lbl_logo.setScaledContents(True)

        self.lbl_title = QtWidgets.QLabel("Create Account", self.centralwidget)
        self.lbl_title.setGeometry(50, 175, 435, 35)
        self.lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-family: sans-serif; font-size: 20px; font-weight: bold; color: #437c37;")

        self.email = QtWidgets.QLineEdit(self.centralwidget)
        self.email.setGeometry(140, 250, 261, 41)
        self.email.setPlaceholderText("Email")
        self.email.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; border-radius: 4px; padding-left: 8px;")

        self.password = QtWidgets.QLineEdit(self.centralwidget)
        self.password.setGeometry(140, 320, 261, 41)
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; border-radius: 4px; padding-left: 8px;")

        self.confirm = QtWidgets.QLineEdit(self.centralwidget)
        self.confirm.setGeometry(140, 390, 261, 41)
        self.confirm.setPlaceholderText("Confirm Password")
        self.confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirm.setStyleSheet("background-color: white; border: 1px solid #c0c0c0; border-radius: 4px; padding-left: 8px;")

        self.btn_signup = QtWidgets.QPushButton("Sign Up", self.centralwidget)
        self.btn_signup.setGeometry(200, 480, 121, 41)
        self.btn_signup.setStyleSheet("background-color: #437c37; color: white; font-weight: bold; border-radius: 4px;")

        self.btn_login = QtWidgets.QPushButton("Log In", self.centralwidget)
        self.btn_login.setGeometry(330, 580, 81, 20)
        self.btn_login.setStyleSheet("color: #437c37; border: none; font-weight: bold; text-align: left; background: transparent;")

        self.lbl_hint = QtWidgets.QLabel("Already have an account?", self.centralwidget)
        self.lbl_hint.setGeometry(180, 580, 145, 20)
        self.lbl_hint.setStyleSheet("color: #555555; background: transparent;")

        self.btn_signup.clicked.connect(self.signup)
        self.btn_login.clicked.connect(self.open_login)

    def signup(self):
        email = self.email.text()
        password = self.password.text()
        confirm = self.confirm.text()

        if email == "" or password == "":
            QtWidgets.QMessageBox.warning(self, "Error", "Semua data harus diisi")
            return

        if password != confirm:
            QtWidgets.QMessageBox.warning(self, "Error", "Password tidak sama")
            return

        try:
            conn = sqlite3.connect(DB_LOGIN_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO data_pengguna (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            conn.close()

            QtWidgets.QMessageBox.information(
                self, "Berhasil", "Akun berhasil dibuat dan tersimpan di DB Browser!"
            )
            self.open_login()
        except sqlite3.OperationalError:
            QtWidgets.QMessageBox.critical(
                self, "Error Database", 
                f"Gagal menulis ke database '{DB_LOGIN_PATH}'."
            )

    def open_login(self):
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()


# ==============================================================================
# 2. BAGIAN TKINTER: DASHBOARD LOGISTIK (MENGGUNAKAN DATABASE)
# ==============================================================================

def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    elif jenis == "Cabai": return "7 - 10 °C"
    elif jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_roi(img_path, jenis, roi):
    img = cv2.imread(img_path)
    if img is None: return "Error", "Gagal load gambar", 0

    x, y, w, h = roi
    img_roi = img[y:y+h, x:x+w]
    hsv = cv2.cvtColor(cv2.GaussianBlur(img_roi, (5, 5), 0), cv2.COLOR_BGR2HSV)
    
    mask_orange = cv2.inRange(hsv, np.array([4, 65, 45]), np.array([22, 255, 255]))
    mask_red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    )
    mask_green = cv2.inRange(hsv, np.array([35, 45, 35]), np.array([85, 255, 255]))
    
    total_roi = img_roi.shape[0] * img_roi.shape[1]
    pct_orange = (cv2.countNonZero(mask_orange) / total_roi) * 100
    pct_red = (cv2.countNonZero(mask_red) / total_roi) * 100
    pct_green = (cv2.countNonZero(mask_green) / total_roi) * 100

    if max(pct_orange, pct_red, pct_green) < 5:
        return "Error", "Objek bukan sayuran yang dikenali.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return "Error", f"Salah komoditas! Terdeteksi {warna_dominan}, bukan {jenis}.", -1

    mask_clean = mask_orange if jenis == "Wortel" else (mask_red if jenis == "Cabai" else mask_green)
    if cv2.countNonZero(mask_clean) < 500:
        return "Error", "Objek sayuran tidak terdeteksi jelas.", -1

    damage_pct = (cv2.countNonZero(cv2.bitwise_and(cv2.inRange(hsv, np.array([0,0,0]), np.array([180,255,70])), mask_clean)) / cv2.countNonZero(mask_clean)) * 100
    yellow_pct = (cv2.countNonZero(cv2.bitwise_and(cv2.inRange(hsv, np.array([18,40,40]), np.array([40,255,255])), mask_clean)) / cv2.countNonZero(mask_clean)) * 100
    mean_sat = np.mean(hsv[:,:,1])

    score = 0
    if damage_pct > 10: score += 4
    elif damage_pct > 3: score += 2
    if jenis in ["Brokoli", "Cabai"] and yellow_pct > 15: score += 2
    if mean_sat < 60: score += 2
    elif mean_sat < 90: score += 1

    if score >= 4: status, sisa = "BUSUK / RUSAK", 0
    elif score >= 2: status, sisa = "Kurang Segar", 2
    else: status, sisa = "Segar & Alami", 4

    return jenis, status, sisa


class AppLogistik:
    def __init__(self, root):
        self.root = root
        self.root.title("Optimalisasi Logistik Pertanian")
        self.root.geometry("1120x660")
        self.current_img_path = None
        self.roi = None
        
        self.cap = None 
        self.is_camera_on = False
        self.current_frame = None
        
        self.init_ui()
        self.load_data_from_db()
        self.update_live_camera()
        
    def init_ui(self):
        lbl_header = tk.Label(self.root, text="OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA", font=("Helvetica", 12, "bold"), bg="#1b5e20", fg="white", pady=12)
        lbl_header.pack(fill=tk.X)
        
        container = tk.Frame(self.root, bg="#f4f7f5")
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        frame_kiri = tk.LabelFrame(container, text=" Panel Input Scanner ", font=("Helvetica", 10, "bold"), bg="white", padx=12, pady=12)
        frame_kiri.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.cb_komoditas = ttk.Combobox(frame_kiri, values=["Wortel", "Cabai", "Brokoli"], state="readonly")
        self.cb_komoditas.set("Wortel")
        self.cb_komoditas.pack(fill=tk.X, pady=5)
        
        self.lbl_preview = tk.Label(frame_kiri, text="[ Preview ]", bg="#e0e0e0", height=15)
        self.lbl_preview.pack(fill=tk.BOTH, expand=True)
        
        self.btn_cam = tk.Button(frame_kiri, text="Buka Kamera", command=self.toggle_camera, bg="#1976d2", fg="white")
        self.btn_cam.pack(fill=tk.X, pady=2)
        tk.Button(frame_kiri, text="Pilih Foto dari Galeri", command=self.browse_file, bg="#ff9800", fg="white").pack(fill=tk.X, pady=2)
        tk.Button(frame_kiri, text="Tandai Area Sayur (ROI)", command=self.select_roi, bg="#7b1fa2", fg="white").pack(fill=tk.X, pady=2)
        tk.Button(frame_kiri, text="Jalankan Analisis", command=self.process_image, bg="#2e7d32", fg="white", font=("Helvetica", 10, "bold")).pack(fill=tk.X, pady=8)

        frame_kanan = tk.LabelFrame(container, text=" Dashboard ", font=("Helvetica", 10, "bold"), bg="white")
        frame_kanan.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.lbl_info_scan = tk.Label(
            frame_kanan,
            text="Hasil Pindai Sistem\n====================\nKomoditas : -\nKondisi   : -\nSisa      : -\nSuhu Simpan : -",
            justify=tk.LEFT, bg="#f9f9f9", font=("Consolas", 10)
        )
        self.lbl_info_scan.pack(fill=tk.X, pady=10)
        
        self.tree = ttk.Treeview(frame_kanan, columns=("ID", "Nama", "Kondisi", "Sisa", "Suhu"), show="headings")
        for col in ["ID", "Nama", "Kondisi", "Sisa", "Suhu"]: 
            self.tree.heading(col, text=col)
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Nama", width=150)
        self.tree.column("Kondisi", width=180)
        self.tree.column("Sisa", width=100, anchor="center")
        self.tree.column("Suhu", width=120, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

    def load_data_from_db(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        try:
            conn = sqlite3.connect(DB_ANALISIS_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai")
            rows = cursor.fetchall()
            
            for row in rows:
                self.tree.insert("", tk.END, values=row)
                
            conn.close()
        except sqlite3.OperationalError:
            print("Database logistik_hortikultura.db kosong atau belum terisi.")

    def select_roi(self):
        if not self.current_img_path:
            messagebox.showwarning("Peringatan", "Pilih foto dulu!")
            return
        img = cv2.imread(self.current_img_path)
        r = cv2.selectROI("Tandai Area Sayur", img, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow("Tandai Area Sayur")
        if r[2] > 0 and r[3] > 0:
            self.roi = r
            messagebox.showinfo("Info", "Area berhasil ditandai!")

    def browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp")])
        if path:
            self.current_img_path = path
            self.roi = None
            self.render_preview(path)

    def process_image(self):
        if not self.current_img_path: return
        if not self.roi:
            img = cv2.imread(self.current_img_path)
            self.roi = (0, 0, img.shape[1], img.shape[0])
            
        nama, kondisi, sisa = cek_kondisi_roi(self.current_img_path, self.cb_komoditas.get(), self.roi)
        if sisa == -1:
            messagebox.showerror("Error", kondisi)
            return
            
        suhu = rekomendasi_suhu(nama)
        sisa_hari = f"{sisa} Hari"

        text = f"Hasil Pindai Sistem\n====================\nKomoditas   : {nama}\nKondisi     : {kondisi}\nSisa Segar  : {sisa_hari}\nSuhu Simpan : {suhu}"
        self.lbl_info_scan.configure(text=text)
        
        try:
            conn = sqlite3.connect(DB_ANALISIS_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?, ?, ?, ?)",
                (nama, kondisi, sisa_hari, suhu)
            )
            conn.commit()
            conn.close()
            
            self.load_data_from_db()
            
        except sqlite3.OperationalError as e:
            messagebox.showerror("Database Error", f"Gagal menyimpan data ke DB Browser:\n{e}")

    def toggle_camera(self):
        self.is_camera_on = not self.is_camera_on
        self.btn_cam.configure(text="Capture" if self.is_camera_on else "Buka Kamera")
        if self.is_camera_on:
            if self.cap is None: self.cap = cv2.VideoCapture(0)
        else:
            if self.current_frame is not None:
                self.current_img_path = "temp_capture.jpg"
                cv2.imwrite(self.current_img_path, self.current_frame)
                self.render_preview(self.current_img_path)

    def update_live_camera(self):
        if self.is_camera_on and self.cap is not None:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)).resize((460, 240)))
                self.lbl_preview.configure(image=img_tk, text="")
                self.lbl_preview.image = img_tk
        self.root.after(15, self.update_live_camera)

    def render_preview(self, path):
        try:
            img = Image.open(path).resize((460, 240))
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_preview.configure(image=img_tk, text="")
            self.lbl_preview.image = img_tk
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuka gambar:\n{e}")

    def on_closing(self):
        if self.cap is not None: self.cap.release()
        self.root.destroy()


# ==============================================================================
# 3. ALUR UTAMA EXECUTION
# ==============================================================================
if __name__ == "__main__":
    qt_app = QtWidgets.QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    qt_app.exec_()

    if LOGIN_SUCCESS:
        root = tk.Tk()
        app_dashboard = AppLogistik(root)
        root.protocol("WM_DELETE_WINDOW", app_dashboard.on_closing)
        root.mainloop()
