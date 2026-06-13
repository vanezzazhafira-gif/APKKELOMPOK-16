import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
import base64

# Mengatur layout menjadi wide dan membersihkan tema bawaan
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", layout="wide")

DB_LOGIN = "manajemen_akses.db"
DB_ANALISIS = "logistik_hortikultura.db"

# =========================================================
# DATABASE INITIALIZATION
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_LOGIN)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS data_pengguna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

    conn = sqlite3.connect(DB_ANALISIS)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS riwayat_pindai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            komoditas TEXT,
            kondisi TEXT,
            sisa_segar TEXT,
            suhu_simpan TEXT
        )
    """)
    conn.commit()
    conn.close()

def login(email, password):
    conn = sqlite3.connect(DB_LOGIN)
    cur = conn.cursor()
    cur.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (email, password))
    user = cur.fetchone()
    conn.close()
    return user

def signup(email, password):
    conn = sqlite3.connect(DB_LOGIN)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO data_pengguna(email,password) VALUES (?,?)", (email, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

init_db()

# =========================================================
# IMAGE TO BASE64 HELPER
# =========================================================
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

login_bg = file_to_base64("login.jpeg")
signup_bg = file_to_base64("signup.jpg")
logo_img = file_to_base64("logo.png")

# =========================================================
# OPENCV CORE ANALYSIS
# =========================================================
def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    if jenis == "Cabai": return "7 - 10 °C"
    if jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_roi(path_gambar, jenis):
    img = cv2.imread(path_gambar)
    if img is None:
        return "Error", "Gagal load gambar", -1

    h_orig, w_orig, _ = img.shape
    img_roi = img[0:h_orig, 0:w_orig]
    hsv = cv2.cvtColor(cv2.GaussianBlur(img_roi, (5, 5), 0), cv2.COLOR_BGR2HSV)

    mask_orange = cv2.inRange(hsv, np.array([4, 65, 45]), np.array([22, 255, 255]))
    mask_red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    )
    mask_green = cv2.inRange(hsv, np.array([35, 45, 35]), np.array([85, 255, 255]))

    total_roi = img_roi.shape[0] * img_roi.shape[1]
    pct_orange = cv2.countNonZero(mask_orange) / total_roi * 100
    pct_red = cv2.countNonZero(mask_red) / total_roi * 100
    pct_green = cv2.countNonZero(mask_green) / total_roi * 100

    if max(pct_orange, pct_red, pct_green) < 5:
        return "Error", "Objek bukan sayuran yang dikenali.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return "Error", f"Salah komoditas! Terdeteksi {warna_dominan}, bukan {jenis}.", -1

    mask_clean = mask_orange if jenis == "Wortel" else mask_red if jenis == "Cabai" else mask_green
    if cv2.countNonZero(mask_clean) < 500:
        return "Error", "Objek sayuran tidak terdeteksi jelas.", -1

    damage_pct = (cv2.countNonZero(cv2.bitwise_and(cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 70])), mask_clean)) / max(cv2.countNonZero(mask_clean), 1)) * 100
    yellow_pct = (cv2.countNonZero(cv2.bitwise_and(cv2.inRange(hsv, np.array([18, 40, 40]), np.array([40, 255, 255])), mask_clean)) / max(cv2.countNonZero(mask_clean), 1)) * 100

    mean_sat = np.mean(hsv[:, :, 1])
    score = 0
    if damage_pct > 10: score += 4
    elif damage_pct > 3: score += 2
    if jenis in ["Brokoli", "Cabai"] and yellow_pct > 15: score += 2
    if mean_sat < 60: score += 2
    elif mean_sat < 90: score += 1

    if score >= 4: return jenis, "BUSUK / RUSAK", 0
    if score >= 2: return jenis, "Kurang Segar", 2
    return jenis, "Segar & Alami", 4

# =========================================================
# STATE MANAGEMENT
# =========================================================
if "login" not in st.session_state: st.session_state.login = False
if "page" not in st.session_state: st.session_state.page = "Login"
if "hasil" not in st.session_state:
    st.session_state.hasil = {"komoditas": "-", "kondisi": "-", "sisa": "-", "suhu": "-"}
if "riwayat_session" not in st.session_state: st.session_state.riwayat_session = []

# Menampung mode input aktif ("kamera" atau "galeri")
if "input_mode" not in st.session_state: st.session_state.input_mode = None

# =========================================================
# PERFECT STYLE INJECTION (SANGAT PERSIS DESIGN QT)
# =========================================================
st.markdown("""
<style>
/* Hilangkan paksa navigasi bawaan streamlit */
section[data-testid="stSidebar"] {display:none;}
header[data-testid="stHeader"] {display:none;}
footer {visibility: hidden;}

