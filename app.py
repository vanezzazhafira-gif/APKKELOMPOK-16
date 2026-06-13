import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import tempfile
import os

# Konfigurasi dasar page Streamlit wide
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", layout="wide")

DB_LOGIN = "manajemen_akses.db"
DB_ANALISIS = "logistik_hortikultura.db"

# URL Logo Resmi Kelompok 16 sesuai gambar yang diberikan
LOGO_URL = "https://raw.githubusercontent.com/vanezzahafira-gif/APKKELOMPOK-16/main/login.jpeg"

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
# ANALYSIS CORE ENGINE (OPENCV)
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
        return "Error_Komoditas", f"Salah komoditas! Terdeteksi {warna_dominan}, bukan {jenis}.", -1

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
if "riwayat_session" not in st.session_state: 
    st.session_state.riwayat_session = [
        (1, "Cabai", "Segar & Alami", "4 Hari", "7 - 10 °C"),
        (2, "Wortel", "Kurang Segar", "2 Hari", "0 - 4 °C"),
        (3, "Cabai", "Segar & Alami", "4 Hari", "7 - 10 °C")
    ]

# Menyembunyikan komponen header bawaan streamlit agar bersih
st.markdown("<style>header[data-testid='stHeader'] {display:none;}</style>", unsafe_allow_html=True)

# =========================================================
# SYSTEM PAGES
# =========================================================

