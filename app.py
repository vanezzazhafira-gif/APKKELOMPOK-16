import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image

# ==============================================================================
# 1. INISIALISASI DATABASE & LOGIKA SISTEM (TETAP SAMA / TIDAK DIUBAH)
# ==============================================================================
DB_LOGIN_PATH = "manajemen_akses.db"
DB_ANALISIS_PATH = "logistik_hortikultura.db"

def init_databases():
    conn = sqlite3.connect(DB_LOGIN_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_pengguna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

    conn = sqlite3.connect(DB_ANALISIS_PATH)
    cursor = conn.cursor()
    cursor.execute("""
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

init_databases()

def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    elif jenis == "Cabai": return "7 - 10 °C"
    elif jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_citra(cv_img, jenis):
    cv_img = cv2.resize(cv_img, (400, 300))
    hsv = cv2.cvtColor(cv2.GaussianBlur(cv_img, (5, 5), 0), cv2.COLOR_BGR2HSV)
    
    mask_orange = cv2.inRange(hsv, np.array([4, 65, 45]), np.array([22, 255, 255]))
    mask_red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    )
    mask_green = cv2.inRange(hsv, np.array([35, 45, 35]), np.array([85, 255, 255]))
    
    total_piksel = cv_img.shape[0] * cv_img.shape[1]
    pct_orange = (cv2.countNonZero(mask_orange) / total_piksel) * 100
    pct_red = (cv2.countNonZero(mask_red) / total_piksel) * 100
    pct_green = (cv2.countNonZero(mask_green) / total_piksel) * 100

    if max(pct_orange, pct_red, pct_green) < 3:
        return None, "Objek sayuran tidak terdeteksi dengan jelas di area preview.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return None, f"Salah komoditas! Kamera mendeteksi {warna_dominan}, mohon sesuaikan pilihan.", -1

    mask_clean = mask_orange if jenis == "Wortel" else (mask_red if jenis == "Cabai" else mask_green)
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

# ==============================================================================
# 2. KONFIGURASI HALAMAN & CUSTOM CSS STRUKTURAL
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", layout="wide")

if "halaman" not in st.session_state:
    st.session_state.halaman = "login"
if "foto_input" not in st.session_state:
    st.session_state.foto_input = None

# CSS untuk memaksa layout berbentuk kotak jendela (window box) di tengah halaman browser
st.markdown("""
<style>
    /* Mengubah background utama browser menjadi abu-abu netral */
    .stApp {
        background-color: #f3f4f6 !important;
    }
    
    /* Menyembunyikan header bawaan streamlit */
    header { visibility: hidden; }
    
    /* Container Box Tengah menyerupai Form Aplikasi Desktop */
    .window-container-box {
        background-color: #ffffff !important;
        padding: 40px 35px;
        border-radius: 16px;
        box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.1);
        max-width: 440px;
        margin: 50px auto;
        position: relative;
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }

    /* Lingkaran Hijau Atas */
    .window-container-box::before {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        background-color: #487e47;
        border-radius: 50%;
        top: -90px;
        right: -70px;
        z-index: 0;
    }

    /* Lingkaran Hijau Bawah */
    .window-container-box::after {
        content: "";
        position: absolute;
        width: 220px;
        height: 220px;
        background-color: #487e47;
        border-radius: 50%;
        bottom: -90px;
        left: -70px;
        z-index: 0;
    }

    /* Lapisan Konten agar berada di atas ornamen lingkaran */
    .inner-content {
        position: relative;
        z-index: 2;
    }
    
    /* Tombol Streamlit disesuaikan */
    div.stButton > button {
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. HALAMAN INTERFACE: LOG IN
# ==============================================================================
if st.session_state.halaman == "login":
    # Membuka pembungkus kotak terpadu
    st.markdown('<div class="window-container-box"><div class="inner-content">', unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #111111; margin-bottom: 5px; font-weight: 800; font-family: sans-serif;'>Log In</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #4b5563; font-size: 13px; font-weight: 500; margin-bottom: 30px; font-family: sans-serif;'>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</p>", unsafe_allow_html=True)
    
    in_user = st.text_input("Username", placeholder="Masukkan username anda", key="log_user")
    in_pass = st.text_input("Password", placeholder="Masukkan password anda", type="password", key="log_pass")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("LOG IN", use_container_width=True):
        conn = sqlite3.connect(DB_LOGIN_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (in_user, in_pass))
        user_found = cursor.fetchone()
        conn.close()
        
        if user_found:
            st.session_state.halaman = "dashboard"
            st.rerun()
        else:
            st.error("Username atau Password salah!")
            
    st.markdown("<div style='margin-top: 25px; border-top: 1px solid #e5e7eb; padding-top: 15px;'></div>", unsafe_allow_html=True)
    
    col_t1, col_b1 = st.columns([1.3, 1])
    with col_t1:
        st.markdown("<p style='margin-top: 6px; font-size: 14px; color: #374151;'>Have not account?</p>", unsafe_allow_html=True)
    with col_b1:
        if st.button("Create Account", use_container_width=True, key="btn_to_signup"):
            st.session_state.halaman = "signup"
            st.rerun()
            
    # Menutup pembungkus kotak terpadu
    st.markdown('</div></div>', unsafe_allow_html=True)

# ==============================================================================
# 4. HALAMAN INTERFACE: SIGN UP
# ==============================================================================
elif st.session_state.halaman == "signup":
    st.markdown('<div class="window-container-box"><div class="inner-content">', unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; color: #111111; margin-bottom: 5px; font-weight: 800; font-family: sans-serif;'>Sign Up</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #487e47; font-size: 15px; font-weight: bold; margin-bottom: 25px; font-family: sans-serif;'>Create an account</p>", unsafe_allow_html=True)
    
    reg_email = st.text_input("Email", placeholder="Masukkan email baru", key="reg_e")
    reg_pass1 = st.text_input("Password", placeholder="Buat kata sandi", type="password", key="reg_p1")
    reg_pass2 = st.text_input("Confirm Password", placeholder="Ulangi kata sandi", type="password", key="reg_p2")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Up", use_container_width=True):
        if reg_pass1 != reg_pass2:
            st.error("Konfirmasi password tidak cocok!")
        elif reg_email == "" or reg_pass1 == "":
            st.warning("Form registrasi tidak boleh kosong!")
        else:
            try:
                conn = sqlite3.connect(DB_LOGIN_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO data_pengguna(email, password) VALUES (?,?)", (reg_email, reg_pass1))
                conn.commit()
                conn.close()
                st.success("Registrasi Sukses! Silakan Login.")
                st.session_state
