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

# URL Logo Resmi Kelompok 16
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
    st.session_state.riwayat_session = []

# Sembunyikan elemen header default Streamlit
st.markdown("<style>header[data-testid='stHeader'] {display:none;}</style>", unsafe_allow_html=True)

# =========================================================
# SYSTEM PAGES
# =========================================================

# --- 1. HALAMAN LOGIN ---
if not st.session_state.login and st.session_state.page == "Login":
    st.markdown(f"""
    <style>
        .stApp {{ background-color: #f3f3f3 !important; }}
        .login-bg-container {{
            position: relative;
            background-color: #ffffff;
            width: 420px;
            height: 560px;
            margin: 40px auto;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
            font-family: sans-serif;
            padding: 30px;
            box-sizing: border-box;
        }}
        .header-box-custom {{
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            position: relative;
        }}
        .logo-img-custom {{
            width: 85px;
            height: 85px;
            border-radius: 50%;
            object-fit: cover;
            border: 1px solid #ddd;
            margin-right: 15px;
        }}
        .title-text-custom {{
            font-size: 28px;
            font-weight: bold;
            color: #000000;
            margin: 0;
        }}
        .subtitle-text-custom {{
            font-size: 13.5px;
            font-weight: bold;
            color: #000000;
            margin-top: 15px;
            margin-bottom: 25px;
            line-height: 1.4;
        }}
        .footer-login-custom {{
            margin-top: 30px;
            font-size: 13.5px;
            color: #000000;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        /* Menghilangkan margin bawaan widget streamlit di dalam box */
        div[data-testid="stVerticalBlock"] > div {{
            margin-bottom: 0px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    # Membuka pembungkus form kotak putih tunggal
    st.markdown('<div class="login-bg-container">', unsafe_allow_html=True)
    
    # Elemen Header Atas (Logo + Tulisan Log In)
    st.markdown(f"""
    <div class="header-box-custom">
        <img class="logo-img-custom" src="{LOGO_URL}">
        <span class="title-text-custom">Log In</span>
    </div>
    <div class="subtitle-text-custom">Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</div>
    """, unsafe_allow_html=True)
    
    # Elemen Form Isian
    email = st.text_input("Username", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    
    st.write("")
    
    # Tombol LOG IN Utama
    if st.button("LOG IN", use_container_width=True, type="primary", key="btn_execute_login"):
        if login(email, password):
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Username atau Password Salah")
            
    st.write("---")
    
    # Bagian Footer Bawah untuk Navigasi Buat Akun (Tetap di dalam Kotak)
    st.markdown('<div class="footer-login-custom"><span>Have not account?</span>', unsafe_allow_html=True)
    if st.button("Create Account", key="go_signup"):
        st.session_state.page = "Sign Up"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Menutup pembungkus form kotak putih tunggal
    st.markdown('</div>', unsafe_allow_html=True)

# --- 2. HALAMAN SIGN UP ---
elif not st.session_state.login and st.session_state.page == "Sign Up":
    st.markdown(f"""
    <style>
        .stApp {{ background-color: #f3f3f3 !important; }}
        .signup-bg-container {{
            background-color: #ffffff;
            width: 420px;
            height: 590px;
            margin: 30px auto;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
            font-family: sans-serif;
            padding: 30px;
            box-sizing: border-box;
            position: relative;
        }}
        .signup-header {{
            margin-bottom: 20px;
        }}
        .signup-title {{
            font-size: 34px;
            font-weight: bold;
            color: #000000;
            margin: 0;
        }}
        .signup-subtitle {{
            font-size: 20px;
            font-weight: bold;
            color: #437c37;
            margin-top: 5px;
            margin-bottom: 20px;
        }}
        .logo-bottom-container {{
            display: flex;
            justify-content: center;
            margin-top: 25px;
        }}
        .logo-bottom-img {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: cover;
            border: 1px solid #ddd;
        }}
        .footer-signup-custom {{
            margin-top: 20px;
            font-size: 13.5px;
            color: #000000;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="signup-bg-container">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="signup-header">
        <div class="signup-title">Sign Up</div>
        <div class="signup-subtitle">Create an account</div>
    </div>
    """, unsafe_allow_html=True)
    
    new_email = st.text_input("Email", key="su_email")
    new_password = st.text_input("Password", type="password", key="su_pass")
    confirm = st.text_input("Confirm Password", type="password", key="su_confirm")
    
    st.write("")
    if st.button("Sign Up", use_container_width=True, type="primary", key="do_signup_action"):
        if new_password == confirm:
            if signup(new_email, new_password):
                st.success("Akun berhasil dibuat!")
                st.session_state.page = "Login"
                st.rerun()
            else: st.error("Email sudah terdaftar.")
        else: st.error("Password tidak cocok.")
        
    st.markdown('<div class="footer-signup-custom"><span>Already have an account?</span>', unsafe_allow_html=True)
    if st.button("Log In", key="back_to_login"):
        st.session_state.page = "Login"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Logo kelompok di bagian bawah dalam box sign up
    st.markdown(f'<div class="logo-bottom-container"><img class="logo-bottom-img" src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. DASHBOARD UTAMA ---
else:
    st.markdown("""
    <style>
        .stApp { background-color: #ffffff !important; }
        
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

    # PANEL KIRI: PANEL INPUT SCANNER
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

    # PANEL KANAN: PANEL DASHBOARD UTAMA
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
