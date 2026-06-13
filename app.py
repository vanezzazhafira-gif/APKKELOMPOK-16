import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# ==============================================================================
# CONFIG DATABASE
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

# ==============================================================================
# CUSTOM DESAIN STYLE (CSS) - Memaksa Tampilan Mirip Desain Aslimu
# ==============================================================================
st.set_page_config(page_title="Logistik Hortikultura", page_icon="🌱", layout="wide")

st.markdown("""
    <style>
    /* Menghilangkan header default streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Membuat background halaman abu-abu terang */
    .stApp {
        background-color: #f3f3f3 !important;
    }
    
    /* Wadah Utama Login (Kotak Vertikal Tengah) */
    .login-container {
        max-width: 480px;
        margin: 40px auto;
        padding: 40px 30px;
        background-color: white;
        border-radius: 8px;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    
    /* Styling Teks Judul Hijau Pertanian */
    .app-title {
        color: #2e7d32;
        font-family: sans-serif;
        font-size: 22px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 30px;
    }
    
    /* Memaksa input text agar melengkung dan rapi */
    div.stTextInput > div > div > input {
        border-radius: 4px !important;
        border: 1px solid #c0c0c0 !important;
        height: 50px !important;
        font-size: 15px !important;
    }
    
    /* Mengatur style tombol login biru */
    .stButton > button {
        width: 100% !important;
        height: 50px !important;
        background-color: #1976d2 !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 15px !important;
        border-radius: 4px !important;
        border: none !important;
        margin-top: 10px;
    }
    
    /* Style khusus tombol daftar */
    .signup-box button {
        background-color: #437c37 !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==============================================================================
# LOGIKA LOGISTIK (OPENCV)
# ==============================================================================
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
        return None, "Objek sayuran tidak terdeteksi jelas.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return None, f"Salah komoditas! Terdeteksi {warna_dominan}, bukan {jenis}.", -1

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
# ALUR HALAMAN (SESSION STATE)
# ==============================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page_status" not in st.session_state:
    st.session_state.page_status = "login"  # login atau signup

# --- 1. TAMPILAN PAGE LOGIN ---
if not st.session_state.logged_in and st.session_state.page_status == "login":
    # Membuat grid tengah agar posisi pas di center monitor
    _, col_center, _ = st.columns([1, 1.2, 1])
    
    with col_center:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Tampilkan logo kelompok bulat di atas tengah container
        if os.path.exists("logoo.jpg"):
            st.image("logoo.jpg", width=110)
            
        st.markdown('<div class="app-title">Aplikasi Hortikultura</div>', unsafe_allow_html=True)
        
        login_email = st.text_input("Username", placeholder="Masukkan Username/Email", label_visibility="collapsed")
        st.write("")
        login_pass = st.text_input("Password", type="password", placeholder="Masukkan Password", label_visibility="collapsed")
        
        if st.button("LOG IN"):
            if login_email == "" or login_pass == "":
                st.warning("Data tidak boleh kosong!")
            else:
                conn = sqlite3.connect(DB_LOGIN_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (login_email, login_pass))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.success("Login Berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau Password Salah!")
                    
        st.write("---")
        st.write("Have not account?")
        if st.button("Create Account", key="go_signup"):
            st.session_state.page_status = "signup"
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

# --- 2. TAMPILAN PAGE SIGN UP ---
elif not st.session_state.logged_in and st.session_state.page_status == "signup":
    _, col_center, _ = st.columns([1, 1.2, 1])
    
    with col_center:
        st.markdown('<div class="login-container signup-box">', unsafe_allow_html=True)
        
        if os.path.exists("logoo.jpg"):
            st.image("logoo.jpg", width=110)
            
        st.markdown('<div class="app-title" style="color:#437c37;">Create Account</div>', unsafe_allow_html=True)
        
        reg_email = st.text_input("Email", placeholder="Email", label_visibility="collapsed")
        st.write("")
        reg_pass = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        st.write("")
        reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm Password", label_visibility="collapsed")
        
        if st.button("Sign Up"):
            if reg_email == "" or reg_pass == "":
                st.warning("Semua data harus diisi!")
            elif reg_pass != reg_confirm:
                st.error("Password tidak sama!")
            else:
                try:
                    conn = sqlite3.connect(DB_LOGIN_PATH)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO data_pengguna (email, password) VALUES (?, ?)", (reg_email, reg_pass))
                    conn.commit()
                    conn.close()
                    st.success("Akun berhasil dibuat!")
                    st.session_state.page_status = "login"
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Email sudah digunakan!")
                    
        st.write("---")
        st.write("Already have an account?")
        if st.button("Log In", key="go_login"):
            st.session_state.page_status = "login"
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

# --- 3. TAMPILAN PAGE DASHBOARD UTAMA (SETELAH LOGIN BERHASIL) ---
else:
    st.markdown("<div style='background-color:#1b5e20;padding:12px;border-radius:5px'><h2 style='color:white;text-align:center;margin:0;'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</h2></div>", unsafe_allow_html=True)
    
    col_user, col_logout = st.columns([8, 2])
    col_user.write("Sesi Aktif: **Dashboard Logistik**")
    if col_logout.button("Log Out", key="logout_act"):
        st.session_state.logged_in = False
        st.session_state.page_status = "login"
        st.rerun()

    st.write("---")
    col_kiri, col_kanan = st.columns([1, 1])
    
    with col_kiri:
        st.subheader("📸 Panel Input Scanner")
        komoditas_pilihan = st.selectbox("Pilih Komoditas", ["Wortel", "Cabai", "Brokoli"])
        
        metode_input = st.radio("Metode Pengambilan Gambar:", ["Gunakan Kamera Perangkat", "Unggah Foto dari Galeri"])
        
        file_gambar = None
        if metode_input == "Gunakan Kamera Perangkat":
            file_gambar = st.camera_input("Ambil Foto Komoditas")
        else:
            file_gambar = st.file_uploader("Pilih File Gambar", type=["jpg", "jpeg", "png", "bmp"])
            
        if file_gambar is not None:
            image_pil = Image.open(file_gambar)
            img_np = np.array(image_pil)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            if st.button("Jalankan Analisis", key="run_analisis"):
                nama, kondisi, sisa = cek_kondisi_citra(img_cv, komoditas_pilihan)
                if sisa == -1:
                    st.error(kondisi)
                else:
                    suhu_rekomendasi = rekomendasi_suhu(nama)
                    sisa_hari = f"{sisa} Hari"
                    
                    conn = sqlite3.connect(DB_ANALISIS_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?, ?, ?, ?)",
                        (nama, kondisi, sisa_hari, suhu_rekomendasi)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Analisis Berhasil direkam!")

    with col_kanan:
        st.subheader("📊 Dashboard")
        
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_rows = cursor.fetchall()
        conn.close()
        
        if data_rows:
            terbaru = data_rows[0]
            st.info(f"""
            **Hasil Pindai Sistem:**
            * Komoditas : {terbaru[1]}
            * Kondisi : {terbaru[2]}
            * Sisa : {terbaru[3]}
            * Suhu Simpan : {terbaru[4]}
            """)
        
        import pandas as pd
        if data_rows:
            df = pd.DataFrame(data_rows, columns=["ID", "Nama", "Kondisi", "Sisa", "Suhu"])
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.warning("Belum ada data pemindaian.")