/* Background dasar aplikasi putih abu bersih ala windows desktop */
.stApp {
    background-color: #f0f0f0;
}

.block-container {
    padding: 10px 20px;
}

/* CONTAINER UTAMA WINDOWS */
.main-window {
    background-color: #ffffff;
    border: 1px solid #707070;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #000000;
    min-height: 680px;
}

/* GREEN HEADER TOP BAR */
.title-bar {
    background-color: #1c6b2a;
    color: #ffffff;
    padding: 10px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* LAYOUT DUA KOLOM */
.window-body {
    display: flex;
    padding: 15px;
    gap: 15px;
}

/* GROUP BOX STYLE (SANGAT PENTING UTK QT DESIGNER LOOK) */
.group-box {
    border: 1px solid #b0b0b0;
    border-radius: 4px;
    padding: 20px 12px 12px 12px;
    position: relative;
    background-color: #ffffff;
}

.group-box-title {
    position: absolute;
    top: -10px;
    left: 12px;
    background-color: #ffffff;
    padding: 0 6px;
    font-size: 13px;
    font-weight: 600;
    color: #000000;
}

.left-panel { width: 340px; }
.right-panel { flex: 1; display: flex; flex-direction: column; gap: 15px; }

/* PANEL PREVIEW GAMBAR ASLI */
.preview-container {
    width: 100%;
    height: 250px;
    border: 1px solid #a0a0a0;
    background-color: #dcdcdc;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    color: #404040;
    margin-top: 10px;
    margin-bottom: 12px;
}

.preview-container img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

/* TOMBOL WARNA WARNI EDITAN QT DESIGNER */
.stButton > button {
    width: 100%;
    height: 34px;
    border-radius: 0px !important;
    font-size: 13px;
    font-weight: bold;
    border: 1px solid #555555;
    transition: none;
    margin-bottom: 6px;
}

.btn-blue > div > button { background-color: #1d73e7 !important; color: white !important; }
.btn-orange > div > button { background-color: #f39c12 !important; color: white !important; }
.btn-purple > div > button { background-color: #8e44ad !important; color: white !important; }
.btn-green > div > button { background-color: #27ae60 !important; color: white !important; }

/* KOTAK HASIL DATA PINDAI */
.result-box {
    font-family: 'Courier New', Courier, monospace;
    font-size: 15px;
    line-height: 1.5;
    white-space: pre;
    color: #000000;
}

/* INPUT SELECTBOX CUSTOM */
div[data-testid="stSelectbox"] > div {
    border-radius: 0px !important;
    border: 1px solid #a0a0a0;
}

/* TRICK: MENYEMBUNYIKAN INPUTAN MODUL ASLI STREAMLIT SECARA TOTAL */
.hidden-uploader { display: none; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# HALAMAN LOGIN & SIGNUP (TETAP TERINTEGRASI)
# =========================================================
if not st.session_state.login and st.session_state.page == "Login":
    bg = f"data:image/jpeg;base64,{login_bg}" if login_bg else ""
    st.markdown(f'<style>.block-container{{max-width:500px; margin:50px auto; background-image:url("{bg}");}}</style>', unsafe_allow_html=True)
    st.subheader("Log In")
    email = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("LOG IN"):
        if login(email, password): st.session_state.login = True; st.rerun()
        else: st.error("Username atau Password Salah")
    if st.button("Create Account"): st.session_state.page = "Sign Up"; st.rerun()

elif not st.session_state.login and st.session_state.page == "Sign Up":
    st.subheader("Sign Up")
    new_email = st.text_input("Email")
    new_password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")
    if st.button("Sign Up"):
        if new_password == confirm and signup(new_email, new_password): st.success("Sukses!"); st.session_state.page = "Login"; st.rerun()
        else: st.error("Gagal atau password tidak cocok")

# =========================================================
# HALAMAN DASHBOARD UTAMA (RE-DESIGN TOTAL)
# =========================================================
else:
    # --- PROSES INPUT KAMERA DAN GALERI TERSEMBUNYI ---
    # Komponen ini tidak terlihat di layar, tapi bekerja di latar belakang sistem HP Android
    with st.sidebar:
        st.markdown('<div class="hidden-uploader">', unsafe_allow_html=True)
        native_cam = st.camera_input("Sistem_Kamera", key="hidden_cam")
        native_file = st.file_uploader("Sistem_Galeri", type=["jpg","jpeg","png"], key="hidden_file")
        st.markdown('</div>', unsafe_allow_html=True)

    # Menentukan file gambar mana yang ditangkap sistem
    active_file = None
    if st.session_state.input_mode == "kamera" and native_cam is not None:
        active_file = native_cam
    elif st.session_state.input_mode == "galeri" and native_file is not None:
        active_file = native_file

    # --- HTML RENDER SELESAI & RAPI ---
    st.markdown('<div class="main-window">', unsafe_allow_html=True)
    st.markdown('<div class="title-bar">OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>', unsafe_allow_html=True)
    st.markdown('<div class="window-body">', unsafe_allow_html=True)

    # -----------------------------------------------------
    # 1. KOLOM KIRI: PANEL INPUT SCANNER
    # -----------------------------------------------------
    st.columns_left = st.container()
    with st.columns_left:
        st.markdown('<div class="group-box left-panel"><span class="group-box-title">Panel Input Scanner</span>', unsafe_allow_html=True)
        
        # Dropdown Komoditas
        komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"], label_visibility="collapsed")
        
        # Logika Render Gambar Preview Kontainer
        if active_file:
            img_open = Image.open(active_file)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_prev:
                img_open.convert("RGB").save(tmp_prev.name)
            base64_data = file_to_base64(tmp_prev.name)
            st.markdown(f'<div class="preview-container"><img src="data:image/jpeg;base64,{base64_data}"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="preview-container">[ Preview ]</div>', unsafe_allow_html=True)

        # Tombol Aksi Kustom Berwarna
        st.markdown('<div class="btn-blue">', unsafe_allow_html=True)
        if st.button("Buka Kamera"):
            st.session_state.input_mode = "kamera"
            st.info("📸 Kamera Sistem Siap. Silakan klik icon kamera bawaan browser/HP di menu samping.")
        st.markdown('</div><div class="btn-orange">', unsafe_allow_html=True)
        if st.button("Pilih Foto dari Galeri"):
            st.session_state.input_mode = "galeri"
            st.info("📁 Galeri Sistem Siap. Silakan pilih berkas foto dari menu unggah samping.")
        st.markdown('</div><div class="btn-purple">', unsafe_allow_html=True)
        st.button("Tandai Area Sayur (ROI)")
        
        st.markdown('</div><div class="btn-green">', unsafe_allow_html=True)
        jalankan_analisis = st.button("Jalankan Analisis")
        st.markdown('</div></div>', unsafe_allow_html=True)

    # -----------------------------------------------------
    # 2. KOLOM KANAN: PANEL DASHBOARD & TABEL
    # -----------------------------------------------------
    st.columns_right = st.container()
    with st.columns_right:
        st.markdown('<div class="right-panel">', unsafe_allow_html=True)
        
        # Sub-Box Atas: Hasil Pindai
        st.markdown('<div class="group-box"><span class="group-box-title">Dashboard</span>', unsafe_allow_html=True)
        
        # Eksekusi Logika Analisis Gambar
        if jalankan_analisis and active_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_analisis:
                tmp_analisis.write(active_file.getbuffer())
                path_img = tmp_analisis.name
            
            nama_veg, kond_veg, sisa_hari = cek_kondisi_roi(path_img, komoditas)
            if sisa_hari != -1:
                suhu_rekom = rekomendasi_suhu(nama_veg)
                st.session_state.hasil = {
                    "komoditas": nama_veg,
                    "kondisi": kond_veg,
                    "sisa": f"{sisa_hari} Hari",
                    "suhu": suhu_rekom
                }
                # Simpan ke SQLite
                conn = sqlite3.connect(DB_ANALISIS)
                cur = conn.cursor()
                cur.execute("INSERT INTO riwayat_pindai (komoditas,kondisi,sisa_segar,suhu_simpan) VALUES (?,?,?,?)", (nama_veg, kond_veg, f"{sisa_hari} Hari", suhu_rekom))
                conn.commit()
                conn.close()
                
                # Update visual table row
                new_id = len(st.session_state.riwayat_session) + 1
                st.session_state.riwayat_session.append((new_id, nama_veg, kond_veg, f"{sisa_hari} Hari", suhu_rekom))

        # Render Text Hasil Pindai Sistem
        res = st.session_state.hasil
        st.markdown(f"""
<div class="result-box">Hasil Pindai Sistem
==============================
Komoditas      : {res["komoditas"]}
Kondisi        : {res["kondisi"]}
Sisa Masa      : {res["sisa"]}
Suhu Simpan    : {res["suhu"]}</div>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Sub-Box Bawah: Tabel Riwayat Logistik
        st.markdown('<div class="group-box" style="flex:1;"><span class="group-box-title">Riwayat Logistik</span>', unsafe_allow_html=True)
        st.dataframe(
            st.session_state.riwayat_session,
            use_container_width=True,
            hide_index=True,
            column_config={0: "ID", 1: "Nama", 2: "Kondisi", 3: "Sisa", 4: "Suhu"}
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Tutup Tag Selesai Konstruksi Utama HTML
    st.markdown('</div></div></div>', unsafe_allow_html=True)
