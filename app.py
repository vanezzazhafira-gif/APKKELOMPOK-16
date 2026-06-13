import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# Database Path
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
        return None, "Objek sayuran tidak terdeteksi dengan jelas.", -1

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
# CSS CORE REPLICA ENGINE (MENIRU LAYOUT TKINTER WINDOWS)
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", page_icon="🌱", layout="wide")

st.markdown("""
<style>
/* Sembunyikan Header/Footer Default Streamlit */
header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] { visibility: hidden !important; height: 0px !important; }

/* Background Dasar Desktop Windows (Abu-abu Terang) */
.stApp { background-color: #f0f0f0 !important; }

/* ================== STYLE KOTAK AUTH (LOGIN / SIGNUP) ================== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="auth_card_trigger"]) {
    background-color: white !important;
    border: 1px solid #bcbcbc !important;
    border-radius: 8px !important;
    padding: 30px !important;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.1) !important;
    max-width: 420px !important;
    margin: 60px auto !important;
}

/* Mengubah Tombol Login/Signup Menjadi Style Standar Khas Desktop */
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="auth_card_trigger"]) button {
    background-color: #e1e1e1 !important;
    color: black !important;
    border: 1px solid #acacac !important;
    border-radius: 3px !important;
    font-weight: bold !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="auth_card_trigger"]) button:hover {
    background-color: #e5f1fb !important;
    border-color: #0078d7 !important;
}

/* Navigasi Teks Bawah Khas Sketsa */
.nav-text-container { text-align: right !important; margin-top: 15px; }
.nav-text-container button { background: none !important; border: none !important; color: #0066cc !important; text-decoration: underline !important; font-size: 14px !important; padding: 0 !important;}

/* ================== STYLE DASHBOARD UTAMA ================== */
.app-header-green {
    background-color: #246329 !important;
    border: 1px solid #18441c;
    padding: 12px !important;
    text-align: center !important;
    color: white !important;
    font-size: 20px !important;
    font-weight: bold !important;
    margin-bottom: 20px;
    letter-spacing: 0.5px;
}

/* Group Box Frame Seperti Sketsa */
.group-box {
    background-color: #ffffff !important;
    border: 1px solid #b8b8b8 !important;
    border-radius: 4px !important;
    padding: 25px 18px 18px 18px !important;
    position: relative;
    min-height: 580px;
}
.group-box-title {
    position: absolute;
    top: -12px;
    left: 12px;
    background-color: #f0f0f0;
    padding: 0 6px;
    font-weight: bold !important;
    font-size: 14px !important;
    color: black !important;
}

/* Frame Hasil Pindai Monospace */
.result-display-frame {
    text-align: left !important;
    font-family: monospace !important;
    font-size: 15px !important;
    color: black !important;
    line-height: 1.6;
    background-color: #fdfdfd;
    border: 1px dashed #b5b5b5;
    padding: 12px;
    margin-bottom: 20px;
}

/* Pengatur Warna Tombol Aksi di Dashboard */
.btn-style button { background-color: #e1e1e1 !important; color: black !important; border-radius: 2px !important; border: 1px solid #acacac !important; margin-bottom: -5px; text-align: center !important; }
.btn-style button:hover { background-color: #cfcfcf !important; }
.btn-green-submit button { background-color: #2c7d32 !important; color: white !important; border: 1px solid #1c5221 !important; font-weight: bold !important; }
.btn-green-submit button:hover { background-color: #215e26 !important; }

/* Force Semua Inputan Berwarna Terang Teks Hitam */
div[data-baseweb="input"] input, div[data-baseweb="select"] > div { background-color: white !important; color: black !important; }
div[data-baseweb="input"] { border: 1px solid #a0a0a0 !important; }
p, span, label { color: black !important; }
div[data-testid="stDataFrame"] { background-color: white !important; border: 1px solid #cccccc !important; }
</style>
""", unsafe_allow_html=True)

if "terautentikasi" not in st.session_state:
    st.session_state.terautentikasi = False
if "halaman_aktif" not in st.session_state:
    st.session_state.halaman_aktif = "login"
if "foto_terpilih" not in st.session_state:
    st.session_state.foto_terpilih = None

