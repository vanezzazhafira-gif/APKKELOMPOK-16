import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import tempfile

st.set_page_config(page_title="Aplikasi Web Hortikultura", layout="wide")

DB_LOGIN = "manajemen_akses.db"
DB_ANALISIS = "logistik_hortikultura.db"

def rekomendasi_suhu(jenis):
    if jenis == "Wortel": return "0 - 4 °C"
    elif jenis == "Cabai": return "7 - 10 °C"
    elif jenis == "Brokoli": return "0 - 2 °C"
    return "-"

def cek_kondisi_roi(path_gambar, jenis):
    img = cv2.imread(path_gambar)
    if img is None:
        return "Error", "Gagal load gambar", -1

    hsv = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2HSV)

    mask_orange = cv2.inRange(hsv, np.array([4, 65, 45]), np.array([22, 255, 255]))
    mask_red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255])),
        cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    )
    mask_green = cv2.inRange(hsv, np.array([35, 45, 35]), np.array([85, 255, 255]))

    total_pixels = img.shape[0] * img.shape[1]
    pct_orange = cv2.countNonZero(mask_orange) / total_pixels * 100
    pct_red = cv2.countNonZero(mask_red) / total_pixels * 100
    pct_green = cv2.countNonZero(mask_green) / total_pixels * 100

    if max(pct_orange, pct_red, pct_green) < 5:
        return "Error", "Objek bukan sayuran yang dikenali.", -1

    d = {"Wortel": pct_orange, "Cabai": pct_red, "Brokoli": pct_green}
    warna_dominan = max(d, key=d.get)

    if jenis != warna_dominan:
        return "Error", f"Salah komoditas! Terdeteksi {warna_dominan}, bukan {jenis}.", -1

    mask_clean = mask_orange if jenis == "Wortel" else mask_red if jenis == "Cabai" else mask_green

    damage_pct = (
        cv2.countNonZero(
            cv2.bitwise_and(
                cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 70])),
                mask_clean
            )
        ) / max(cv2.countNonZero(mask_clean), 1)
    ) * 100

    yellow_pct = (
        cv2.countNonZero(
            cv2.bitwise_and(
                cv2.inRange(hsv, np.array([18, 40, 40]), np.array([40, 255, 255])),
                mask_clean
            )
        ) / max(cv2.countNonZero(mask_clean), 1)
    ) * 100

    mean_sat = np.mean(hsv[:, :, 1])

    score = 0
    if damage_pct > 10: score += 4
    elif damage_pct > 3: score += 2
    if jenis in ["Brokoli", "Cabai"] and yellow_pct > 15: score += 2
    if mean_sat < 60: score += 2
    elif mean_sat < 90: score += 1

    if score >= 4:
        status, sisa = "BUSUK / RUSAK", 0
    elif score >= 2:
        status, sisa = "Kurang Segar", 2
    else:
        status, sisa = "Segar & Alami", 4

    return jenis, status, sisa

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

