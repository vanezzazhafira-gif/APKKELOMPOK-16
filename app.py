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


# =========================================================
# DATABASE
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
# IMAGE HELPER
# =========================================================
def file_to_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


login_bg = file_to_base64("login.jpeg")
signup_bg = file_to_base64("signup.jpg")
logo_img = file_to_base64("logo.png")


# =========================================================
# OPENCV ANALYSIS
# =========================================================
def rekomendasi_suhu(jenis):
    if jenis == "Wortel":
        return "0 - 4 °C"
    if jenis == "Cabai":
        return "7 - 10 °C"
    if jenis == "Brokoli":
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
    if score >= 2:
        return jenis, "Kurang Segar", 2
    return jenis, "Segar & Alami", 4


# =========================================================
# SESSION
# =========================================================
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

if "riwayat_session" not in st.session_state:
    st.session_state.riwayat_session = []


# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
section[data-testid="stSidebar"] {display:none;}
header[data-testid="stHeader"] {display:none;}

.stApp {
    background:#111111;
}

.block-container {
    padding-top:0rem;
    padding-bottom:0rem;
}

/* LOGIN & SIGN UP */
.auth-input div[data-testid="stTextInput"] input {
    height:70px;
    background:rgba(255,255,255,0.98);
    color:black;
    border:1px solid #dddddd;
    font-size:15px;
}

.signup-input div[data-testid="stTextInput"] input {
    height:42px;
    background:rgba(255,255,255,0.98);
    color:black;
    border:1px solid #dddddd;
    font-size:13px;
}

.auth-btn div.stButton > button,
.signup-btn div.stButton > button,
.small-btn div.stButton > button {
    background:white;
    color:black;
    border:1px solid #cccccc;
    border-radius:4px;
    display:block;
    margin:auto;
}

.auth-btn div.stButton > button {
    width:180px;
    height:50px;
}

.signup-btn div.stButton > button {
    width:120px;
    height:40px;
}

.small-btn div.stButton > button {
    width:105px;
    height:24px;
    font-size:11px;
}

.auth-text {
    text-align:center;
    font-size:19px;
    color:black;
}

/* DASHBOARD STYLE - dibuat mengikuti tampilan Qt Designer */
.dashboard-shell {
    width:1120px;
    min-height:660px;
    margin:0 auto;
    background:#f4f4f4;
    color:black;
    border:1px solid #d0d0d0;
    position:relative;
}

.topbar {
    height:70px;
    background:#145d1f;
    color:white;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:21px;
    font-weight:800;
    letter-spacing:0.2px;
    position:relative;
}

.logo-box {
    position:absolute;
    left:15px;
    top:7px;
    width:90px;
    height:55px;
    background:white;
    display:flex;
    align-items:center;
    justify-content:center;
}

.logo-box img {
    max-width:85px;
    max-height:52px;
}

.dash-content {
    display:grid;
    grid-template-columns: 405px 1fr;
    column-gap:45px;
    padding:38px 30px 25px 30px;
}

.left-area {
    width:405px;
}

.right-area {
    width:600px;
}

.section-title {
    font-size:16px;
    font-weight:700;
    margin-left:12px;
    margin-bottom:2px;
}

.select-wrap {
    width:400px;
    margin-left:12px;
}

.preview-panel {
    width:400px;
    height:250px;
    margin-left:12px;
    margin-top:10px;
    border:2px solid #111;
    background:#efefef;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:700;
    font-size:17px;
}

.preview-panel img {
    max-width:100%;
    max-height:100%;
    object-fit:contain;
}

.button-stack {
    margin-left:12px;
    margin-top:80px;
    width:400px;
}

.blue-btn div.stButton > button,
.orange-btn div.stButton > button,
.purple-btn div.stButton > button,
.green-btn div.stButton > button {
    width:400px;
    height:58px;
    border-radius:0px;
    color:white;
    font-weight:700;
    border:none;
    margin-bottom:25px;
}

