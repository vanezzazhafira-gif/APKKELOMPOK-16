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
# CSS CONFIG & LAYOUT DESKTOP
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", page_icon="🌱", layout="wide")

st.markdown("""
<style>
/* Sembunyikan header default streamlit */
header, footer, [data-testid="stHeader"] { visibility: hidden !important; height: 0px !important; }

/* Background dasar aplikasi web */
.stApp { background-color: #f0f0f0 !important; }

/* Membungkus form login ke dalam Card putih di tengah */
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stCustomComponentToWebpage"]) {
    background-color: white !important;
    border: 1px solid #bcbcbc !important;
    border-radius: 8px !important;
    padding: 35px !important;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.12) !important;
    max-width: 450px !important;
    margin: auto !important;
}

.app-title-tk {
    font-size: 14px !important;
    font-weight: bold !important;
    color: black !important;
    text-align: center !important;
    margin-top: 5px !important;
    margin-bottom: 25px !important;
}

/* --- PANEL UTAMA DASHBOARD --- */
.app-header-green {
    background-color: #246329 !important;
    border: 1px solid #18441c;
    padding: 10px !important;
    text-align: center !important;
    color: white !important;
    font-size: 18px !important;
    font-weight: bold !important;
    margin-bottom: 15px;
}
.group-box {
    background-color: #f9f9f9 !important;
    border: 1px solid #b8b8b8 !important;
    border-radius: 3px !important;
    padding: 15px !important;
    position: relative;
    min-height: 540px;
}
.group-box-title {
    position: absolute;
    top: -12px;
    left: 15px;
    background-color: #f0f0f0;
    padding: 0 5px;
    font-weight: bold !important;
    font-size: 13px !important;
    color: black !important;
}
.result-display-frame {
    text-align: center !important;
    font-family: monospace !important;
    font-size: 15px !important;
    color: black !important;
    line-height: 1.6;
    margin-top: 10px;
    margin-bottom: 20px;
}

/* --- STYLING WARNA TOMBOL --- */
.btn-blue button { background-color: #1e81d2 !important; color: white !important; border-radius: 0px !important; }
.btn-orange button { background-color: #f19f12 !important; color: white !important; border-radius: 0px !important; }
.btn-purple button { background-color: #7a1fa2 !important; color: white !important; border-radius: 0px !important; }
.btn-green button { background-color: #2c7d32 !important; color: white !important; border-radius: 0px !important; font-weight: bold !important; }

div[data-baseweb="input"] { background-color: white !important; border: 1px solid #a0a0a0 !important; color: black !important; }
div[data-baseweb="select"] { background-color: white !important; color: black !important; }
div[data-testid="stMarkdownContainer"] p { color: black !important; }
</style>
""", unsafe_allow_html=True)

if "terautentikasi" not in st.session_state:
    st.session_state.terautentikasi = False
if "user_aktif" not in st.session_state:
    st.session_state.user_aktif = ""
if "foto_terpilih" not in st.session_state:
    st.session_state.foto_terpilih = None
if "halaman_aktif" not in st.session_state:
    st.session_state.halaman_aktif = "login"  # Default ke halaman login

# ==============================================================================
# INTERFASE LOGIN & SIGNUP (NAVIGASI DIPINDAH KE BAGIAN BAWAH FORM)
# ==============================================================================
if not st.session_state.terautentikasi:
    st.write("<br><br>", unsafe_allow_html=True)
    
    col_kiri, col_tengah, col_kanan = st.columns([1, 1.1, 1])
    
    with col_tengah:
        # Pemicu CSS container
        st.write("") 
        
        # 1. Tampilkan Logo Kelompok Paling Atas di Dalam Kotak
        if os.path.exists("logoo.PNG"):
            c_img1, c_img2, c_img3 = st.columns([1, 1.2, 1])
            with c_img2:
                st.image("logoo.PNG", width=100)
                
        # TAMPILAN JIKA MENYALAKAN HALAMAN LOGIN
        if st.session_state.halaman_aktif == "login":
            st.markdown("<h1 style='text-align: center; color: black; font-size: 34px; margin: 0;'>Log In</h1>", unsafe_allow_html=True)
            st.markdown("<div class='app-title-tk'>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</div>", unsafe_allow_html=True)
            
            username_input = st.text_input("Username", placeholder="Username", label_visibility="collapsed", key="txt_user")
            st.write("")
            password_input = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed", key="txt_pass")
            st.write("<br>", unsafe_allow_html=True)
            
            if st.button("LOG IN", use_container_width=True):
                conn = sqlite3.connect(DB_LOGIN_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (username_input, password_input))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.terautentikasi = True
                    st.session_state.user_aktif = username_input
                    st.rerun()
                else:
                    st.error("Username atau Password Salah")
            
            # --- NAVIGASI PINDAH KE BAWAH ---
            st.write("---")
            col_nav1, col_nav2 = st.columns([1.6, 1])
            with col_nav1:
                st.markdown("<p style='font-size:13px; margin-top:5px; color: black;'>Have not account?</p>", unsafe_allow_html=True)
            with col_nav2:
                if st.button("Create Account", use_container_width=True):
                    st.session_state.halaman_aktif = "signup"
                    st.rerun()
                    
        # TAMPILAN JIKA MENYALAKAN HALAMAN SIGNUP
        else:
            st.markdown("<h1 style='text-align: center; color: black; font-size: 34px; margin: 0;'>Sign Up</h1>", unsafe_allow_html=True)
            st.markdown("<div class='app-title-tk' style='color:#246329 !important;'>Create an account</div>", unsafe_allow_html=True)
            
            reg_email = st.text_input("Email", placeholder="Email", label_visibility="collapsed", key="reg_e")
            st.write("")
            reg_pass = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed", key="reg_p")
            st.write("")
            reg_confirm = st.text_input("Confirm Password", placeholder="Confirm Password", type="password", label_visibility="collapsed", key="reg_c")
            st.write("<br>", unsafe_allow_html=True)
            
            if st.button("Sign Up", use_container_width=True):
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
                        st.success("Akun berhasil dibuat!")
                        st.session_state.halaman_aktif = "login"
                        st.rerun()
                    except:
                        st.error("Email sudah digunakan")
            
            # --- NAVIGASI PINDAH KE BAWAH ---
            st.write("---")
            col_nav1, col_nav2 = st.columns([1.7, 1])
            with col_nav1:
                st.markdown("<p style='font-size:13px; margin-top:5px; color: black;'>Already have an account?</p>", unsafe_allow_html=True)
            with col_nav2:
                if st.button("Log In", use_container_width=True):
                    st.session_state.halaman_aktif = "login"
                    st.rerun()

