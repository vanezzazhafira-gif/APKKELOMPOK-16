import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import os

# ==============================================================================
# 1. INISIALISASI DATABASE & LOGIKA SISTEM
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
    conn.commit()
    conn.close()

# Jalankan inisialisasi tabel saat aplikasi dimuat
init_databases()

def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    elif jenis == "Cabai": return "7 - 10 °C"
    elif jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_citra(cv_img, jenis):
    # Standarisasi ukuran gambar untuk pemrosesan HSV
    cv_img = cv2.resize(cv_img, (400, 300))
    hsv = cv2.cvtColor(cv2.GaussianBlur(cv_img, (5, 5), 0), cv2.COLOR_BGR2HSV)
    
    # Range Warna Masking (Orange, Merah, Hijau)
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

    # Validasi keberadaan objek di depan kamera
    if max(pct_orange, pct_red, pct_green) < 3:
        return None, "Objek sayuran tidak terdeteksi dengan jelas di area preview.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    # Validasi kesesuaian antara pilihan dropdown dengan fisik sayur
    if jenis != warna_dominan:
        return None, f"Salah komoditas! Kamera mendeteksi {warna_dominan}, mohon sesuaikan pilihan.", -1

    # Analisis tingkat kerusakan/pembusukan spot gelap & hilangnya saturasi warna
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

    # Penentuan Status Mutu Akhir
    if score >= 4: status, sisa = "BUSUK / RUSAK", 0
    elif score >= 2: status, sisa = "Kurang Segar", 2
    else: status, sisa = "Segar & Alami", 4

    return jenis, status, sisa

# ==============================================================================
# 2. KONFIGURASI HALAMAN & LAYOUT UTAMA
# ==============================================================================
st.set_page_config(page_title="Optimalisasi Logistik Pertanian", layout="wide")

# Manajemen Alur Halaman (Session State)
if "halaman" not in st.session_state:
    st.session_state.halaman = "login"
if "foto_input" not in st.session_state:
    st.session_state.foto_input = None