# ==============================================================================
# TAMPILAN 1: REPLIKA LOGIN / SIGN UP SCREEN
# ==============================================================================
if not st.session_state.terautentikasi:
    _, center_col, _ = st.columns([1, 1.1, 1])
    
    with center_col:
        # Pemicu CSS Kotak Putih Auth
        st.markdown('<div id="auth_card_trigger"></div>', unsafe_allow_html=True)
        
        # --- MODE HALAMAN LOGIN ---
        if st.session_state.halaman_aktif == "login":
            # 1. Gambar/Logo Paling Atas
            if os.path.exists("logoo.PNG"):
                st.image("logoo.PNG", use_container_width=True)
            else:
                st.markdown("<div style='height:100px; background:#e0e0e0; text-align:center; padding-top:35px; color:gray;'>[ login.jpeg ]</div>", unsafe_allow_html=True)
            
            st.write("<br>", unsafe_allow_html=True)
            
            # 2. Input Fields Berurutan
            username_input = st.text_input("Username", placeholder="Username", label_visibility="collapsed", key="txt_user")
            st.write("")
            password_input = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed", key="txt_pass")
            st.write("<br>", unsafe_allow_html=True)
            
            # 3. Tombol LOG IN di Tengah Kecil
            col_b1, col_b2, col_b3 = st.columns([1, 1.2, 1])
            with col_b2:
                btn_login = st.button("LOG IN", use_container_width=True)
                
            if btn_login:
                conn = sqlite3.connect(DB_LOGIN_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (username_input, password_input))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.terautentikasi = True
                    st.rerun()
                else:
                    st.error("Username atau Password Salah")
            
            # 4. Teks Tautan Pindah Halaman di Pojok Bawah
            st.markdown("<div class='nav-text-container'>", unsafe_allow_html=True)
            if st.button("Create Account", key="go_signup"):
                st.session_state.halaman_aktif = "signup"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # --- MODE HALAMAN SIGN UP ---
        else:
            # 1. Gambar/Logo Paling Atas
            if os.path.exists("logoo.PNG"):
                st.image("logoo.PNG", use_container_width=True)
            else:
                st.markdown("<div style='height:100px; background:#e0e0e0; text-align:center; padding-top:35px; color:gray;'>[ signup.jpg ]</div>", unsafe_allow_html=True)
            
            st.write("<br>", unsafe_allow_html=True)
            
            # 2. Input Fields Berurutan
            reg_email = st.text_input("Email", placeholder="Email", label_visibility="collapsed", key="reg_e")
            st.write("")
            reg_pass = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed", key="reg_p")
            st.write("")
            reg_confirm = st.text_input("Confirm Password", placeholder="Confirm Password", type="password", label_visibility="collapsed", key="reg_c")
            st.write("<br>", unsafe_allow_html=True)
            
            # 3. Tombol Sign Up
            col_s1, col_s2, col_s3 = st.columns([1, 1.2, 1])
            with col_s2:
                btn_signup = st.button("Sign Up", use_container_width=True)
                
            if btn_signup:
                if reg_pass != reg_confirm:
                    st.error("Password tidak sama")
                elif reg_email == "" or reg_pass == "":
                    st.warning("Form tidak boleh kosong")
                else:
                    try:
                        conn = sqlite3.connect(DB_LOGIN_PATH)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO data_pengguna(email,password) VALUES (?,?)", (reg_email, reg_pass))
                        conn.commit()
                        conn.close()
                        st.success("Akun sukses dibuat!")
                        st.session_state.halaman_aktif = "login"
                        st.rerun()
                    except:
                        st.error("Email sudah terdaftar")
            
            # 4. Teks Tautan Kembali ke Login
            st.markdown("<div class='nav-text-container'>", unsafe_allow_html=True)
            if st.button("Log In", key="go_login"):
                st.session_state.halaman_aktif = "login"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# TAMPILAN 2: REPLIKA DASHBOARD UTAMA (DENGAN TATA LETAK JELAS DAN PRESISI)
