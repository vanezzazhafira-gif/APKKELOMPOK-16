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

# ==============================================================================
# CONFIG & KUSTOMISASI CSS TERBARU
# ==============================================================================
st.set_page_config(
    page_title="Logistik Hortikultura",
    page_icon="🌱",
    layout="wide"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"]{
    background: linear-gradient(135deg, #1b5e20, #4caf50);
}

.login-card{
    background: white;
    padding: 40px;
    border-radius: 20px;
    box-shadow: 0px 5px 25px rgba(0,0,0,0.3);
    color: black !important;
}

/* Memperbaiki warna input text agar terlihat jelas di dalam card putih */
.login-card div[data-baseweb="input"] {
    color: black !important;
}

.title-app{
    text-align: center;
    color: white;
    font-size: 34px;
    font-weight: bold;
    margin-bottom: 30px;
    margin-top: 50px;
}

.main-header{
    background: #ffffff;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
    color: #1b5e20;
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 20px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
}

.panel{
    background: white;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.15);
    color: black !important;
}

.result-box{
    background: #f4fbf4;
    padding: 20px;
    border-radius: 12px;
    border-left: 6px solid #1b5e20;
    color: black !important;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

if "terautentikasi" not in st.session_state:
    st.session_state.terautentikasi = False
if "user_aktif" not in st.session_state:
    st.session_state.user_aktif = ""

# ==============================================================================
# 1. HALAMAN LOGIN & SIGNUP (CARD DI TENGAH)
# ==============================================================================
if not st.session_state.terautentikasi:
    st.markdown(
        "<div class='title-app'>🌱 APLIKASI LOGISTIK HORTIKULTURA</div>",
        unsafe_allow_html=True
    )

    kiri, tengah, kanan = st.columns([1, 1.3, 1])

    with tengah:
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)

        menu = st.radio(
            "",
            ["Masuk Akun", "Daftar Akun Baru"],
            horizontal=True
        )

        if menu == "Masuk Akun":
            st.subheader("LOGIN")
            username_input = st.text_input("Username / Email")
            password_input = st.text_input("Password", type="password")

            if st.button("LOG IN", use_container_width=True, type="primary"):
                conn = sqlite3.connect(DB_LOGIN_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM data_pengguna WHERE email=? AND password=?",
                    (username_input, password_input)
                )
                user = cursor.fetchone()
                conn.close()

                if user:
                    st.session_state.terautentikasi = True
                    st.session_state.user_aktif = username_input
                    st.rerun()
                else:
                    st.error("Username atau Password Salah")
        else:
            st.subheader("SIGN UP")
            new_email = st.text_input("Email")
            new_pass = st.text_input("Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")

            if st.button("SIGN UP", use_container_width=True, type="primary"):
                if new_pass != confirm_pass:
                    st.error("Password tidak sama")
                else:
                    try:
                        conn = sqlite3.connect(DB_LOGIN_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO data_pengguna(email,password) VALUES (?,?)",
                            (new_email, new_pass)
                        )
                        conn.commit()
                        conn.close()
                        st.success("Akun berhasil dibuat, silakan pindah ke menu 'Masuk Akun'.")
                    except:
                        st.error("Email sudah digunakan")

        st.markdown("</div>", unsafe_allow_html=True)

# ==============================================================================
# 2. HALAMAN DASHBOARD UTAMA
# ==============================================================================
else:
    st.markdown("<div class='main-header'>OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>", unsafe_allow_html=True)
    
    # Tombol Logout dan Info User ditaruh di dalam container putih kecil agar serasi
    col_user, col_logout = st.columns([8, 2])
    with col_user:
        st.markdown(f"<span style='color: white; font-weight: bold;'>Pengguna aktif: {st.session_state.user_aktif}</span>", unsafe_allow_html=True)
    with col_logout:
        if st.button("Keluar Sesi", use_container_width=True):
            st.session_state.terautentikasi = False
            st.session_state.user_aktif = ""
            st.rerun()

    st.write("<br>", unsafe_allow_html=True)
    
    # Pembagian Kolom Baru Sesuai Layout Request [1, 1.4]
    kolom_kiri, kolom_kanan = st.columns([1, 1.4])
    
    # --- PANEL KIRI: SCANNER ---
    with kolom_kiri:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
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
            st.image(img_pil, caption="Preview Gambar", use_container_width=True)
            
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
                    st.success("Data pemindaian berhasil diproses!")
                    st.rerun()
                    
        st.markdown("</div>", unsafe_allow_html=True)

    # --- PANEL KANAN: DASHBOARD ---
    with kolom_kanan:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("📊 Dashboard")
        
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        data_db = cursor.fetchall()
        conn.close()
        
        if data_db:
            terbaru = data_db[0]
            st.markdown(f"""
            <div class='result-box'>
            <b style='font-size: 18px; color: #1b5e20;'>Hasil Pindai Sistem</b>
            <hr style='margin-top:5px; margin-bottom:10px; border-color: #1b5e20;'>
            Komoditas : <b>{terbaru[1]}</b><br>
            Kondisi : <b>{terbaru[2]}</b><br>
            Sisa Segar : <b>{terbaru[3]}</b><br>
            Suhu Simpan : <b>{terbaru[4]}</b>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Belum ada riwayat data di database.")
            
        st.write("<br><b>Tabel Logistik Riwayat Lengkap:</b>", unsafe_allow_html=True)
        if data_db:
            import pandas as pd
            df_tabel = pd.DataFrame(data_db, columns=["ID Pindai", "Nama", "Kondisi Mutu", "Sisa Hari", "Suhu Rekomendasi"])
            st.dataframe(df_tabel, hide_index=True, use_container_width=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
