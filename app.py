import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
import base64

# Mengatur konfigurasi dasar page Streamlit
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
# STATE MANAGEMENT & CLEAN STYLING
# =========================================================
if "login" not in st.session_state: st.session_state.login = False
if "page" not in st.session_state: st.session_state.page = "Login"
if "hasil" not in st.session_state:
    st.session_state.hasil = {"komoditas": "-", "kondisi": "-", "sisa": "-", "suhu": "-"}
if "riwayat_session" not in st.session_state: st.session_state.riwayat_session = []

# CSS Amankan tampilan Terminal Output Dashboard agar rapi
st.markdown("""
<style>
    header[data-testid="stHeader"] {display:none;}
    .result-terminal {
        background-color: #f8f9fa;
        border: 1px solid #dcdcdc;
        border-left: 5px solid #145d1f;
        padding: 15px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 16px;
        color: black;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# ROUTING HALAMAN
# =========================================================

# --- HALAMAN LOGIN (DIPERBAIKI AGAR TIDAK HANCUR) ---
if not st.session_state.login and st.session_state.page == "Login":
    # Membuat container terpusat yang rapi tanpa CSS luar yang merusak layout
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.markdown("<h2 style='text-align: center; color: black;'>Log In</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Aplikasi Prediksi Kadaluwarsa Produk Hortikultura</p>", unsafe_allow_html=True)
        
        email = st.text_input("Username / Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        
        st.write("")
        if st.button("LOG IN", use_container_width=True, type="primary"):
            if login(email, password): 
                st.session_state.login = True
                st.rerun()
            else: 
                st.error("Username atau Password Salah")
                
        st.write("---")
        st.write("Belum punya akun?")
        if st.button("Create Account", use_container_width=True): 
            st.session_state.page = "Sign Up"
            st.rerun()

# --- HALAMAN SIGN UP (DIPERBAIKI AGAR TIDAK HANCUR) ---
elif not st.session_state.login and st.session_state.page == "Sign Up":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.markdown("<h2 style='text-align: center; color: black;'>Sign Up</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Buat akun baru anda</p>", unsafe_allow_html=True)
        
        new_email = st.text_input("Email Baru", key="signup_email")
        new_password = st.text_input("Password Baru", type="password", key="signup_pass")
        confirm = st.text_input("Konfirmasi Password", type="password", key="signup_confirm")
        
        st.write("")
        if st.button("Daftar Akun", use_container_width=True, type="primary"):
            if new_password == confirm:
                if signup(new_email, new_password):
                    st.success("Akun berhasil dibuat! Silakan Log In.")
                    st.session_state.page = "Login"
                    st.rerun()
                else:
                    st.error("Email sudah terdaftar atau terjadi kesalahan database.")
            else: 
                st.error("Konfirmasi password tidak cocok.")
                
        st.write("---")
        if st.button("Kembali ke Halaman Log In", use_container_width=True):
            st.session_state.page = "Login"
            st.rerun()

# =========================================================
# DASHBOARD UTAMA (BISA DI JALANKAN DI LAPTOP & HP)
# =========================================================
else:
    # Header Atas Hijau sesuai mock-up Qt Designer kamu
    st.markdown("<h2 style='text-align: center; color: #145d1f; background-color: #e2f0d9; padding: 10px; border-radius: 4px; font-family: sans-serif;'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</h2>", unsafe_allow_html=True)
    st.write("---")

    # Pembagian 2 Kolom Utama (Kiri untuk Panel Input, Kanan untuk Dashboard)
    col_kiri, col_kanan = st.columns([1, 1.3], gap="large")

    # -----------------------------------------------------
    # PANEL KIRI: INPUT SCANNER
    # -----------------------------------------------------
    with col_kiri:
        with st.expander("📺 Panel Input Scanner", expanded=True):
            komoditas = st.selectbox("Pilih Komoditas:", ["Wortel", "Cabai", "Brokoli"])
            
            st.write("**Pilih Metode Ambil Gambar:**")
            opsi_input = st.radio("Pilihan sumber:", ["Kamera Laptop / HP", "Unggah Gambar dari File"], label_visibility="collapsed")
            
            active_file = None
            if opsi_input == "Kamera Laptop / HP":
                active_file = st.camera_input("Ambil foto objek")
            else:
                active_file = st.file_uploader("Pilih file foto (.jpg, .png)", type=["jpg", "jpeg", "png"])

            # Kotak Preview Gambar
            st.write("**Preview Gambar:**")
            if active_file:
                st.image(active_file, use_container_width=True)
            else:
                st.info("Gambar belum dimasukkan.")

            st.write("---")
            jalankan_analisis = st.button("🟢 Jalankan Analisis Data", use_container_width=True, type="primary")

    # -----------------------------------------------------
    # PANEL KANAN: DASHBOARD HASIL & TABEL
    # -----------------------------------------------------
    with col_kanan:
        with st.expander("📊 Dashboard Hasil Pemindaian", expanded=True):
            
            # Proses Hitung Algoritma OpenCV
            if jalankan_analisis:
                if active_file is None:
                    st.warning("⚠️ Mohon ambil foto atau unggah gambar terlebih dahulu!")
                else:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        tmp_file.write(active_file.getbuffer())
                        path_img = tmp_file.name
                    
                    nama_veg, kond_veg, sisa_hari = cek_kondisi_roi(path_img, komoditas)
                    
                    if sisa_hari == -1:
                        st.session_state.hasil = {
                            "komoditas": "Tidak Dikenali",
                            "kondisi": kond_veg,
                            "sisa": "-",
                            "suhu": "-"
                        }
                    else:
                        suhu_rekom = rekomendasi_suhu(nama_veg)
                        string_sisa = f"{sisa_hari} Hari"
                        st.session_state.hasil = {
                            "komoditas": nama_veg,
                            "kondisi": kond_veg,
                            "sisa": string_sisa,
                            "suhu": suhu_rekom
                        }
                        
                        # Simpan Ke SQLite Riwayat
                        try:
                            conn = sqlite3.connect(DB_ANALISIS)
                            cur = conn.cursor()
                            cur.execute("INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?, ?, ?, ?)", 
                                        (nama_veg, kond_veg, string_sisa, suhu_rekom))
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            st.error(f"Gagal simpan DB: {e}")
                        
                        # Masukkan ke riwayat tabel visual
                        new_id = len(st.session_state.riwayat_session) + 1
                        st.session_state.riwayat_session.append((new_id, nama_veg, kond_veg, string_sisa, suhu_rekom))

            # Cetak Output Terminal Monospace (Sesuai Gambar Asli)
            res = st.session_state.hasil
            text_output = f"""Hasil Pindai Sistem
===================================
Komoditas Terdeteksi : {res["komoditas"]}
Kondisi Kematangan   : {res["kondisi"]}
Estimasi Sisa Segar  : {res["sisa"]}
Suhu Penyimpanan     : {res["suhu"]}"""
            
            st.markdown(f'<div class="result-terminal">{text_output}</div>', unsafe_allow_html=True)

        st.write("")
        
        with st.expander("📜 Riwayat Distribusi Logistik", expanded=True):
            if len(st.session_state.riwayat_session) > 0:
                st.dataframe(
                    st.session_state.riwayat_session,
                    use_container_width=True,
                    hide_index=True,
                    column_config={0: "ID", 1: "Nama Komoditas", 2: "Kondisi", 3: "Masa Simpan", 4: "Suhu"}
                )
            else:
                st.caption("Belum ada riwayat data.")
