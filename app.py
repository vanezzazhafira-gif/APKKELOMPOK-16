import streamlit as st
import sqlite3
import cv2
import numpy as np
from PIL import Image
import tempfile
import os
import base64

st.set_page_config(page_title="Optimalisasi Logistik Pertanian", layout="wide")

DB_LOGIN = "manajemen_akses.db"
DB_ANALISIS = "logistik_hortikultura.db"


# =========================
# DATABASE
# =========================
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


# =========================
# HELPER IMAGE
# =========================
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


login_bg = file_to_base64("login.jpeg")
signup_bg = file_to_base64("signup.jpg")
logo_img = file_to_base64("logo.png")


# =========================
# ANALISIS OPENCV
# =========================
def rekomendasi_suhu(jenis):
    if jenis == "Wortel":
        return "0 - 4 °C"
    elif jenis == "Cabai":
        return "7 - 10 °C"
    elif jenis == "Brokoli":
        return "0 - 2 °C"
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

    if cv2.countNonZero(mask_clean) < 500:
        return "Error", "Objek sayuran tidak terdeteksi jelas.", -1

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
    if damage_pct > 10:
        score += 4
    elif damage_pct > 3:
        score += 2

    if jenis in ["Brokoli", "Cabai"] and yellow_pct > 15:
        score += 2

    if mean_sat < 60:
        score += 2
    elif mean_sat < 90:
        score += 1

    if score >= 4:
        return jenis, "BUSUK / RUSAK", 0
    elif score >= 2:
        return jenis, "Kurang Segar", 2
    else:
        return jenis, "Segar & Alami", 4


# =========================
# SESSION
# =========================
if "login" not in st.session_state:
    st.session_state.login = False

if "page" not in st.session_state:
    st.session_state.page = "Login"

if "hasil" not in st.session_state:
    st.session_state.hasil = {
        "komoditas": "-",
        "kondisi": "-",
        "sisa": "-",
        "suhu": "-"
    }


# =========================
# CSS
# =========================
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    display: none;
}

header[data-testid="stHeader"] {
    display: none;
}

.stApp {
    background: #111111;
}

.block-container {
    padding-top: 0rem;
    padding-bottom: 0rem;
}

/* LOGIN & SIGNUP */
.auth-wrap {
    width: 536px;
    min-height: 851px;
    margin: 18px auto;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    position: relative;
    color: black;
}

.auth-bg {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    z-index: 0;
}

.auth-content {
    position: relative;
    z-index: 2;
    padding: 1px 50px;
}

.login-space {
    height: 280px;
}

.signup-space {
    height: 250px;
}

.auth-input div[data-testid="stTextInput"] input {
    height: 70px;
    background: rgba(255,255,255,0.96);
    color: black;
    border: 1px solid #e2e2e2;
    font-size: 15px;
}

.auth-btn div.stButton > button {
    width: 180px;
    height: 50px;
    margin-left: auto;
    margin-right: auto;
    display: block;
    background: white;
    color: black;
    border: 1px solid #ccc;
    border-radius: 5px;
}

.small-btn div.stButton > button {
    width: 100px;
    height: 24px;
    font-size: 11px;
    background: white;
    color: black;
    border: 1px solid #ccc;
    border-radius: 4px;
}

.signup-input div[data-testid="stTextInput"] input {
    height: 42px;
    background: rgba(255,255,255,0.96);
    color: black;
    border: 1px solid #e2e2e2;
    font-size: 13px;
}

.signup-btn div.stButton > button {
    width: 120px;
    height: 40px;
    margin-left: auto;
    margin-right: auto;
    display: block;
    background: white;
    color: black;
    border: 1px solid #ccc;
    border-radius: 5px;
}

.auth-text {
    text-align: center;
    font-size: 19px;
    color: black;
}

/* DASHBOARD */
.dashboard-page {
    background: #eeeeee;
    width: 1120px;
    min-height: 660px;
    margin: 18px auto;
    border-radius: 0px;
    overflow: hidden;
    color: black;
}

.dashboard-header {
    background: #145d1f;
    color: white;
    text-align: center;
    padding: 12px;
    font-size: 21px;
    font-weight: 800;
}

.dashboard-body {
    padding: 10px 15px;
}

.panel-box {
    background: white;
    border: 1px solid #999;
    padding: 10px;
    min-height: 575px;
}

.panel-title {
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 10px;
}

.preview-box {
    background: #dddddd;
    height: 337px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: black;
    margin-bottom: 4px;
}

.result-box {
    background: #f7f7f7;
    padding: 18px 0px 12px 275px;
    font-family: monospace;
    font-size: 16px;
    white-space: pre-line;
    border-bottom: 1px solid #999;
}