# CSS Pendukung untuk merapikan spasi default Streamlit
st.markdown("""
<style>
    div.block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. HALAMAN INTERFACE: LOG IN
# ==============================================================================
if st.session_state.halaman == "login":
    _, col_center, _ = st.columns([1, 1.3, 1])
    
    with col_center:
        # Menampilkan logo kelompok di bagian paling atas
        if os.path.exists("logoo.PNG"):
            st.image("logoo.PNG", width=110)
            
        st.title("Log In")
        st.write("Aplikasi Prediksi Kadaluwarsa Produk Hortikultura")
        st.write("---")
        
        in_user = st.text_input("Username / Email", placeholder="Masukkan username anda", key="log_user")
        in_pass = st.text_input("Password", placeholder="Masukkan password anda", type="password", key="log_pass")
        
        st.write("")
        if st.button("LOG IN", use_container_width=True):
            conn = sqlite3.connect(DB_LOGIN_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM data_pengguna WHERE email=? AND password=?", (in_user, in_pass))
            user_found = cursor.fetchone()
            conn.close()
            
            if user_found:
                st.session_state.halaman = "dashboard"
                st.rerun()
            else:
                st.error("Kombinasi Username atau Password salah!")
                
        st.write("")
        st.write("Have not account?")
        if st.button("Create Account", key="go_to_signup"):
            st.session_state.halaman = "signup"
            st.rerun()

# ==============================================================================
# 4. HALAMAN INTERFACE: SIGN UP
# ==============================================================================
elif st.session_state.halaman == "signup":
    _, col_center, _ = st.columns([1, 1.3, 1])
    
    with col_center:
        st.title("Sign Up")
        st.subheader("Create an account")
        st.write("---")
        
        reg_email = st.text_input("Email", placeholder="Masukkan email baru", key="reg_e")
        reg_pass1 = st.text_input("Password", placeholder="Buat kata sandi", type="password", key="reg_p1")
        reg_pass2 = st.text_input("Confirm Password", placeholder="Ulangi kata sandi", type="password", key="reg_p2")
        
        st.write("")
        if st.button("Sign Up", use_container_width=True):
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
                    st.success("Registrasi Berhasil! Silakan masuk menggunakan akun baru.")
                    st.session_state.halaman = "login"
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Email tersebut sudah terdaftar di sistem!")
                    
        st.write("")
        st.write("Already have an account?")
        if st.button("Log In", key="back_to_login"):
            st.session_state.halaman = "login"
            st.rerun()
            
        st.write("")
        if os.path.exists("logoo.PNG"):
            st.image("logoo.PNG", width=110)

# ==============================================================================
# 5. HALAMAN INTERFACE: DASHBOARD UTAMA MONITORING
# ==============================================================================
elif st.session_state.halaman == "dashboard":
    # Header bar hijau atas yang solid
    st.markdown("""
        <div style="background-color: #246329; padding: 12px; border-radius: 4px; text-align: center; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0; font-weight: bold; letter-spacing: 1px;">OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Penempatan Tombol Log Out di pojok kanan atas
    col_space, col_logout = st.columns([11, 1])
    with col_logout:
        if st.button("Log Out", use_container_width=True):
            st.session_state.foto_input = None
            st.session_state.halaman = "login"
            st.rerun()
            
    # Pembagian Dua Sub-Panel Utama (Scanner & Dashboard Hasil)
    panel_kiri, panel_kanan = st.columns([1, 1.3])
    
    # --- PANEL INPUT SCANNER (KIRI) ---
    with panel_kiri:
        st.markdown("### **Panel Input Scanner**")
        
        pilihan_sayur = st.selectbox("Komoditas:", ["Wortel", "Cabai", "Brokoli"], label_visibility="visible")
        
        # Area Container Kotak Preview Gambar
        with st.container(border=True):
            if st.session_state.foto_input is None:
                st.markdown("<div style='height: 250px; background-color: #e8e8e8; display: flex; align-items: center; justify-content: center; border-radius:4px; color:#555;'><B>[ Preview ]</B></div>", unsafe_allow_html=True)
            else:
                st.image(st.session_state.foto_input, use_container_width=True)
                
        # Penanganan Upload / Ambil File Gambar
        file_terunggah = st.file_uploader("Unggah berkas foto atau gambar sayur:", type=["jpg", "png", "jpeg"])
        if file_terunggah:
            st.session_state.foto_input = Image.open(file_terunggah)
            
        # Tombol Simulasi Aksi Scanner
        st.button("📸 Buka Kamera", use_container_width=True)
        st.button("📁 Pilih Foto dari Galeri", use_container_width=True)
        st.button("🎯 Tandai Area Sayur (ROI)", use_container_width=True)
        
        st.write("")
        btn_proses_analisis = st.button("🚀 Jalankan Analisis", use_container_width=True, type="primary")
        
        # Eksekusi Pemrosesan Citra Terpilih
        if btn_proses_analisis:
            if st.session_state.foto_input is None:
                st.warning("Mohon unggah atau masukkan foto sayuran terlebih dahulu!")
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
                    
                    # Manajemen Koneksi ke DB Analisis
                    conn = sqlite3.connect(DB_ANALISIS_PATH)
                    cursor = conn.cursor()
                    
                    # --- ATURAN KHUSUS: Hapus seluruh data lama agar tidak menumpuk ---
                    cursor.execute("DELETE FROM riwayat_pindai")
                    
                    # Masukkan satu record baru hasil analisis terkini
                    cursor.execute("""
                        INSERT INTO riwayat_pindai (komoditas, kondisi, sisa_segar, suhu_simpan)
                        VALUES (?, ?, ?, ?)
                    """, (nama, kondisi, f"{sisa_hari} Hari", suhu_ruang))
                    
                    conn.commit()
                    conn.close()
                    st.success("Analisis selesai! Data monitor diperbarui.")
                    st.rerun()

    # --- PANEL DASHBOARD MONITOR (KANAN) ---
    with panel_kanan:
        st.markdown("### **Dashboard**")
        
        # Mengambil baris data terbaru dari database logistik
        conn = sqlite3.connect(DB_ANALISIS_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id DESC")
        isi_tabel = cursor.fetchall()
        conn.close()
        
        v_nama, v_kondisi, v_sisa, v_suhu = "-", "-", "-", "-"
        if isi_tabel:
            v_nama, v_kondisi, v_sisa, v_suhu = isi_tabel[0][1], isi_tabel[0][2], isi_tabel[0][3], isi_tabel[0][4]
            
        # Bingkai Cetak Monospace Hasil Pindai Sistem
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
        
        # Merendering Tabel Log di bagian bawah layar
        if isi_tabel:
            import pandas as pd
            df_monitor = pd.DataFrame(isi_tabel, columns=["ID", "Nama", "Kondisi", "Sisa", "Suhu"])
            st.dataframe(df_monitor, hide_index=True, use_container_width=True)
        else:
            st.info("Belum ada riwayat pemindaian. Jalankan analisis di panel kiri untuk menampilkan data.")