st.markdown("""
<style>
.stApp {
    background-color: #f2f2f2;
}

.block-container {
    padding-top: 1.5rem;
    max-width: 1120px;
}

.login-card, .signup-card {
    background: white;
    border-radius: 8px;
    padding: 55px 70px;
    max-width: 540px;
    margin: auto;
    box-shadow: 0 0 8px rgba(0,0,0,0.18);
    text-align: center;
}

.login-title, .signup-title {
    font-size: 42px;
    font-weight: 800;
    color: black;
    text-align: center;
    margin-bottom: 10px;
}

.login-subtitle, .signup-subtitle {
    font-size: 20px;
    font-weight: 700;
    color: #315f38;
    text-align: center;
    margin-bottom: 35px;
}

.green-circle-top {
    position: fixed;
    right: -120px;
    top: 70px;
    width: 360px;
    height: 360px;
    background: #3f7d32;
    border-radius: 50%;
    z-index: 0;
}

.green-circle-bottom {
    position: fixed;
    left: -120px;
    bottom: -160px;
    width: 360px;
    height: 360px;
    background: #3f7d32;
    border-radius: 50%;
    z-index: 0;
}

.dashboard-header {
    background-color: #145d1f;
    color: white;
    padding: 14px;
    text-align: center;
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 10px;
}

.panel-box {
    background: white;
    border: 1px solid #999;
    padding: 12px;
    min-height: 560px;
}

.preview-box {
    background: #ddd;
    height: 335px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 8px;
    color: black;
}

.result-box {
    background: #f7f7f7;
    padding: 18px;
    font-family: monospace;
    font-size: 16px;
    white-space: pre-line;
    border-bottom: 1px solid #aaa;
    margin-bottom: 0;
}

div.stButton > button {
    width: 100%;
    border-radius: 0px;
    color: white;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

if "login" not in st.session_state:
    st.session_state["login"] = False

if "page" not in st.session_state:
    st.session_state["page"] = "Login"

if "hasil" not in st.session_state:
    st.session_state["hasil"] = {
        "komoditas": "-",
        "kondisi": "-",
        "sisa": "-",
        "suhu": "-"
    }

if not st.session_state["login"]:
    menu = st.sidebar.selectbox("Navigasi", ["Login", "Sign Up"])

    if menu == "Login":
        st.markdown('<div class="green-circle-top"></div>', unsafe_allow_html=True)
        st.markdown('<div class="green-circle-bottom"></div>', unsafe_allow_html=True)

        st.markdown('<div class="login-title">Log In</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="login-subtitle">Aplikasi Prediksi Kadaluwarsa Produk Holtikultura</div>',
            unsafe_allow_html=True
        )

        email = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("LOG IN"):
            if login(email, password):
                st.session_state["login"] = True
                st.success("Login Berhasil")
                st.rerun()
            else:
                st.error("Username atau Password Salah")

        st.markdown("#### Have not account?")
        if st.button("Create Account"):
            st.session_state["page"] = "Sign Up"
            st.rerun()

    elif menu == "Sign Up":
        st.markdown('<div class="signup-title">Sign Up</div>', unsafe_allow_html=True)
        st.markdown('<div class="signup-subtitle">Create an account</div>', unsafe_allow_html=True)

        new_email = st.text_input("Email")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Sign Up"):
            if new_email == "" or new_password == "":
                st.error("Semua data harus diisi")
            elif new_password != confirm_password:
                st.error("Password tidak sama")
            else:
                if signup(new_email, new_password):
                    st.success("Akun berhasil dibuat. Silakan Login.")
                else:
                    st.error("Email sudah digunakan.")

        st.markdown("#### Already have an account?")
        if st.button("Log In"):
            st.rerun()

else:
    st.markdown(
        '<div class="dashboard-header">OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>',
        unsafe_allow_html=True
    )

    if st.sidebar.button("Logout"):
        st.session_state["login"] = False
        st.rerun()

    col1, col2 = st.columns([1, 2.15])

    with col1:
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)
        st.markdown("### Panel Input Scanner")

        komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"])

        uploaded_file = st.file_uploader(
            "Pilih Foto dari Galeri",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
        else:
            st.markdown('<div class="preview-box">[ Preview ]</div>', unsafe_allow_html=True)

        st.button("Buka Kamera")
        st.button("Pilih Foto dari Galeri")
        st.button("Tandai Area Sayur (ROI)")

        if st.button("Jalankan Analisis"):
            if uploaded_file is None:
                st.error("Pilih foto dulu.")
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(uploaded_file.getbuffer())
                    path = tmp.name

                nama, kondisi, sisa = cek_kondisi_roi(path, komoditas)

                if sisa == -1:
                    st.error(kondisi)
                else:
                    suhu = rekomendasi_suhu(nama)
                    sisa_hari = f"{sisa} Hari"

                    st.session_state["hasil"] = {
                        "komoditas": nama,
                        "kondisi": kondisi,
                        "sisa": sisa_hari,
                        "suhu": suhu
                    }

                    conn = sqlite3.connect(DB_ANALISIS)
                    cur = conn.cursor()
                    cur.execute(
                        """
                        INSERT INTO riwayat_pindai
                        (komoditas,kondisi,sisa_segar,suhu_simpan)
                        VALUES (?,?,?,?)
                        """,
                        (nama, kondisi, sisa_hari, suhu)
                    )
                    conn.commit()
                    conn.close()

                    st.success("Analisis berhasil")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)
        st.markdown("### Dashboard")

        hasil = st.session_state["hasil"]

        st.markdown(f"""
        <div class="result-box">
        Hasil Pindai Sistem
        ====================
        Komoditas : {hasil["komoditas"]}
        Kondisi   : {hasil["kondisi"]}
        Sisa      : {hasil["sisa"]}
        Suhu Simpan : {hasil["suhu"]}
        </div>
        """, unsafe_allow_html=True)

        conn = sqlite3.connect(DB_ANALISIS)
        data = conn.execute(
            "SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai ORDER BY id ASC"
        ).fetchall()
        conn.close()

        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
            column_config={
                0: "ID",
                1: "Nama",
                2: "Kondisi",
                3: "Sisa",
                4: "Suhu"
            }
        )

        st.markdown('</div>', unsafe_allow_html=True)
