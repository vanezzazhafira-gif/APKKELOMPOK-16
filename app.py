import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# ==============================================================================
# INITIALIZATION & DATABASE LOGIC (RESET AUTOMATICALLY)
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
# STYLING INTERFACE (CLEAN LIGHT THEME ONLY)
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", page_icon="🌱", layout="wide")

st.markdown("""
<style>
/* Sembunyikan elemen dekorasi default Streamlit */
header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] { visibility: hidden !important; height: 0px !important; }

/* Set canvas dasar menjadi abu-abu terang */
.stApp { background-color: #f2f4f7 !important; }

/* Desain kolom input teks di dalam kertas */
div[data-baseweb="input"] {
    background-color: #ffffff !important;
    border: 1px solid #cccccc !important;
    border-radius: 6px !important;
}
input {
    color: #111111 !important;
    font-size: 15px !important;
}
input::placeholder {
    color: #888888 !important;
}

/* Tipografi Header Form */
.form-main-title { text-align: center !important; color: #111111 !important; font-size: 26px !important; font-weight: 700 !important; margin: 10px 0 2px 0 !important; }
.form-sub-title { text-align: center !important; color: #555555 !important; font-size: 13px !important; font-weight: 500 !important; margin-bottom: 20px !important; }

/* Desain Tombol Standar Form */
div[data-testid="stMainBlockContainer"] button {
    background-color: #f0f0f0 !important;
    color: #222222 !important;
    border: 1px solid #b5b5b5 !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
}
div[data-testid="stMainBlockContainer"] button:hover {
    background-color: #e2e8f0 !important;
    border-color: #64748b !important;
}

/* Navigasi Pindah Halaman Kanan Bawah */
.footer-link-container { text-align: right !important; margin-top: 15px; }
.footer-link-container button { background: none !important; border: none !important; color: #0284c7 !important; text-decoration: underline !important; padding: 0 !important; font-weight: 400 !important; }

/* DASHBOARD LAYOUT STYLING */
.dashboard-title-bar { background-color: #1e3a1f !important; padding: 12px !important; text-align: center !important; color: white !important; font-size: 20px !important; font-weight: bold !important; margin-bottom: 20px; border-radius: 4px; }
.custom-card { background-color: #ffffff !important; border: 1px solid #d1d5db !important; border-radius: 6px !important; padding: 22px !important; min-height: 560px; }
.card-header-label { font-weight: 700 !important; font-size: 15px !important; color: #1f2937 !important; margin-bottom: 10px; display: block; }
.terminal-output { font-family: monospace !important; font-size: 14px !important; color: #111111 !important; background-color: #f9fafb !important; border: 1px dashed #9ca3af !important; padding: 12px; line-height: 1.6; margin-bottom: 15px; }
.submit-green-btn button { background-color: #16a34a !important; color: white !important; border: 1px solid #15803d !important; font-weight: bold !important; }
.submit-green-btn button:hover { background-color: #15803d !important; }
</style>
""", unsafe_allow_html=True)

if "terautentikasi" not in st.session_state:
    st.session_state.terautentikasi = False
if "halaman_aktif" not in st.session_state:
    st.session_state.halaman_aktif = "login"
if "foto_terpilih" not in st.session_state:
    st.session_state.foto_terpilih = None

