import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# ==============================================================================
# 1. KONFIGURASI DATABASE & DATA AWAL
# ==============================================================================
DB_LOGIN_PATH = "manajemen_akses.db"
DB_ANALISIS_PATH = "logistik_hortikultura.db"

# Inisialisasi Database jika belum ada tabelnya
def init_databases():
    # DB Login
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

    # DB Analisis Logistik
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
# 2. LOGIKA ANALISIS CITRA (OPENCV & HSV)
# ==============================================================================
def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    elif jenis == "Cabai": return "7 - 10 °C"
    elif jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_citra(cv_img, jenis):
    # Resize standar untuk pemrosesan
    cv_img = cv2.resize(cv_img, (400, 300))
    hsv = cv2.cvtColor(cv2.GaussianBlur(cv_img, (5, 5), 0), cv2.COLOR_BGR2HSV)
    
    # Masking Warna Komoditas
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
        return None, "Objek sayuran/cabai tidak terdeteksi dengan jelas di kamera.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return None, f"Salah pilihan komoditas! Sistem mendeteksi warna dominan {warna_dominan}, tetapi kamu memilih {jenis}.", -1

    mask_clean = mask_orange if jenis == "Wortel" else (mask_red if jenis == "Cabai" else mask_green)
    
    # Deteksi kerusakan/pembusukan (berdasarkan bagian gelap/layu)
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
# 3. ANTARMUKA WEB STREAMLIT
# ==============================================================================
st.set_page_config(page_title="Logistik Hortikultura", page_icon="🌱", layout="wide")

# Session State untuk menyimpan status login pengguna
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- HALAMAN AKSES (LOGIN & SIGN UP) ---
if not st.session_state.logged_in:
    st.title("🌱 Aplikasi Hortikultura Kelompok")
    
    # Menampilkan Logo Kelompok jika ada di repository GitHub-mu
    if os.path.exists("logoo.jpg"):
        st.image("logoo.jpg", width=120)
        
    tab1, tab2 = st.tabs(["Masuk Akun", "Daftar Baru"])
    
    with tab1:
        st.subheader("Login Pengguna")
        login_email = st.text_input("Username / Email", key="login_em")
        login_pass = st.text_input("Password", type="password", key="login_ps")
        if st.button("LOG IN", type="primary"):
            conn = sqlite3.connect(DB_LOGIN_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (login_email, login_pass))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                st.session_state.logged_in = True
                st.session_state.user_email = login_email
                st.success("Login Berhasil!")
                st.rerun()
            else:
                st.error("Username atau Password Salah!")
                
    with tab2:
        st.subheader("Buat Akun Baru")
        reg_email = st.text_input("Email Baru", key="reg_em")
        reg_pass = st.text_input("Password Baru", type="password", key="reg_ps")
        reg_confirm = st.text_input("Konfirmasi Password", type="password", key="reg_co")
        if st.button("Sign Up"):
            if reg_email == "" or reg_pass == "":
                st.warning("Data tidak boleh kosong!")
            elif reg_pass != reg_confirm:
                st.error("Konfirmasi password tidak cocok!")
            else:
                try:
                    conn = sqlite3.connect(DB_LOGIN_PATH)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO data_pengguna (email, password) VALUES (?, ?)", (reg_email, reg_pass))
                    conn.commit()
                    conn.close()
                    st.success("Akun berhasil dibuat! Silakan pindah ke tab 'Masuk Akun'.")
                except sqlite3.IntegrityError:
                    st.error("Email sudah terdaftar!")

# --- HALAMAN DASHBOARD LOGISTIK UTAMA ---
else:
    # Header Utama
    st.markdown("<div style='background-color:#1b5e20;padding:12px;border-radius:5px'><h2 style='color:white;text-align:center;margin:0;'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</h2></div>", unsafe_allow_html=True)
    
    # Tombol Logout di pojok kanan atas
    col_user, col_logout = st.columns([8, 2])
    col_user.write(f"Sesi Aktif: **{st.session_state.user_email}**")
    if col_logout.button("Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.rerun()

    st.write("---")
    
    col_kiri, col_kanan = st.columns([1, 1])
    
    with col_kiri:
        st.subheader("📸 Panel Input Scanner")
        komoditas_pilihan = st.selectbox("Pilih Komoditas", ["Wortel", "Cabai", "Brokoli"])
        
        # Pilihan Input Kamera atau Unggah File bawaan Streamlit (sangat stabil di HP/Laptop)
        metode_input = st.radio("Metode Pengambilan Gambar:", ["Gunakan Kamera Perangkat", "Unggah Foto dari Galeri"])
        
        file_gambar = None
        if metode_input == "Gunakan Kamera Perangkat":
            file_gambar = st.camera_input("Ambil Foto Komoditas")
        else:
            file_gambar = st.file_uploader("Pilih File Gambar", type=["jpg", "jpeg", "png", "bmp"])
            
        if file_gambar is not None:
            # Mengonversi file gambar ke format OpenCV BGR
            image_pil = Image.open(file_gambar)
            img_np = np.array(image_pil)
            # Jika gambar RGBA, ubah ke RGB dahulu sebelum ke BGR
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            if st.button("Jalankan Analisis Kualitas", type="primary", use_container_width=True):
                nama, kondisi, sisa = cek_kondisi_citra(img_cv, komoditas_pilihan)
                
                if sisa == -1:
                    st.error(kondisi)
                else:
                    suhu_rekomendasi = rekomendasi_suhu(nama)
                    sisa_hari = f"{sisa} Hari"
                    
                    # Simpan ke Database analisis logistik
                    conn = sqlite3.connect(DB_ANALISIS_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?, ?, ?, ?)",
                        (nama, kondisi, sisa_hari, suhu_rekomendasi)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Analisis selesai dan data berhasil direkam ke riwayat database!")

    with col_kanan:
        st.subheader("📊 Hasil Real-Time & Riwayat Logistik")
        
        # Mengambil data terbaru dari database logistik untuk ditampilkan
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_rows = cursor.fetchall()
        conn.close()
        
        if data_rows:
            # Tampilkan data paling baru sebagai ringkasan kartu di atas dashboard
            terbaru = data_rows[0]
            st.info(f"""
            **Hasil Pindai Sistem Terakhir:**
            * Komoditas: **{terbaru[1]}**
            * Kondisi Mutu: **{terbaru[2]}**
            * Estimasi Sisa Segar: **{terbaru[3]}**
            * Rekomendasi Suhu Simpan: **{terbaru[4]}**
            """)
        else:
            st.warning("Belum ada data pemindaian di dalam database.")
            
        # Tabel Riwayat Keseluruhan menggunakan tabel interaktif Streamlit
        st.write("**Tabel Riwayat Pemindaian Seluruh Komoditas:**")
        if data_rows:
            import pandas as pd
            df = pd.DataFrame(data_rows, columns=["ID", "Nama Komoditas", "Kondisi", "Sisa Segar", "Suhu Simpan"])
            st.dataframe(df, hide_index=True, use_container_width=True)
