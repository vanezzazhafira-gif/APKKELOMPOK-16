import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os
import time

# ==============================================================================
# 1. INISIALISASI DATABASE & LOGIKA SISTEM (OTOMATIS BERSIH & RESET ID KE 1)
# ==============================================================================
DB_LOGIN_PATH = "manajemen_akses.db"
DB_ANALISIS_PATH = "logistik_hortikultura.db"

def init_databases():
    # Database Akun Pengguna
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

    # Database Hasil Analisis Logistik
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
    
    # RESET TOTAL SAAT APLIKASI DI-BOOT/RESTART: Hapus data & kembalikan ID ke angka 1
    if "db_terbersihkan" not in st.session_state:
        cursor.execute("DELETE FROM riwayat_pindai")
        # Perintah ini wajib untuk memaksa AUTOINCREMENT kembali mulai dari 1
        cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'riwayat_pindai'")
        st.session_state.db_terbersihkan = True
        
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
# 2. SEGMEN LAYOUT CSS
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", layout="wide")

if "halaman" not in st.session_state:
    st.session_state.halaman = "login"
if "foto_input" not in st.session_state:
    st.session_state.foto_input = None
if "mode_input" not in st.session_state:
    st.session_state.mode_input = None

st.markdown("""
<style>
    .stApp {
        background-color: #ffffff !important;
    }
    header { visibility: hidden; }
    
    [data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    
    .stWidgetLabel, .stWidgetLabel p, label p {
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    .bg-circle-top-right {
        position: fixed;
        width: 440px;
        height: 440px;
        background-color: #527a4d;
        border-radius: 50%;
        top: -160px;
        right: -110px;
        z-index: 0;
    }

    .bg-circle-bottom-left {
        position: fixed;
        width: 440px;
        height: 440px;
        background-color: #527a4d;
        border-radius: 50%;
        bottom: -160px;
        left: -110px;
        z-index: 0;
    }

    .login-container {
        position: relative;
        z-index: 10;
        max-width: 440px;
        margin: 0 auto;
        padding-top: 10px;
    }
    
    .logo-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 0 auto 5px auto;
        width: 100%;
    }
    
    .stTextInput>div>div>input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
    }
</style>
""", unsafe_allow_html=True)

NAMA_FILE_LOGO = "logoo.PNG"