.blue-btn div.stButton > button {background:#1976d2;}
.orange-btn div.stButton > button {background:#ff9800;}
.purple-btn div.stButton > button {background:#7b1fa2;}
.green-btn div.stButton > button {background:#2e7d32;}

.result-panel {
    width:590px;
    height:200px;
    border:2px solid #111;
    background:#f8f8f8;
    margin-top:16px;
    font-size:18px;
    font-weight:700;
    padding-top:18px;
    text-align:center;
    line-height:1.35;
}

.result-text {
    font-family:Arial, sans-serif;
    white-space:pre-line;
}

.table-panel {
    width:590px;
    height:240px;
    background:white;
    margin-top:0px;
}

/* agar komponen asli streamlit tidak merusak jarak */
div[data-testid="stSelectbox"] {
    margin-top:0px;
    margin-bottom:0px;
}

div[data-testid="stSelectbox"] div {
    color:black;
}

div[data-testid="stFileUploader"] {
    display:none;
}

[data-testid="stDataFrame"] {
    background:white;
}

.clear-btn div.stButton > button {
    width:400px;
    height:32px;
    border-radius:0px;
    background:#555;
    color:white;
    margin-top:-10px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# LOGIN PAGE
# =========================================================
if not st.session_state.login and st.session_state.page == "Login":
    bg = f"data:image/jpeg;base64,{login_bg}" if login_bg else ""

    st.markdown(f"""
    <style>
    .block-container {{
        max-width:536px;
        min-height:851px;
        margin:18px auto;
        padding-left:50px;
        padding-right:50px;
        background-image:url('{bg}');
        background-size:cover;
        background-position:center top;
        background-repeat:no-repeat;
        border-radius:8px;
        overflow:hidden;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:360px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="auth-input">', unsafe_allow_html=True)
    email = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
    password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="auth-btn">', unsafe_allow_html=True)
    if st.button("LOG IN"):
        if login(email, password):
            st.session_state.login = True
            st.rerun()
        else:
            st.error("Username atau Password Salah")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:65px;"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2.4, 1])
    with c1:
        st.markdown('<div class="auth-text">Have not account?</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="small-btn">', unsafe_allow_html=True)
        if st.button("Create Account"):
            st.session_state.page = "Sign Up"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# SIGN UP PAGE
# =========================================================
elif not st.session_state.login and st.session_state.page == "Sign Up":
    bg = f"data:image/jpeg;base64,{signup_bg}" if signup_bg else ""

    st.markdown(f"""
    <style>
    .block-container {{
        max-width:535px;
        min-height:849px;
        margin:18px auto;
        padding-left:140px;
        padding-right:115px;
        background-image:url('{bg}');
        background-size:cover;
        background-position:center top;
        background-repeat:no-repeat;
        border-radius:8px;
        overflow:hidden;
    }}
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:335px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="signup-input">', unsafe_allow_html=True)
    new_email = st.text_input("Email", placeholder="Email", label_visibility="collapsed")
    new_password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
    confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm Password", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:22px;"></div>', unsafe_allow_html=True)

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

    st.markdown('<div style="height:55px;"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2.8, 1])
    with c1:
        st.markdown('<div class="auth-text">Already have an account?</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="small-btn">', unsafe_allow_html=True)
        if st.button("Log In"):
            st.session_state.page = "Login"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# DASHBOARD PAGE
# =========================================================
else:
    st.markdown("""
    <style>
    .block-container {
        max-width:1120px;
        margin:0 auto;
        padding-left:0px;
        padding-right:0px;
        background:transparent;
    }
    </style>
    """, unsafe_allow_html=True)

    logo_html = ""
    if logo_img:
        logo_html = f'<div class="logo-box"><img src="data:image/png;base64,{logo_img}"></div>'

    st.markdown(f"""
    <div class="dashboard-shell">
        <div class="topbar">
            {logo_html}
            OPTIMALISASI DISTRIBUSI LOGISTIK HORTIKULTURA
        </div>
        <div class="dash-content">
            <div class="left-area">
                <div class="section-title">Panel Input Scanner</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="select-wrap">', unsafe_allow_html=True)
    komoditas = st.selectbox("", ["Wortel", "Cabai", "Brokoli"], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Pilih Foto dari Galeri",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as preview_tmp:
            image.convert("RGB").save(preview_tmp.name)
        img64 = file_to_base64(preview_tmp.name)
        st.markdown(
            f'<div class="preview-panel"><img src="data:image/jpeg;base64,{img64}"></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown('<div class="preview-panel">[ Preview ]</div>', unsafe_allow_html=True)

    st.markdown('<div class="button-stack">', unsafe_allow_html=True)

    st.markdown('<div class="blue-btn">', unsafe_allow_html=True)
    st.button("Buka Kamera")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="orange-btn">', unsafe_allow_html=True)
    st.button("Pilih Foto dari Galeri")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="purple-btn">', unsafe_allow_html=True)
    st.button("Tandai Area Sayur")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="green-btn">', unsafe_allow_html=True)
    analisis = st.button("Jalankan Analisis")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="clear-btn">', unsafe_allow_html=True)
    selesai = st.button("Selesai / Bersihkan Hasil")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if selesai:
        st.session_state.hasil = {
            "komoditas": "-",
            "kondisi": "-",
            "sisa": "-",
            "suhu": "-"
        }
        st.session_state.riwayat_session = []
        st.rerun()

    if analisis:
        if uploaded_file is None:
            st.session_state.hasil = {
                "komoditas": "Error",
                "kondisi": "Pilih foto dulu",
                "sisa": "-",
                "suhu": "-"
            }
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.getbuffer())
                path = tmp.name

            nama, kondisi, sisa = cek_kondisi_roi(path, komoditas)

            if sisa == -1:
                st.session_state.hasil = {
                    "komoditas": "Error",
                    "kondisi": kondisi,
                    "sisa": "-",
                    "suhu": "-"
                }
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

                new_id = len(st.session_state.riwayat_session) + 1
                st.session_state.riwayat_session.append(
                    (new_id, nama, kondisi, sisa_hari, suhu)
                )

    st.markdown("""
            </div>
            <div class="right-area">
                <div class="section-title">Dashboard</div>
    """, unsafe_allow_html=True)

    h = st.session_state.hasil
    st.markdown(f"""
        <div class="result-panel">
            <div class="result-text">
Hasil Pindai Sistem:
-----------------------------
Komoditas Terdeteksi : {h["komoditas"]}
Kondisi Kematangan   : {h["kondisi"]}
Estimasi Sisa Segar  : {h["sisa"]}
Suhu Penyimpanan     : {h["suhu"]}
            </div>
        </div>
        <div class="table-panel">
    """, unsafe_allow_html=True)

    st.dataframe(
        st.session_state.riwayat_session,
        use_container_width=True,
        hide_index=True,
        column_config={
            0: "ID",
            1: "Nama Komoditas",
            2: "Kondisi",
            3: "Masa Simpan",
            4: "Suhu"
        }
    )

    st.markdown("""
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