.blue-btn div.stButton > button {
    background: #1976d2;
    color: white;
    border-radius: 0px;
    width: 100%;
    height: 35px;
}

.orange-btn div.stButton > button {
    background: #ff9800;
    color: white;
    border-radius: 0px;
    width: 100%;
    height: 35px;
}

.purple-btn div.stButton > button {
    background: #7b1fa2;
    color: white;
    border-radius: 0px;
    width: 100%;
    height: 35px;
}

.green-btn div.stButton > button {
    background: #2e7d32;
    color: white;
    border-radius: 0px;
    width: 100%;
    height: 35px;
    font-weight: 800;
}

[data-testid="stDataFrame"] {
    background: white;
}

</style>
""", unsafe_allow_html=True)


# =========================
# LOGIN PAGE
# =========================
if not st.session_state.login and st.session_state.page == "Login":
    bg = f"data:image/jpeg;base64,{login_bg}" if login_bg else ""

    st.markdown(f"""
    <div class="auth-wrap">
        <div class="auth-bg" style="background-image:url('{bg}');"></div>
        <div class="auth-content">
            <div class="login-space"></div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-input">', unsafe_allow_html=True)
    email = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
    password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="auth-btn">', unsafe_allow_html=True)
    if st.button("LOG IN"):
        if login(email, password):
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Username atau Password Salah")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:70px;"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.2, 1, 1.2])
    with c1:
        st.markdown('<div class="auth-text">Have not account?</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="small-btn">', unsafe_allow_html=True)
        if st.button("Create Account"):
            st.session_state.page = "Sign Up"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================
# SIGNUP PAGE
# =========================
elif not st.session_state.login and st.session_state.page == "Sign Up":
    bg = f"data:image/jpeg;base64,{signup_bg}" if signup_bg else ""

    st.markdown(f"""
    <div class="auth-wrap">
        <div class="auth-bg" style="background-image:url('{bg}');"></div>
        <div class="auth-content">
            <div class="signup-space"></div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="signup-input">', unsafe_allow_html=True)
    new_email = st.text_input("Email", placeholder="Email", label_visibility="collapsed")
    new_password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
    confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm Password", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:25px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="signup-btn">', unsafe_allow_html=True)
    if st.button("Sign Up"):
        if new_email == "" or new_password == "":
            st.error("Semua data harus diisi")
        elif new_password != confirm:
            st.error("Password tidak sama")
        elif signup(new_email, new_password):
            st.success("Akun berhasil dibuat. Silakan login.")
        else:
            st.error("Email sudah digunakan.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:45px;"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([2.2, 0.8, 1.3])
    with c1:
        st.markdown('<div class="auth-text">Already have an account?</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="small-btn">', unsafe_allow_html=True)
        if st.button("Log In"):
            st.session_state.page = "Login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
        </div>
    </div>
    """, unsafe_allow_html=True)


# =========================
# DASHBOARD PAGE
# =========================
else:
    st.markdown('<div class="dashboard-page">', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-header">OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="dashboard-body">', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2.25])

    with col1:
        st.markdown('<div class="panel-box">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Panel Input Scanner</div>', unsafe_allow_html=True)

        komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"], label_visibility="collapsed")

        uploaded_file = st.file_uploader(
            "Pilih Foto",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
        else:
            st.markdown('<div class="preview-box">[ Preview ]</div>', unsafe_allow_html=True)

        st.markdown('<div class="blue-btn">', unsafe_allow_html=True)
        st.button("Buka Kamera")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="orange-btn">', unsafe_allow_html=True)
        st.button("Pilih Foto dari Galeri")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="purple-btn">', unsafe_allow_html=True)
        st.button("Tandai Area Sayur (ROI)")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="green-btn">', unsafe_allow_html=True)
        analisis = st.button("Jalankan Analisis")
        st.markdown('</div>', unsafe_allow_html=True)

        if analisis:
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

                    st.session_state.hasil = {
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
        st.markdown('<div class="panel-title">Dashboard</div>', unsafe_allow_html=True)

        h = st.session_state.hasil
        st.markdown(f"""
        <div class="result-box">
Hasil Pindai Sistem
====================
Komoditas : {h["komoditas"]}
Kondisi   : {h["kondisi"]}
Sisa      : {h["sisa"]}
Suhu Simpan : {h["suhu"]}
        </div>
        """, unsafe_allow_html=True)

        conn = sqlite3.connect(DB_ANALISIS)
        data = conn.execute(
            "SELECT id, komoditas, kondisi, sisa_segar, suhu_simpan FROM riwayat_pindai"
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

    st.markdown('</div></div>', unsafe_allow_html=True)
