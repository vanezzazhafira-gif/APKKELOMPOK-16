import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import tempfile

DB_LOGIN = "manajemen_akses.db"
DB_ANALISIS = "logistik_hortikultura.db"

# --- FUNGSI ANALISIS OPENCV DARI PROGRAMMU ---
def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    elif jenis == "Cabai": return "7 - 10 °C"
    elif jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_roi(path_gambar, jenis, roi=None):
    """
    Fungsi analisis citra sayuran asli milikmu yang membaca dari path file temporary.
    """
    img = cv2.imread(path_gambar)
    if img is None: return "Error", "Gagal load gambar", -1

    # Menggunakan seluruh area gambar jika roi tidak didefinisikan spesifik
    hsv = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2HSV)
    
    mask_orange = cv2.inRange(hsv, np.array([4, 65, 45]), np.array([22, 255, 255]))
    mask_red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    )
    mask_green = cv2.inRange(hsv, np.array([35, 45, 35]), np.array([85, 255, 255]))
    
    total_pixels = img.shape[0] * img.shape[1]
    pct_orange = (cv2.countNonZero(mask_orange) / total_pixels) * 100
    pct_red = (cv2.countNonZero(mask_red) / total_pixels) * 100
    pct_green = (cv2.countNonZero(mask_green) / total_pixels) * 100

    if max(pct_orange, pct_red, pct_green) < 5:
        return "Error", "Objek bukan sayuran yang dikenali.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return "Error", f"Salah komoditas! Terdeteksi {warna_dominan}, bukan {jenis}.", -1

    mask_clean = mask_orange if jenis == "Wortel" else (mask_red if jenis == "Cabai" else mask_green)
    if cv2.countNonZero(mask_clean) < 500:
        return "Error", "Objek sayuran tidak terdeteksi jelas.", -1

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

# --- LOGIKA DATABASE (LOGIN & SIGNUP) ---
def login(email, password):
    conn = sqlite3.connect(DB_LOGIN)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM data_pengguna WHERE email=? AND password=?",
        (email, password)
    )
    user = cur.fetchone()
    conn.close()
    return user

def signup(email, password):
    conn = sqlite3.connect(DB_LOGIN)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO data_pengguna(email,password) VALUES (?,?)",
        (email, password)
    )
    conn.commit()
    conn.close()

# --- INTERFACE UTAMA STREAMLIT ---
if "login" not in st.session_state:
    st.session_state["login"] = False

# JIKA BELUM LOGIN
if not st.session_state["login"]:
    menu = st.sidebar.selectbox("Navigasi", ["Login", "Sign Up"])
    
    if menu == "Login":
        st.title("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if login(email, password):
                st.session_state["login"] = True
                st.success("Login Berhasil")
                st.rerun()
            else:
                st.error("Email atau Password Salah")
                
    elif menu == "Sign Up":
        st.title("Sign Up")
        new_email = st.text_input("Email Baru")
        new_password = st.text_input("Password Baru", type="password")
        
        if st.button("Daftar Akun"):
            if new_email != "" and new_password != "":
                signup(new_email, new_password)
                st.success("Registrasi Berhasil! Silakan pindah ke menu Login.")
            else:
                st.error("Form tidak boleh kosong.")

# JIKA SUDAH LOGIN (MASUK DASHBOARD)
else:
    st.title("🥦 Aplikasi Logistik Hortikultura")
    
    if st.sidebar.button("Logout"):
        st.session_state["login"] = False
        st.rerun()

    komoditas = st.selectbox("Pilih Komoditas Sayuran", ["Wortel", "Cabai", "Brokoli"])
    
    uploaded_file = st.file_uploader(
        "Upload Gambar Sayuran",
        type=["jpg", "jpeg", "png"]
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(
            image,
            caption="Preview Gambar",
            use_container_width=True
        )

        # TOMBOL ANALISIS SESUAI KERANGKA PERINTAHMU
        if st.button("Analisis"):
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".jpg"
            ) as tmp:
                tmp.write(uploaded_file.getbuffer())
                path = tmp.name

            img = cv2.imread(path)
            
            if img is not None:
                roi = (0, 0, img.shape[1], img.shape[0])
                
                # Memanggil fungsi analisis bawaanmu
                nama, kondisi, sisa = cek_kondisi_roi(
                    path,
                    komoditas,
                    roi
                )

                if sisa == -1:
                    st.error(f"Gagal Analisis: {kondisi}")
                else:
                    suhu = rekomendasi_suhu(nama)

                    st.success("Analisis Selesai")
                    st.write("Komoditas :", nama)
                    st.write("Kondisi :", kondisi)
                    st.write("Sisa Segar :", f"{sisa} Hari")
                    st.write("Suhu Simpan :", suhu)

                    # SIMPAN KE DATABASE SEMENTARA SESUAI PETUNJUK
                    conn = sqlite3.connect(DB_ANALISIS)
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO riwayat_pindai
                        (komoditas,kondisi,sisa_segar,suhu_simpan)
                        VALUES (?,?,?,?)
                        """,
                        (nama, kondisi, f"{sisa} Hari", suhu)
                    )
                    conn.commit()
                    conn.close()
            else:
                st.error("File gambar rusak atau tidak dapat dibaca oleh OpenCV.")

    # --- TAMPILKAN RIWAYAT ---
    try:
        conn = sqlite3.connect(DB_ANALISIS)
        data = conn.execute("SELECT * FROM riwayat_pindai ORDER BY id DESC").fetchall()
        conn.close()

        st.subheader("Riwayat Analisis")
        if data:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("Belum ada riwayat analisis data.")
    except sqlite3.OperationalError:
        st.info("Database riwayat kosong atau tabel belum dibuat.")