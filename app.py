import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# Atur nama database sesuai yang ada di GitHub kamu
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

st.set_page_config(page_title="Logistik Hortikultura", page_icon="🌱", layout="wide")

if "terautentikasi" not in st.session_state:
    st.session_state.terautentikasi = False
if "user_aktif" not in st.session_state:
    st.session_state.user_aktif = ""

if not st.session_state.terautentikasi:
    st.title("🌱 Aplikasi Logistik Hortikultura")
    
    # Sesuaikan dengan nama file logomu di GitHub (logoo.PNG)
    if os.path.exists("logoo.PNG"):
        st.image("logoo.PNG", width=110)
        
    pilihan_tab = st.sidebar.radio("Navigasi Akses:", ["Masuk Akun", "Daftar Akun Baru"])
    
    if pilihan_tab == "Masuk Akun":
        st.subheader("Login Form")
        username_input = st.text_input("Username / Email")
        password_input = st.text_input("Password", type="password")
        
        if st.button("LOG IN", type="primary"):
            conn = sqlite3.connect(DB_LOGIN_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (username_input, password_input))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                st.session_state.terautentikasi = True
                st.session_state.user_aktif = username_input
                st.success("Selamat Datang! Login Berhasil.")
                st.rerun()
            else:
                st.error("Maaf, Username atau Password salah!")
                
    elif pilihan_tab == "Daftar Akun Baru":
        st.subheader("Sign Up Form")
        new_email = st.text_input("Masukkan Email")
        new_pass = st.text_input("Masukkan Password", type="password")
        confirm_pass = st.text_input("Konfirmasi Password", type="password")
        
        if st.button("Register Akun"):
            if new_email == "" or new_pass == "":
                st.warning("Form registrasi tidak boleh kosong!")
            elif new_pass != confirm_pass:
                st.error("Konfirmasi password tidak cocok!")
            else:
                try:
                    conn = sqlite3.connect(DB_LOGIN_PATH)
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO data_pengguna (email, password) VALUES (?, ?)", (new_email, new_pass))
                    conn.commit()
                    conn.close()
                    st.success("Akun sukses dibuat! Silakan pindah ke menu 'Masuk Akun'.")
                except sqlite3.IntegrityError:
                    st.error("Email tersebut sudah terdaftar sebelumnya!")

else:
    st.markdown("<div style='background-color:#1b5e20;padding:12px;border-radius:4px'><h2 style='color:white;text-align:center;margin:0;'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</h2></div>", unsafe_allow_html=True)
    
    col_user, col_logout = st.columns([8, 2])
    col_user.write(f"Pengguna aktif: **{st.session_state.user_aktif}**")
    if col_logout.button("Keluar Sesi / Log Out", use_container_width=True):
        st.session_state.terautentikasi = False
        st.session_state.user_aktif = ""
        st.rerun()

    st.write("---")
    kolom_kiri, kolom_kanan = st.columns([1, 1])
    
    with kolom_kiri:
        st.subheader("📸 Panel Input Scanner")
        pilih_komoditas = st.selectbox("Komoditas Sayuran:", ["Wortel", "Cabai", "Brokoli"])
        opsi_kamera = st.radio("Sumber Input Citra:", ["Gunakan Kamera HP/Laptop (Live)", "Unggah File Foto dari Galeri"])
        
        file_media = None
        if opsi_kamera == "Gunakan Kamera HP/Laptop (Live)":
            file_media = st.camera_input("Arahkan sayuran ke kamera depan")
        else:
            file_media = st.file_uploader("Upload Foto Sayur", type=["jpg", "jpeg", "png", "bmp"])
            
        if file_media is not None:
            img_pil = Image.open(file_media)
            img_np = np.array(img_pil)
            if len(img_np.shape) == 3 and img_np.shape[2] == 4:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2RGB)
            img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
            
            if st.button("Jalankan Analisis Kualitas", type="primary", use_container_width=True):
                nama, kondisi, sisa = cek_kondisi_citra(img_cv, pilih_komoditas)
                if sisa == -1:
                    st.error(kondisi)
                else:
                    suhu_ideal = rekomendasi_suhu(nama)
                    sisa_hari = f"{sisa} Hari"
                    
                    conn = sqlite3.connect(DB_ANALISIS_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan) VALUES (?,?,?,?)",
                        (nama, kondisi, sisa_hari, suhu_ideal)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Data pemindaian berhasil diproses dan direkam!")

    with kolom_kanan:
        st.subheader("📊 Dashboard Utama & Riwayat")
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_db = cursor.fetchall()
        conn.close()
        
        if data_db:
            terbaru = data_db[0]
            st.info(f"""
            **Hasil Pindai Sistem Paling Baru:**
            * Nama Komoditas : **{terbaru[1]}**
            * Kondisi Fisik : **{terbaru[2]}**
            * Estimasi Sisa Segar : **{terbaru[3]}**
            * Batas Suhu Simpan : **{terbaru[4]}**
            """)
        else:
            st.warning("Belum ada riwayat data di database.")
            
        st.write("**Tabel Logistik Riwayat Lengkap:**")
        if data_db:
            import pandas as pd
            df_tabel = pd.DataFrame(data_db, columns=["ID Pindai", "Nama", "Kondisi Mutu", "Sisa Hari", "Suhu Rekomendasi"])
            st.dataframe(df_tabel, hide_index=True, use_container_width=True)