# ==============================================================================
else:
    # Header Panjang Hijau di Paling Atas
    st.markdown("<div class='app-header-green'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>", unsafe_allow_html=True)
    
    # Tombol kecil Log Out ditaruh di atas kanan luar frame
    o_l, o_r = st.columns([11.8, 1.2])
    with o_r:
        if st.button("Log Out", use_container_width=True):
            st.session_state.terautentikasi = False
            st.rerun()

    # Memecah Layout Menjadi 2 Kolom Berdampingan Sesuai Sketsa
    kolom_kiri, kolom_kanan = st.columns([1, 1.35])
    
    # ------------------ KOTAK 1: PANEL INPUT SCANNER (KIRI) ------------------
    with kolom_kiri:
        st.markdown("<div class='group-box'><div class='group-box-title'>Panel Input Scanner</div>", unsafe_allow_html=True)
        
        # Komoditas Label & Dropdown
        st.markdown("<p style='font-weight:bold; margin-bottom:2px;'>Komoditas</p>", unsafe_allow_html=True)
        pilih_komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"], label_visibility="collapsed")
        
        # Kotak Kerangka Preview Gambar
        st.write("<p style='font-weight:bold; margin-top:10px; margin-bottom:2px;'>Preview Gambar</p>", unsafe_allow_html=True)
        st.markdown("<div style='background-color:#dcdcdc; border:1px solid #b0b0b0; height:180px; width:100%; display:flex; align-items:center; justify-content:center; overflow:hidden; margin-bottom:12px;'>", unsafe_allow_html=True)
        if st.session_state.foto_terpilih is None:
            st.markdown("<span style='color:#555555; font-size:14px;'>[ Preview Gambar ]</span>", unsafe_allow_html=True)
        else:
            st.image(st.session_state.foto_terpilih, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Input upload file tersembunyi
        media_input = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed", key="uploader_dash")
        if media_input:
            st.session_state.foto_terpilih = Image.open(media_input)
            
        # Tombol Aksi Sesuai Urutan Sketsa
        st.markdown("<div class='btn-style'>", unsafe_allow_html=True)
        if st.button("Buka Kamera", use_container_width=True):
            st.info("Kamera Siap. Silakan unggah gambar lewat kolom di atas.")
            
        if st.button("Pilih Foto", use_container_width=True):
            st.info("Gunakan kolom upload file di atas untuk memilih foto.")
            
        st.button("Pilih ROI", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Tombol Eksekusi Analisis (Warna Hijau Khusus)
        st.markdown("<div class='btn-style btn-green-submit' style='margin-top:10px;'>", unsafe_allow_html=True)
        btn_eksekusi = st.button("Jalankan Analisis", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if btn_eksekusi and st.session_state.foto_terpilih is not None:
            img_np = np.array(st.session_state.foto_terpilih)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            nama, kondisi, sisa = cek_kondisi_citra(img_cv, pilih_komoditas)
            if sisa == -1:
                st.error(kondisi)
            else:
                suhu_ideal = rekomendasi_suhu(nama)
                conn = sqlite3.connect(DB_ANALISIS_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?,?,?,?)", (nama, kondisi, f"{sisa} Hari", suhu_ideal))
                conn.commit()
                conn.close()
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ KOTAK 2: DASHBOARD OUTPUT (KANAN) ------------------
    with kolom_kanan:
        st.markdown("<div class='group-box'><div class='group-box-title'>Dashboard</div>", unsafe_allow_html=True)
        
        # Ambil data riwayat terbaru dari database sqlite3
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_db = cursor.fetchall()
        conn.close()
        
        k_nama, k_kondisi, k_sisa, k_suhu = "-", "-", "-", "-"
        if data_db:
            k_nama, k_kondisi, k_sisa, k_suhu = data_db[0][1], data_db[0][2], data_db[0][3], data_db[0][4]
            
        # Tampilan Teks Hasil Utama
        st.markdown(f"""
        <div class='result-display-frame'>
            Hasil Pindai Sistem<br>
            ---------------------------<br>
            Komoditas : {k_nama}<br>
            Kondisi   : {k_kondisi}<br>
            Sisa Hari : {k_sisa}<br>
            Suhu      : {k_suhu}
        </div>
        """, unsafe_allow_html=True)
        
        # Kerangka Tabel Riwayat Data Analisis
        st.markdown("<p style='font-weight:bold; margin-bottom:5px;'>Riwayat Data</p>", unsafe_allow_html=True)
        if data_db:
            import pandas as pd
            df_tabel = pd.DataFrame(data_db, columns=["ID", "Nama", "Kondisi", "Sisa", "Suhu"])
            st.dataframe(df_tabel, hide_index=True, use_container_width=True, height=270)
        else:
            st.markdown("<div style='border:1px solid #ccc; background:white; color:gray; text-align:center; padding:40px;'>Belum ada data riwayat pindai.</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