# --- 1. HALAMAN LOGIN ---
if not st.session_state.login and st.session_state.page == "Login":
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: #f3f3f3 !important;
        }}
        .login-bg-container {{
            position: relative;
            background-color: #ffffff;
            width: 420px;
            height: 620px;
            margin: 20px auto;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .circle-decor-top {{
            position: absolute;
            top: -110px; right: -90px;
            width: 290px; height: 290px;
            background-color: #437c37;
            border-radius: 50%;
            z-index: 1;
        }}
        .circle-decor-bottom {{
            position: absolute;
            bottom: -110px; left: -70px;
            width: 250px; height: 250px;
            background-color: #437c37;
            border-radius: 50%;
            z-index: 1;
        }}
        .login-logo {{
            position: absolute;
            top: 25px; left: 25px;
            width: 110px; height: 110px;
            background-image: url('{LOGO_URL}');
            background-size: cover;
            background-position: center;
            z-index: 2;
        }}
        .login-title-box {{
            text-align: center;
            margin-top: 145px;
            z-index: 2;
            position: relative;
        }}
        .login-title-box h1 {{
            font-size: 38px; font-weight: bold; color: #000000; margin: 0;
        }}
        .login-title-box p {{
            font-size: 13.5px; font-weight: bold; color: #000000; margin-top: 12px; padding: 0 15px;
            line-height: 1.3;
        }}
        .login-form-wrapper {{
            position: relative;
            z-index: 5;
            padding: 5px 45px;
        }}
        .create-account-text {{
            position: absolute;
            bottom: 48px;
            left: 0; right: 0;
            text-align: center;
            font-size: 13.5px;
            color: #000000;
            z-index: 5;
        }}
    </style>
    <div class="login-bg-container">
        <div class="circle-decor-top"></div>
        <div class="circle-decor-bottom"></div>
        <div class="login-logo"></div>
        <div class="login-title-box">
            <h1>Log In</h1>
            <p>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='login-form-wrapper'>", unsafe_allow_html=True)
    email = st.text_input("Username", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    
    st.write("")
    col_btn_in, _ = st.columns([1, 1.5])
    with col_btn_in:
        if st.button("LOG IN", type="secondary", key="btn_execute_login"):
            if login(email, password):
                st.session_state.login = True
                st.rerun()
            else:
                st.error("Username atau Password Salah")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='create-account-text'>Have not account? &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1.65, 1, 1.3])
    with col_l2:
        if st.button("Create Account", key="go_signup"):
            st.session_state.page = "Sign Up"
            st.rerun()

# --- 2. HALAMAN SIGN UP ---
elif not st.session_state.login and st.session_state.page == "Sign Up":
    st.markdown(f"""
    <style>
        .stApp {{ background-color: #f3f3f3 !important; }}
        .signup-bg-container {{
            background-color: #ffffff;
            width: 420px;
            height: 620px;
            margin: 20px auto;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            position: relative;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .signup-title-header {{
            text-align: center;
            padding-top: 35px;
        }}
        .signup-title-header h1 {{
            font-size: 40px; font-weight: bold; color: #000000; margin: 0;
        }}
        .signup-title-header p {{
            font-size: 22px; font-weight: bold; color: #437c37; margin-top: 5px;
        }}
        .signup-form-wrapper {{
            padding: 0px 45px;
            margin-top: -390px;
            position: relative;
            z-index: 10;
        }}
        .signup-bottom-logo {{
            position: absolute;
            bottom: 25px;
            left: 50%;
            transform: translateX(-50%);
            width: 110px;
            height: 110px;
            background-image: url('{LOGO_URL}');
            background-size: cover;
            background-position: center;
        }}
        .already-account-text {{
            position: absolute;
            bottom: 152px;
            left: 0; right: 0;
            text-align: center;
            font-size: 14px;
            color: #000000;
        }}
    </style>
    <div class="signup-bg-container">
        <div class="signup-title-header">
            <h1>Sign Up</h1>
            <p>Create an account</p>
        </div>
        <div class="already-account-text">Already have an account? &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
        <div class="signup-bottom-logo"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='signup-form-wrapper'>", unsafe_allow_html=True)
    new_email = st.text_input("Email", key="su_email")
    new_password = st.text_input("Password", type="password", key="su_pass")
    confirm = st.text_input("Confirm Password", type="password", key="su_confirm")
    
    st.write("")
    col_su_center, _ = st.columns([1, 1])
    with col_su_center:
        if st.button("Sign Up", key="do_signup_action"):
            if new_password == confirm:
                if signup(new_email, new_password):
                    st.success("Akun berhasil dibuat!")
                    st.session_state.page = "Login"
                    st.rerun()
                else: st.error("Email sudah terdaftar.")
            else: st.error("Password tidak cocok.")
    st.markdown("</div>", unsafe_allow_html=True)

    col_s1, col_s2, col_s3 = st.columns([1.75, 0.6, 1.3])
    with col_s2:
        if st.button("Log In", key="back_to_login"):
            st.session_state.page = "Login"
            st.rerun()

# --- 3. DASHBOARD UTAMA ---
else:
    st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; }
        
        /* Green Header Bar */
        .qt-main-header {
            background-color: #1a5e20;
            color: #ffffff;
            font-family: sans-serif;
            font-size: 19px;
            font-weight: bold;
            text-align: center;
            padding: 8px 0px;
            letter-spacing: 0.5px;
            margin-bottom: 15px;
            border: 1px solid #113f15;
        }

        /* Gray Group Box Layout Panels */
        .group-box-panel {
            border: 1px solid #adadad;
            background-color: #fcfcfc;
            padding: 15px;
            min-height: 580px;
        }
        .group-box-title {
            font-family: sans-serif;
            font-size: 13px;
            font-weight: bold;
            color: #000000;
            margin-top: -25px;
            background-color: #ffffff;
            width: fit-content;
            padding: 0px 6px;
            margin-bottom: 15px;
            border-left: 1px solid #adadad;
            border-right: 1px solid #adadad;
        }

        /* Image Preview Placeholder Box */
        .qt-preview-box {
            background-color: #e9e9e9;
            border: 1px solid #b0b0b0;
            height: 250px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333333;
            font-family: sans-serif;
            font-size: 13px;
            margin-bottom: 15px;
        }

        /* Terminal Style Text Blocks */
        .qt-terminal-result {
            background-color: #ffffff;
            border: 1px solid #a0a0a0;
            padding: 15px 30px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 15px;
            font-weight: bold;
            color: #000000;
            white-space: pre;
            line-height: 1.4;
            margin: 0 auto 20px auto;
            width: fit-content;
            text-align: left;
        }

        /* 4 Colored Buttons Core Triggers Styles */
        .stButton>button {
            border-radius: 0px !important;
            font-family: sans-serif !important;
            font-size: 13px !important;
            font-weight: normal !important;
            border: 1px solid #707070 !important;
            color: white !important;
            width: 100% !important;
            height: 34px !important;
            margin-bottom: -5px;
        }
        
        div[data-testid="stHorizontalBlock"] .col-blue-btn .stButton>button { background-color: #1d73e7 !important; }
        div[data-testid="stHorizontalBlock"] .col-orange-btn .stButton>button { background-color: #f39c12 !important; }
        div[data-testid="stHorizontalBlock"] .col-purple-btn .stButton>button { background-color: #8e44ad !important; }
        div[data-testid="stHorizontalBlock"] .col-green-btn .stButton>button { background-color: #27ae60 !important; }
    </style>
    <div class="qt-main-header">OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>
    """, unsafe_allow_html=True)

    col_kiri, col_kanan = st.columns([1, 1.4], gap="medium")

    # -----------------------------------------------------
    # PANEL KIRI: PANEL INPUT SCANNER
    # -----------------------------------------------------
    with col_kiri:
        st.markdown('<div class="group-box-panel"><div class="group-box-title">Panel Input Scanner</div>', unsafe_allow_html=True)
        
        komoditas = st.selectbox("Pilih Komoditas:", ["Wortel", "Cabai", "Brokoli"])
        opsi_input = st.radio("Metode Ambil Gambar:", ["Kamera Laptop / HP", "Unggah Gambar dari File"])
        
        active_file = None
        if opsi_input == "Kamera Laptop / HP":
            active_file = st.camera_input("Ambil foto objek", label_visibility="collapsed")
        else:
            active_file = st.file_uploader("Pilih file foto (.jpg, .png)", type=["jpg", "jpeg", "png"])

        if active_file:
            st.image(active_file, use_container_width=True)
        else:
            st.markdown('<div class="qt-preview-box">[ Preview ]</div>', unsafe_allow_html=True)

        # Baris Tombol Warna Qt Designer
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown('<div class="col-blue-btn">', unsafe_allow_html=True)
            btn_cam = st.button("Buka Kamera")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_b2:
            st.markdown('<div class="col-orange-btn">', unsafe_allow_html=True)
            btn_gal = st.button("Pilih Foto dari Galeri")
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("")
        col_b3, col_b4 = st.columns(2)
        with col_b3:
            st.markdown('<div class="col-purple-btn">', unsafe_allow_html=True)
            btn_roi = st.button("Tandai Area Sayur (ROI)")
            st.markdown('</div>', unsafe_allow_html=True)
        with col_b4:
            st.markdown('<div class="col-green-btn">', unsafe_allow_html=True)
            jalankan_analisis = st.button("Jalankan Analisis")
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------------------------------
    # PANEL KANAN: PANEL DASHBOARD UTAMA
    # -----------------------------------------------------
    with col_kanan:
        st.markdown('<div class="group-box-panel"><div class="group-box-title">Dashboard</div>', unsafe_allow_html=True)
        
        if jalankan_analisis:
            if active_file is None:
                st.warning("Mohon unggah atau ambil gambar terlebih dahulu!")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(active_file.getbuffer())
                    path_img = tmp_file.name
                
                nama_veg, kond_veg, sisa_hari = cek_kondisi_roi(path_img, komoditas)
                
                if nama_veg == "Error_Komoditas":
                    st.error(f"Peringatan: {kond_veg}")
                    st.session_state.hasil = {"komoditas": "-", "kondisi": "-", "sisa": "-", "suhu": "-"}
                elif sisa_hari == -1:
                    st.warning(f"Perhatian: {kond_veg}")
                    st.session_state.hasil = {"komoditas": "-", "kondisi": "-", "sisa": "-", "suhu": "-"}
                else:
                    suhu_rekom = rekomendasi_suhu(nama_veg)
                    string_sisa = f"{sisa_hari} Hari"
                    
                    st.session_state.hasil = {
                        "komoditas": nama_veg,
                        "kondisi": kond_veg,
                        "sisa": string_sisa,
                        "suhu": suhu_rekom
                    }
                    
                    try:
                        conn = sqlite3.connect(DB_ANALISIS)
                        cur = conn.cursor()
                        cur.execute("INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?, ?, ?, ?)", 
                                    (nama_veg, kond_veg, string_sisa, suhu_rekom))
                        conn.commit()
                        conn.close()
                    except:
                        pass
                    
                    new_id = len(st.session_state.riwayat_session) + 1
                    st.session_state.riwayat_session.append((new_id, nama_veg, kond_veg, string_sisa, suhu_rekom))

        # Output Terminal Box
        res = st.session_state.hasil
        text_output = f"""Hasil Pindai Sistem
============================
Komoditas   : {res["komoditas"]}
Kondisi     : {res["kondisi"]}
Sisa        : {res["sisa"]}
Suhu Simpan : {res["suhu"]}"""
        
        st.markdown(f'<div class="qt-terminal-result">{text_output}</div>', unsafe_allow_html=True)
        
        # Tabel Riwayat Logistik
        st.dataframe(
            st.session_state.riwayat_session,
            use_container_width=True,
            hide_index=True,
            column_config={0: "ID", 1: "Nama", 2: "Kondisi", 3: "Sisa", 4: "Suhu"}
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