# ==============================================================================
# SCREEN 1: KOTAK AUTHENTICATION (LOGIN & SIGN UP SECURELY CONTAINERIZED)
# ==============================================================================
if not st.session_state.terautentikasi:
    # Membuat grid kolom agar posisi kotak berada tepat di tengah halaman deskop
    _, tengah_kertas, _ = st.columns([1, 1.1, 1])
    
    with tengah_kertas:
        # PENGGUNAAN BORDER=TRUE: Menjamin seluruh isi masuk ke satu kertas putih utuh!
        with st.container(border=True):
            
            # --- SUB-HALAMAN: LOGIN ---
            if st.session_state.halaman_aktif == "login":
                # 1. Logo Kelompok paling atas, dikecilkan (width=160), otomatis di dalam kertas
                if os.path.exists("logoo.PNG"):
                    _, col_logo, _ = st.columns([1, 2.5, 1])
                    with col_logo:
                        st.image("logoo.PNG", width=160)
                else:
                    st.warning("File logoo.PNG tidak ditemukan di root folder.")
                
                # 2. Judul form login
                st.markdown("<div class='form-main-title'>Log In</div>", unsafe_allow_html=True)
                st.markdown("<div class='form-sub-title'>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</div>", unsafe_allow_html=True)
                
                # 3. Form input email & password berurutan ke bawah
                user_mail = st.text_input("Username", placeholder="Username / Email", label_visibility="collapsed", key="in_user")
                st.write("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                user_pass = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed", key="in_pass")
                st.write("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                
                # 4. Tombol aksi kirim data login
                _, col_btn_log, _ = st.columns([1, 1.5, 1])
                with col_btn_log:
                    btn_login = st.button("LOG IN", use_container_width=True)
                    
                if btn_login:
                    conn = sqlite3.connect(DB_LOGIN_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (user_mail, user_pass))
                    record = cursor.fetchone()
                    conn.close()
                    if record:
                        st.session_state.terautentikasi = True
                        st.rerun()
                    else:
                        st.error("Kredensial salah, silakan periksa kembali.")
                
                # 5. Navigasi buat akun baru (Pojok Kanan Bawah Kertas)
                st.markdown("<div class='footer-link-container'>", unsafe_allow_html=True)
                if st.button("Create Account", key="link_signup"):
                    st.session_state.halaman_aktif = "signup"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # --- SUB-HALAMAN: SIGN UP ---
            else:
                # 1. Logo Kelompok paling atas, dikecilkan (width=160), otomatis di dalam kertas
                if os.path.exists("logoo.PNG"):
                    _, col_logo, _ = st.columns([1, 2.5, 1])
                    with col_logo:
                        st.image("logoo.PNG", width=160)
                
                # 2. Judul form register
                st.markdown("<div class='form-main-title'>Sign Up</div>", unsafe_allow_html=True)
                st.markdown("<div class='form-sub-title'>Buat akun akses baru sistem</div>", unsafe_allow_html=True)
                
                # 3. Input element fields
                reg_email = st.text_input("Email", placeholder="Masukkan Email", label_visibility="collapsed", key="su_mail")
                st.write("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                reg_pass = st.text_input("Password", placeholder="Masukkan Password", type="password", label_visibility="collapsed", key="su_pass")
                st.write("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                reg_confirm = st.text_input("Confirm Password", placeholder="Konfirmasi Password", type="password", label_visibility="collapsed", key="su_conf")
                st.write("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                
                # 4. Button eksekusi simpan akun baru
                _, col_btn_sign, _ = st.columns([1, 1.5, 1])
                with col_btn_sign:
                    btn_signup = st.button("Sign Up", use_container_width=True)
                    
                if btn_signup:
                    if reg_pass != reg_confirm:
                        st.error("Konfirmasi password tidak cocok.")
                    elif reg_email == "" or reg_pass == "":
                        st.warning("Data form tidak boleh dikosongkan.")
                    else:
                        try:
                            conn = sqlite3.connect(DB_LOGIN_PATH)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO data_pengguna(email,password) VALUES (?,?)", (reg_email, reg_pass))
                            conn.commit()
                            conn.close()
                            st.success("Registrasi berhasil! Silakan masuk.")
                            st.session_state.halaman_aktif = "login"
                            st.rerun()
                        except:
                            st.error("Alamat email tersebut sudah terdaftar.")
                
                # 5. Navigasi kembali ke halaman Login
                st.markdown("<div class='footer-link-container'>", unsafe_allow_html=True)
                if st.button("Log In", key="link_login"):
                    st.session_state.halaman_aktif = "login"
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# SCREEN 2: MAIN DASHBOARD CORE (WIPES PREVIOUS RUNS UPON EXECUTION)
# ==============================================================================
else:
    st.markdown("<div class='dashboard-title-bar'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>", unsafe_allow_html=True)
    
    col_space, col_logout = st.columns([11.8, 1.2])
    with col_logout:
        if st.button("Log Out", use_container_width=True):
            st.session_state.terautentikasi = False
            st.rerun()

    kiri_panel, kanan_panel = st.columns([1, 1.35])
    
    # ------------------ SEKTOR KIRI: CONTROLLER SCANNER ------------------
    with kiri_panel:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("<span class='card-header-label'>Panel Input Scanner</span>", unsafe_allow_html=True)
        
        pilih_komoditas = st.selectbox("Komoditas", ["Wortel", "Cabai", "Brokoli"], label_visibility="visible")
        
        st.write("<p style='font-weight:600; margin-top:10px; margin-bottom:4px; color:#374151;'>Preview Gambar</p>", unsafe_allow_html=True)
        st.markdown("<div style='background-color:#e5e7eb; border:1px solid #d1d5db; height:180px; width:100%; display:flex; align-items:center; justify-content:center; overflow:hidden; margin-bottom:12px; border-radius:4px;'>", unsafe_allow_html=True)
        if st.session_state.foto_terpilih is None:
            st.markdown("<span style='color:#6b7280; font-size:14px;'>[ Preview Gambar ]</span>", unsafe_allow_html=True)
        else:
            st.image(st.session_state.foto_terpilih, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        media_input = st.file_uploader("Upload Image", type=["jpg","png","jpeg"], label_visibility="collapsed", key="file_scanner")
        if media_input:
            st.session_state.foto_terpilih = Image.open(media_input)
            
        st.button("Buka Kamera", use_container_width=True)
        st.button("Pilih Foto", use_container_width=True)
        st.button("Pilih ROI", use_container_width=True)
        
        st.markdown("<div class='submit-green-btn' style='margin-top:12px;'>", unsafe_allow_html=True)
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
                
                # --- SYNC KEINGINAN: BERSIHKAN TOTAL DATA ANALISIS LAMA SEBELUM INPUT ---
                cursor.execute("DELETE FROM riwayat_pindai")
                
                # Tulis data pindai tunggal paling baru
                cursor.execute("INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?,?,?,?)", (nama, kondisi, f"{sisa} Hari", suhu_ideal))
                conn.commit()
                conn.close()
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ SEKTOR KANAN: MONITOR MONITORING ------------------
    with kanan_panel:
        st.markdown("<div class='custom-card'>", unsafe_allow_html=True)
        st.markdown("<span class='card-header-label'>Dashboard Monitoring</span>", unsafe_allow_html=True)
        
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_db = cursor.fetchall()
        conn.close()
        
        k_nama, k_kondisi, k_sisa, k_suhu = "-", "-", "-", "-"
        if data_db:
            k_nama, k_kondisi, k_sisa, k_suhu = data_db[0][1], data_db[0][2], data_db[0][3], data_db[0][4]
            
        st.markdown(f"""
        <div class='terminal-output'>
            Hasil Pindai Sistem Terbaru<br>
            -------------------------------------<br>
            Komoditas     : {k_nama}<br>
            Kondisi Fisik : {k_kondisi}<br>
            Sisa Segar    : {k_sisa}<br>
            Suhu Simpan   : {k_suhu}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='font-weight:600; font-size:14px; color:#374151; margin-bottom:6px;'>Tabel Hasil Pindai Terkini</p>", unsafe_allow_html=True)
        if data_db:
            import pandas as pd
            df_tabel = pd.DataFrame(data_db, columns=["ID", "Nama Komoditas", "Kondisi", "Estimasi Sisa", "Suhu Rekomendasi"])
            st.dataframe(df_tabel, hide_index=True, use_container_width=True, height=240)
        else:
            st.markdown("<div style='border:1px dashed #d1d5db; background:#f9fafb; color:#6b7280; text-align:center; padding:50px; font-size:14px; border-radius:4px;'>Belum ada data analisis. Silakan jalankan deteksi sayuran baru.</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