# ==============================================================================
# INTERFASE DASHBOARD UTAMA
# ==============================================================================
else:
    st.markdown("<div class='app-header-green'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>", unsafe_allow_html=True)
    
    col_out_1, col_out_2 = st.columns([9, 1])
    with col_out_2:
        if st.button("Log Out", use_container_width=True):
            st.session_state.terautentikasi = False
            st.rerun()

    kolom_kiri, kolom_kanan = st.columns([1, 1.45])
    
    # --- PANEL INPUT SCANNER ---
    with kolom_kiri:
        st.markdown("<div class='group-box'><div class='group-box-title'>Panel Input Scanner</div>", unsafe_allow_html=True)
        
        pilih_komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"], label_visibility="collapsed")
        
        st.markdown("<div style='background-color:#dcdcdc; border:1px solid #b0b0b0; height:270px; width:100%; display:flex; align-items:center; justify-content:center; overflow:hidden; margin-bottom:10px;'>", unsafe_allow_html=True)
        if st.session_state.foto_terpilih is None:
            st.markdown("<span style='color:#666666; font-size:14px;'>[ Preview ]</span>", unsafe_allow_html=True)
        else:
            st.image(st.session_state.foto_terpilih, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        media_input = st.file_uploader("Upload", type=["jpg","png","jpeg"], label_visibility="collapsed", key="file_internal")
        if media_input:
            st.session_state.foto_terpilih = Image.open(media_input)
            
        st.markdown("<div class='btn-blue'>", unsafe_allow_html=True)
        if st.button("Buka Kamera", use_container_width=True):
            st.info("Unggah berkas foto secara langsung via file uploader di atas.")
        st.markdown("</div><div class='btn-orange'>", unsafe_allow_html=True)
        st.button("Pilih Foto dari Galeri", use_container_width=True)
        st.markdown("</div><div class='btn-purple'>", unsafe_allow_html=True)
        st.button("Tandai Area Sayur (ROI)", use_container_width=True)
        st.markdown("</div><div class='btn-green'>", unsafe_allow_html=True)
        
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

    # --- PANEL DASHBOARD ---
    with kolom_kanan:
        st.markdown("<div class='group-box'><div class='group-box-title'>Dashboard</div>", unsafe_allow_html=True)
        
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_db = cursor.fetchall()
        conn.close()
        
        k_nama, k_kondisi, k_sisa, k_suhu = "-", "-", "-", "-"
        if data_db:
            k_nama, k_kondisi, k_sisa, k_suhu = data_db[0][1], data_db[0][2], data_db[0][3], data_db[0][4]
            
        st.markdown(f"""
        <div class='result-display-frame'>
            Hasil Pindai Sistem<br>
            =====================<br>
            Komoditas : {k_nama}<br>
            Kondisi   : {k_kondisi}<br>
            Sisa      : {k_sisa}<br>
            Suhu Simpan : {k_suhu}
        </div>
        """, unsafe_allow_html=True)
        
        if data_db:
            import pandas as pd
            df_tabel = pd.DataFrame(data_db, columns=["ID", "Nama", "Kondisi", "Sisa", "Suhu"])
            st.dataframe(df_tabel, hide_index=True, use_container_width=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
