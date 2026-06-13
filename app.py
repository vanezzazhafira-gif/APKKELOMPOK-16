import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# ==============================================================================
# DATABASE MANAGEMENT (AUTOMATIC DETACH & RESET)
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
# CSS INTERFACE ENGINE (REPLIKA TKINTER MOCKUP 100% PERSIS)
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", page_icon="🌱", layout="wide")

st.markdown("""
<style>
/* Sembunyikan Header Bawaan Streamlit */
header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] { visibility: hidden !important; height: 0px !important; }

/* Background Dasar Windows Desktop */
.stApp { background-color: #f0f0f0 !important; }

/* KERTAS TKINTER: Wadah tunggal utama halaman Login/Signup */
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="tkinter_paper_frame"]) {
    background-color: white !important;
    background-image: 
        radial-gradient(circle at top right, #4c7a3c 0%, #4c7a3c 140px, transparent 141px),
        radial-gradient(circle at bottom left, #4c7a3c 0%, #4c7a3c 140px, transparent 141px) !important;
    background-repeat: no-repeat !important;
    border: 1px solid #999999 !important;
    border-radius: 12px !important;
    padding: 40px 50px !important;
    box-shadow: 0px 4px 20px rgba(0,0,0,0.15) !important;
    max-width: 520px !important;
    min-height: 720px !important;
    margin: 30px auto !important;
    position: relative !important;
}

/* Memposisikan Logo di Kiri Atas persis Gambar Mockup */
.logo-tkinter-position {
    text-align: left !important;
    margin-left: -10px !important;
    margin-top: -10px !important;
    margin-bottom: 10px !important;
}

/* Judul Utama & Subtitle Sesuai Mockup */
.title-login-tk { font-family: 'Arial Black', Gadget, sans-serif !important; color: black !important; font-size: 42px !important; font-weight: bold !important; text-align: center !important; margin-top: 10px !important; margin-bottom: 5px !important; }
.title-signup-tk { font-family: 'Arial Black', Gadget, sans-serif !important; color: black !important; font-size: 42px !important; font-weight: bold !important; text-align: center !important; margin-top: 5px !important; margin-bottom: 2px !important; }
.subtitle-tk { font-family: 'Arial', sans-serif !important; color: black !important; font-size: 15px !important; font-weight: bold !important; text-align: center !important; margin-bottom: 40px !important; }

/* Kotak Input Besar & Bersih Berwarna Putih */
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="tkinter_paper_frame"]) div[data-baseweb="input"] {
    background-color: white !important;
    border: 1px solid #a6a6a6 !important;
    border-radius: 0px !important; /* Kotak siku khas Tkinter */
    padding: 4px 6px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="tkinter_paper_frame"]) input {
    color: black !important;
    font-size: 16px !important;
}

/* Label Teks Input */
.input-label-tk { color: #555555 !important; font-size: 14px !important; font-weight: bold !important; margin-bottom: 4px !important; margin-top: 15px !important; }

/* Tombol LOG IN / SIGN UP Kotak Putih Tengah */
.btn-container-tk { text-align: center !important; margin-top: 30px !important; margin-bottom: 20px !important; }
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="tkinter_paper_frame"]) button {
    background-color: white !important;
    color: black !important;
    border: 1px solid #b0b0b0 !important;
    border-radius: 4px !important;
    padding: 6px 24px !important;
    font-size: 14px !important;
    font-weight: normal !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[id="tkinter_paper_frame"]) button:hover {
    background-color: #f5f5f5 !important;
    border-color: #333333 !important;
}

/* Navigasi Pindah Form di Bagian Bawah */
.footer-nav-tk { text-align: center !important; font-size: 14px !important; color: black !important; margin-top: 40px !important; }
.footer-nav-tk button { background: white !important; border: 1px solid #cccccc !important; padding: 2px 10px !important; font-size: 12px !important; margin-left: 10px !important; display: inline-block !important; }

/* Logo Tambahan Khusus di Bawah Halaman Sign Up */
.logo-bottom-signup { text-align: center !important; margin-top: 30px !important; }

# ==============================================================================
# DASHBOARD INTERFACE REPLICA STYLE
# ==============================================================================
.dashboard-title-green { background-color: #246329 !important; border: 1px solid #18441c; padding: 10px !important; text-align: center !important; color: white !important; font-size: 20px !important; font-weight: bold !important; margin-bottom: 15px; }
.panel-box-tk { background-color: #f0f0f0 !important; border: 1px solid #b8b8b8 !important; padding: 20px 15px 15px 15px !important; position: relative; min-height: 560px; }
.panel-box-title-tk { position: absolute; top: -12px; left: 12px; background-color: #f0f0f0; padding: 0 6px; font-weight: bold !important; font-size: 14px !important; color: black !important; }
.preview-window-tk { background-color: #dcdcdc; border: 1px solid #b0b0b0; height: 210px; width: 100%; display: flex; align-items: center; justify-content: center; overflow:hidden; margin-bottom: 15px; }
.monitor-frame-tk { text-align: left !important; font-family: monospace !important; font-size: 15px !important; color: black !important; line-height: 1.6; background-color: #ffffff; border: 1px dashed #a0a0a0; padding: 15px; margin-bottom: 20px; }
.btn-blue-tk button { background-color: #1f85de !important; color: white !important; border: 1px solid #1461a4 !important; border-radius: 2px !important; }
.btn-orange-tk button { background-color: #f39c12 !important; color: white !important; border: 1px solid #d35400 !important; border-radius: 2px !important; }
.btn-purple-tk button { background-color: #8e44ad !important; color: white !important; border: 1px solid #732d91 !important; border-radius: 2px !important; }
.btn-green-tk button { background-color: #27ae60 !important; color: white !important; border: 1px solid #1e824c !important; font-weight: bold !important; border-radius: 2px !important; }
div[data-baseweb="select"] > div { background-color: white !important; color: black !important; }
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
# TAMPILAN 1: HALAMAN AUTHENTICATION (REPLIKA KERTAS TKINTER 100% AKURAT)
# ==============================================================================
if not st.session_state.terautentikasi:
    _, center_layout, _ = st.columns([1, 1.1, 1])
    
    with center_layout:
        # Menandai Container Kertas Tkinter
        st.markdown('<div id="tkinter_paper_frame"></div>', unsafe_allow_html=True)
        
        with st.container():
            # --- SUB HALAMAN: LOGIN ---
            if st.session_state.halaman_aktif == "login":
                # Logo kelompok di kiri atas dalam kertas (Sesuai image_d159a1.png)
                st.markdown("<div class='logo-tkinter-position'>", unsafe_allow_html=True)
                if os.path.exists("logoo.PNG"):
                    st.image("logoo.PNG", width=120)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Teks Judul Login Tengah
                st.markdown("<div class='title-login-tk'>Log In</div>", unsafe_allow_html=True)
                st.markdown("<div class='subtitle-tk'>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</div>", unsafe_allow_html=True)
                
                # Field Input Berurutan Ke Bawah
                st.markdown("<div class='input-label-tk'>Username</div>", unsafe_allow_html=True)
                username_val = st.text_input("User", placeholder="Username", label_visibility="collapsed", key="tk_user")
                
                st.markdown("<div class='input-label-tk'>Password</div>", unsafe_allow_html=True)
                password_val = st.text_input("Pass", placeholder="Password", type="password", label_visibility="collapsed", key="tk_pass")
                
                # Tombol Log In Tengah Siku-Siku
                st.markdown("<div class='btn-container-tk'>", unsafe_allow_html=True)
                click_login = st.button("LOG IN", key="btn_execute_login")
                st.markdown("</div>", unsafe_allow_html=True)
                
                if click_login:
                    conn = sqlite3.connect(DB_LOGIN_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (username_val, password_val))
                    valid_user = cursor.fetchone()
                    conn.close()
                    if valid_user:
                        st.session_state.terautentikasi = True
                        st.rerun()
                    else:
                        st.error("Username atau Password Salah")
                
                # Navigasi Tautan Bawah Kertas
                st.markdown("<div class='footer-nav-tk'>Have not account? ", unsafe_allow_html=True)
                if st.button("Create Account", key="tk_goto_signup"):
                    st.session_state.halaman_aktif = "signup"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # --- SUB HALAMAN: SIGN UP ---
            else:
                # Judul Atas Tengah Sign Up (Sesuai image_d1dce3.png)
                st.markdown("<div class='title-signup-tk'>Sign Up</div>", unsafe_allow_html=True)
                st.markdown("<div class='subtitle-tk' style='color:#4c7a3c;'>Create an account</div>", unsafe_allow_html=True)
                
                # Field Input Registrasi
                st.markdown("<div class='input-label-tk'>Email</div>", unsafe_allow_html=True)
                reg_email = st.text_input("E", placeholder="Email", label_visibility="collapsed", key="tk_reg_e")
                
                st.markdown("<div class='input-label-tk'>Password</div>", unsafe_allow_html=True)
                reg_pass = st.text_input("P", placeholder="Password", type="password", label_visibility="collapsed", key="tk_reg_p")
                
                st.markdown("<div class='input-label-tk'>Confirm Password</div>", unsafe_allow_html=True)
                reg_confirm = st.text_input("C", placeholder="Confirm Password", type="password", label_visibility="collapsed", key="tk_reg_c")
                
                # Tombol Sign Up Tengah
                st.markdown("<div class='btn-container-tk'>", unsafe_allow_html=True)
                click_signup = st.button("Sign Up", key="btn_execute_signup")
                st.markdown("</div>", unsafe_allow_html=True)
                
                if click_signup:
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
                            st.success("Akun Sukses Dibuat!")
                            st.session_state.halaman_aktif = "login"
                            st.rerun()
                        except:
                            st.error("Email sudah terdaftar")
                
                # Tautan Navigasi Kembali ke Login
                st.markdown("<div class='footer-nav-tk'>Already have an account? ", unsafe_allow_html=True)
                if st.button("Log In", key="tk_goto_login"):
                    st.session_state.halaman_aktif = "login"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Logo Kelompok di bagian paling bawah khusus halaman Sign Up
                st.markdown("<div class='logo-bottom-signup'>", unsafe_allow_html=True)
                if os.path.exists("logoo.PNG"):
                    st.image("logoo.PNG", width=120)
                st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# TAMPILAN 2: DASHBOARD UTAMA (HAPUS TOTAL DATA LAMA SETIAP KALI SCAN)
# ==============================================================================
else:
    st.markdown("<div class='dashboard-title-green'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>", unsafe_allow_html=True)
    
    _, r_out = st.columns([11.8, 1.2])
    with r_out:
        if st.button("Log Out", use_container_width=True):
            st.session_state.terautentikasi = False
            st.rerun()

    kolom_kiri, kolom_kanan = st.columns([1, 1.35])
    
    # ------------------ PANEL SCANNER (KIRI) ------------------
    with kolom_kiri:
        st.markdown("<div class='panel-box-tk'><div class='panel-box-title-tk'>Panel Input Scanner</div>", unsafe_allow_html=True)
        
        pilih_komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"], label_visibility="collapsed")
        st.write("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        
        # Preview Box
        st.markdown("<div class='preview-window-tk'>", unsafe_allow_html=True)
        if st.session_state.foto_terpilih is None:
            st.markdown("<span style='color:#555555; font-size:14px;'>[ Preview ]</span>", unsafe_allow_html=True)
        else:
            st.image(st.session_state.foto_terpilih, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        media_file = st.file_uploader("", type=["jpg","png","jpeg"], label_visibility="collapsed", key="tk_uploader")
        if media_file:
            st.session_state.foto_terpilih = Image.open(media_file)
            
        # Tombol-Tombol Aksi Berwarna Khas Tkinter-mu
        st.markdown("<div class='btn-blue-tk'>", unsafe_allow_html=True)
        st.button("Buka Kamera", use_container_width=True)
        st.markdown("</div><div class='btn-orange-tk' style='margin-top:8px;'>", unsafe_allow_html=True)
        st.button("Pilih Foto dari Galeri", use_container_width=True)
        st.markdown("</div><div class='btn-purple-tk' style='margin-top:8px;'>", unsafe_allow_html=True)
        st.button("Tandai Area Sayur (ROI)", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='btn-green-tk' style='margin-top:15px;'>", unsafe_allow_html=True)
        btn_analisis = st.button("Jalankan Analisis", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # LOGIKA KHUSUS: Bersihkan riwayat lama saat tombol ditekan
        if btn_analisis and st.session_state.foto_terpilih is not None:
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
                
                # --- AMAN: Hapus baris riwayat lama agar database tidak menumpuk ---
                cursor.execute("DELETE FROM riwayat_pindai")
                
                # Masukkan hasil pindai tunggal terbaru
                cursor.execute("INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?,?,?,?)", (nama, kondisi, f"{sisa} Hari", suhu_ideal))
                conn.commit()
                conn.close()
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ PANEL DASHBOARD MONITOR (KANAN) ------------------
    with kolom_kanan:
        st.markdown("<div class='panel-box-tk'><div class='panel-box-title-tk'>Dashboard</div>", unsafe_allow_html=True)
        
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_db = cursor.fetchall()
        conn.close()
        
        k_nama, k_kondisi, k_sisa, k_suhu = "-", "-", "-", "-"
        if data_db:
            k_nama, k_kondisi, k_sisa, k_suhu = data_db[0][1], data_db[0][2], data_db[0][3], data_db[0][4]
            
        st.markdown(f"""
        <div class='monitor-frame-tk'>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Hasil Pindai Sistem<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;====================<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Komoditas : {k_nama}<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Kondisi&nbsp;&nbsp;&nbsp;: {k_kondisi}<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Sisa&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {k_sisa}<br>
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Suhu Simpan : {k_suhu}
        </div>
        """, unsafe_allow_html=True)
        
        if data_db:
            import pandas as pd
            df_tabel = pd.DataFrame(data_db, columns=["ID", "Nama", "Kondisi", "Sisa", "Suhu"])
            st.dataframe(df_tabel, hide_index=True, use_container_width=True, height=290)
        else:
            st.markdown("<div style='border:1px solid #ccc; background:white; color:gray; text-align:center; padding:50px;'>Belum ada data riwayat.</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