# ==============================================================================
# 3. HALAMAN INTERFACE: LOG IN
# ==============================================================================
if st.session_state.halaman == "login":
    st.markdown('<div class="bg-circle-top-right"></div>', unsafe_allow_html=True)
    st.markdown('<div class="bg-circle-bottom-left"></div>', unsafe_allow_html=True)
    
    col_space1, col_center, col_space2 = st.columns([1.1, 1, 1.1])
    
    with col_center:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown('<div class="logo-wrapper">', unsafe_allow_html=True)
        if os.path.exists(NAMA_FILE_LOGO):
            img_real_logo = Image.open(NAMA_FILE_LOGO)
            st.image(img_real_logo, width=250)
        else:
            st.warning(f"File '{NAMA_FILE_LOGO}' tidak ditemukan.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center; color: #000000; font-size: 50px; font-weight: bold; margin-top: 5px; margin-bottom: 25px;'>Log In</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #000000; font-size: 15px; font-weight: bold; margin-bottom: 40px;'>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</p>", unsafe_allow_html=True)
        
        in_user = st.text_input("Username", placeholder="Masukkan username anda", key="log_user")
        in_pass = st.text_input("Password", placeholder="Masukkan password anda", type="password", key="log_pass")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn_center_l, col_btn_center_m, col_btn_center_r = st.columns([1, 1.3, 1])
        with col_btn_center_m:
            btn_login_click = st.button("LOG IN", use_container_width=True)
            
        if btn_login_click:
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
                
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        col_text_footer, col_btn_footer = st.columns([1.4, 1])
        with col_text_footer:
            st.markdown("<p style='color: #000000; font-size: 15px; font-weight: 500; text-align: right; margin-top: 5px;'>Have not account?</p>", unsafe_allow_html=True)
        with col_btn_footer:
            if st.button("Create Account", use_container_width=True, key="btn_to_signup"):
                st.session_state.halaman = "signup"
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 4. HALAMAN INTERFACE: SIGN UP
# ==============================================================================
elif st.session_state.halaman == "signup":
    st.markdown('<div class="bg-circle-top-right"></div>', unsafe_allow_html=True)
    st.markdown('<div class="bg-circle-bottom-left"></div>', unsafe_allow_html=True)
    
    col_space1, col_center, col_space2 = st.columns([1.1, 1, 1.1])
    
    with col_center:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown('<div class="logo-wrapper">', unsafe_allow_html=True)
        if os.path.exists(NAMA_FILE_LOGO):
            img_real_logo = Image.open(NAMA_FILE_LOGO)
            st.image(img_real_logo, width=250)
        else:
            st.warning(f"File '{NAMA_FILE_LOGO}' tidak ditemukan.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center; color: #000000; font-size: 50px; font-weight: bold; margin-top: 5px; margin-bottom: 25px;'>Sign Up</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #527a4d; font-size: 15px; font-weight: bold; margin-bottom: 30px;'>Create an account</p>", unsafe_allow_html=True)
        
        reg_email = st.text_input("Email", placeholder="Masukkan email baru", key="reg_e")
        reg_pass1 = st.text_input("Password", placeholder="Buat kata sandi", type="password", key="reg_p1")
        reg_pass2 = st.text_input("Confirm Password", placeholder="Ulangi kata sandi", type="password", key="reg_p2")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn_center_l, col_btn_center_m, col_btn_center_r = st.columns([1, 1.3, 1])
        with col_btn_center_m:
            btn_signup_click = st.button("Sign Up", use_container_width=True)
            
        if btn_signup_click:
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
                    
                    st.toast("Akun berhasil dibuat! Mengalihkan ke halaman login...")
                    st.success("Akun berhasil dibuat!")
                    time.sleep(2)
                    
                    st.session_state.halaman = "login"
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Email tersebut sudah terdaftar!")
                    
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        col_text_footer, col_btn_footer = st.columns([1.4, 1])
        with col_text_footer:
            st.markdown("<p style='color: #000000; font-size: 15px; font-weight: 500; text-align: right; margin-top: 5px;'>Already have an account?</p>", unsafe_allow_html=True)
        with col_btn_footer:
            if st.button("Log In", use_container_width=True, key="btn_to_login"):
                st.session_state.halaman = "login"
                st.rerun()
                
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 5. HALAMAN INTERFACE: DASHBOARD UTAMA MONITORING
# ==============================================================================
elif st.session_state.halaman == "dashboard":
    st.markdown("""
        <div style="background-color: #246329; padding: 12px; border-radius: 4px; text-align: center; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0; font-weight: bold; letter-spacing: 1px;">OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col_space, col_logout = st.columns([11, 1])
    with col_logout:
        if st.button("Log Out", use_container_width=True):
            st.session_state.foto_input = None
            st.session_state.mode_input = None
            st.session_state.halaman = "login"
            st.rerun()
            
    panel_kiri, panel_kanan = st.columns([1, 1.3])
    
    with panel_kiri:
        st.markdown("### **Panel Input Scanner**")
        pilihan_sayur = st.selectbox("Komoditas:", ["Wortel", "Cabai", "Brokoli"], label_visibility="visible")
        
        with st.container(border=True):
            if st.session_state.foto_input is None:
                st.markdown("<div style='height: 250px; background-color: #e8e8e8; display: flex; align-items: center; justify-content: center; border-radius:4px; color:#555;'><B>[ Preview ]</B></div>", unsafe_allow_html=True)
            else:
                st.image(st.session_state.foto_input, use_container_width=True)
                
        # Tombol Pemicu Menu Utama
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            if st.button("Pilih Foto dari Galeri", use_container_width=True):
                st.session_state.mode_input = "galeri"
        with col_m2:
            if st.button("Buka Kamera", use_container_width=True):
                st.session_state.mode_input = "kamera"

        if st.session_state.mode_input == "galeri":
            file_terunggah = st.file_uploader("Unggah berkas foto atau gambar sayur:", type=["jpg", "png", "jpeg"])
            if file_terunggah:
                st.session_state.foto_input = Image.open(file_terunggah)
                
        if st.session_state.mode_input == "kamera":
            ambil_kamera = st.camera_input("Ambil Foto langsung dari Kamera:")
            if ambil_kamera:
                st.session_state.foto_input = Image.open(ambil_kamera)
        
        st.button("Tandai Area Sayur (ROI)", use_container_width=True)
        
        st.write("")
        btn_proses_analisis = st.button("Jalankan Analisis", use_container_width=True, type="primary")
        
        if btn_proses_analisis:
            if st.session_state.foto_input is None:
                st.warning("Mohon masukkan foto sayuran terlebih dahulu!")
            else:
                img_mat = np.array(st.session_state.foto_input)
                if len(img_mat.shape) == 3 and img_mat.shape[2] == 4:
                    img_mat = cv2.cvtColor(img_mat, cv2.COLOR_RGBA2RGB)
                img_bgr = cv2.cvtColor(img_mat, cv2.COLOR_RGB2BGR)
                
                nama, kondisi, sisa_hari = cek_kondisi_citra(img_bgr, pilihan_sayur)
                
                if sisa_hari == -1:
                    st.error(kondisi)
                else:
                    suhu_ruang = rekomendasi_suhu(nama)
                    
                    conn = sqlite3.connect(DB_ANALISIS_PATH)
                    cursor = conn.cursor()
                    
                    # Bersihkan riwayat data lama dan RESET urutan AUTOINCREMENT kembali ke 1 sebelum menyimpan data baru
                    cursor.execute("DELETE FROM riwayat_pindai")
                    cursor.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'riwayat_pindai'")
                    
                    # Simpan data pemindaian baru yang selalu menempati ID = 1
                    cursor.execute("""
                        INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan)
                        VALUES (?, ?, ?, ?)
                    """, (nama, kondisi, f"{sisa_hari} Hari", suhu_ruang))
                    
                    conn.commit()
                    conn.close()
                    st.success("Analisis selesai!")
                    st.rerun()

    with panel_kanan:
        st.markdown("### **Dashboard**")
        
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        isi_tabel = cursor.fetchall()
        conn.close()
        
        v_nama, v_kondisi, v_sisa, v_suhu = "-", "-", "-", "-"
        if isi_tabel:
            v_nama, v_kondisi, v_sisa, v_suhu = isi_tabel[0][1], isi_tabel[0][2], isi_tabel[0][3], isi_tabel[0][4]
            
        st.markdown(f"""
        <div style="background-color: #ffffff; border: 1px solid #c8c8c8; padding: 15px; border-radius: 4px; font-family: 'Courier New', Courier, monospace; color: black; line-height: 1.5; margin-bottom: 20px;">
            <p style="margin: 0; text-align: center; font-weight: bold;">Hasil Pindai Sistem</p>
            <p style="margin: 0; text-align: center;">====================</p>
            <p style="margin: 5px 0 5px 40px;">Komoditas : {v_nama}</p>
            <p style="margin: 5px 0 5px 40px;">Kondisi   : {v_kondisi}</p>
            <p style="margin: 5px 0 5px 40px;">Sisa      : {v_sisa}</p>
            <p style="margin: 5px 0 5px 40px;">Suhu Simpan : {v_suhu}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if isi_tabel:
            import pandas as pd
            df_monitor = pd.DataFrame(isi_tabel, columns=["ID", "Nama", "Kondisi", "Sisa", "Suhu"])
            st.dataframe(df_monitor, hide_index=True, use_container_width=True)
        else:
            st.info("Belum ada riwayat pemindaian.")
