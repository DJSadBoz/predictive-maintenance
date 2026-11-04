
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# =====================================================
# 1. CẤU HÌNH TRANG
# =====================================================

st.set_page_config(
    page_title="Predictive Maintenance",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ HỆ THỐNG BẢO TRÌ DỰ ĐOÁN")
st.caption("Giám sát và phát hiện nguy cơ sự cố máy bơm bằng dữ liệu cảm biến")

# =====================================================
# 2. CẤU HÌNH DỮ LIỆU
# =====================================================

DATA_FILE = Path(__file__).parent / "ket_qua_canh_bao.parquet"

SENSOR_COLUMNS = [
    "Độ_rung_RMS_mm_s",
    "Độ_rung_đỉnh_mm_s",
    "Nhiệt_độ_ổ_trục_C",
    "Dòng_điện_động_cơ_A",
    "Lưu_lượng_m3_h",
    "Áp_suất_đầu_ra_bar"
]

SENSOR_NAMES = {
    "Độ_rung_RMS_mm_s": "Độ rung RMS (mm/s)",
    "Độ_rung_đỉnh_mm_s": "Độ rung đỉnh (mm/s)",
    "Nhiệt_độ_ổ_trục_C": "Nhiệt độ ổ trục (°C)",
    "Dòng_điện_động_cơ_A": "Dòng điện động cơ (A)",
    "Lưu_lượng_m3_h": "Lưu lượng (m³/h)",
    "Áp_suất_đầu_ra_bar": "Áp suất đầu ra (bar)"
}

REQUIRED_COLUMNS = ["Thời_gian"] + SENSOR_COLUMNS

# =====================================================
# 3. ĐỌC DỮ LIỆU
# =====================================================

@st.cache_data(show_spinner="Đang đọc dữ liệu...")
def load_parquet(file_bytes):
    return pd.read_parquet(io.BytesIO(file_bytes))

@st.cache_data(show_spinner="Đang đọc CSV...")
def load_csv(file_bytes):
    return pd.read_csv(io.BytesIO(file_bytes))

def prepare_data(df):
    df = df.copy()

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        raise ValueError(
            "Dữ liệu thiếu các cột: " + ", ".join(missing)
        )

    df["Thời_gian"] = pd.to_datetime(
        df["Thời_gian"], errors="coerce"
    )

    for col in SENSOR_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Thời_gian"])
    df = df.sort_values("Thời_gian").reset_index(drop=True)

    if "Ket_qua_tong_hop" not in df.columns:
        df["Ket_qua_tong_hop"] = "Chưa xác định"

    return df

# =====================================================
# 4. CHỌN NGUỒN DỮ LIỆU
# =====================================================

st.sidebar.header("📂 NGUỒN DỮ LIỆU")

uploaded_file = st.sidebar.file_uploader(
    "Tải dữ liệu CSV",
    type=["csv"]
)

try:
    if uploaded_file is not None:
        df = load_csv(uploaded_file.getvalue())
        df = prepare_data(df)
        source_name = uploaded_file.name

    elif DATA_FILE.exists():
        df = load_parquet(DATA_FILE.read_bytes())
        df = prepare_data(df)
        source_name = DATA_FILE.name

    else:
        st.error(
            "Không tìm thấy ket_qua_canh_bao.parquet. "
            "Hãy kiểm tra file trên GitHub."
        )
        st.stop()

except Exception as e:
    st.error(f"Lỗi đọc dữ liệu: {e}")
    st.stop()

if df.empty:
    st.error("Dữ liệu không có bản ghi hợp lệ.")
    st.stop()

st.sidebar.success(f"Đang sử dụng: {source_name}")

# =====================================================
# 5. KHỞI TẠO TRẠNG THÁI PHÁT LẠI
# =====================================================

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "playing" not in st.session_state:
    st.session_state.playing = False

if "last_index" not in st.session_state:
    st.session_state.last_index = 0

total_rows = len(df)

st.session_state.current_index = min(
    max(0, st.session_state.current_index),
    total_rows - 1
)

# =====================================================
# 6. ĐIỀU KHIỂN THỜI GIAN
# =====================================================

st.sidebar.header("⏱️ ĐIỀU KHIỂN THỜI GIAN")

speed = st.sidebar.selectbox(
    "Tốc độ phát",
    options=[1, 2, 5, 10, 30, 60],
    format_func=lambda x: f"{x} bản ghi/giây"
)

col_a, col_b = st.sidebar.columns(2)

if col_a.button("▶ Phát", use_container_width=True):
    st.session_state.playing = True

if col_b.button("⏸ Dừng", use_container_width=True):
    st.session_state.playing = False

col_c, col_d = st.sidebar.columns(2)

if col_c.button("⏮ Đầu", use_container_width=True):
    st.session_state.current_index = 0
    st.session_state.playing = False

if col_d.button("⏭ Cuối", use_container_width=True):
    st.session_state.current_index = total_rows - 1
    st.session_state.playing = False

st.sidebar.divider()

if st.sidebar.button("◀ Tua lùi 60 bản ghi"):
    st.session_state.current_index = max(
        0, st.session_state.current_index - 60
    )

if st.sidebar.button("Tua tới 60 bản ghi ▶"):
    st.session_state.current_index = min(
        total_rows - 1, st.session_state.current_index + 60
    )

# =====================================================
# 7. CHỌN THỜI ĐIỂM CỤ THỂ
# =====================================================

st.sidebar.subheader("📅 Chọn thời điểm")

min_time = df["Thời_gian"].min()
max_time = df["Thời_gian"].max()

selected_time = st.sidebar.slider(
    "Di chuyển đến thời điểm",
    min_value=min_time.to_pydatetime(),
    max_value=max_time.to_pydatetime(),
    value=df.iloc[st.session_state.current_index]["Thời_gian"].to_pydatetime(),
    format="DD/MM/YYYY HH:mm"
)

if st.sidebar.button("Đi đến thời điểm đã chọn"):
    distances = (
        df["Thời_gian"] - pd.Timestamp(selected_time)
    ).abs()

    st.session_state.current_index = int(distances.idxmin())
    st.session_state.playing = False

# =====================================================
# 8. PHÁT LẠI TỰ ĐỘNG
# =====================================================

if st.session_state.playing:
    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(
            interval=1000,
            key="playback_refresh"
        )

        st.session_state.current_index = min(
            total_rows - 1,
            st.session_state.current_index + speed
        )

        if st.session_state.current_index >= total_rows - 1:
            st.session_state.playing = False

    except ImportError:
        st.warning(
            "Thiếu streamlit-autorefresh. "
            "Hãy kiểm tra requirements.txt."
        )

# =====================================================
# 9. BẢN GHI HIỆN TẠI
# =====================================================

current = df.iloc[st.session_state.current_index]

current_time = current["Thời_gian"]
current_status = str(current["Ket_qua_tong_hop"])

st.divider()

st.subheader("📊 TRẠNG THÁI MÁY TẠI THỜI ĐIỂM HIỆN TẠI")

m1, m2, m3 = st.columns(3)

m1.metric(
    "Thời gian",
    current_time.strftime("%d/%m/%Y %H:%M:%S")
)

m2.metric(
    "Vị trí dữ liệu",
    f"{st.session_state.current_index + 1:,}/{total_rows:,}"
)

m3.metric(
    "Trạng thái",
    current_status
)

st.progress(
    (st.session_state.current_index + 1) / total_rows
)

# =====================================================
# 10. CẢNH BÁO
# =====================================================

st.subheader("🚨 KẾT QUẢ GIÁM SÁT")

status_colors = {
    "Bình thường": "success",
    "Cần theo dõi": "warning",
    "Cảnh báo": "warning",
    "Nguy cơ cao": "error"
}

if current_status in status_colors:
    getattr(st, status_colors[current_status])(
        f"Trạng thái thiết bị: {current_status}"
    )
else:
    st.info(f"Trạng thái thiết bị: {current_status}")

# =====================================================
# 11. THÔNG SỐ CẢM BIẾN
# =====================================================

st.subheader("📡 THÔNG SỐ CẢM BIẾN HIỆN TẠI")

cols = st.columns(3)

for i, sensor in enumerate(SENSOR_COLUMNS):
    value = current[sensor]

    with cols[i % 3]:
        st.metric(
            SENSOR_NAMES[sensor],
            f"{value:.3f}" if pd.notna(value) else "N/A"
        )

# =====================================================
# 12. BIỂU ĐỒ CẢM BIẾN
# =====================================================

st.divider()
st.subheader("📈 BIỂU ĐỒ DIỄN BIẾN CẢM BIẾN")

history_size = st.selectbox(
    "Số bản ghi hiển thị",
    [60, 120, 300, 600, 1000],
    index=2
)

start_index = max(
    0, st.session_state.current_index - history_size + 1
)

history = df.iloc[
    start_index:st.session_state.current_index + 1
].copy()

selected_sensor = st.selectbox(
    "Chọn thông số cảm biến",
    SENSOR_COLUMNS,
    format_func=lambda x: SENSOR_NAMES[x]
)

fig = px.line(
    history,
    x="Thời_gian",
    y=selected_sensor,
    title=SENSOR_NAMES[selected_sensor],
    labels={
        "Thời_gian": "Thời gian",
        selected_sensor: SENSOR_NAMES[selected_sensor]
    }
)

fig.update_layout(
    hovermode="x unified",
    height=450
)

st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 13. BẢNG LỊCH SỬ
# =====================================================

st.divider()
st.subheader("📋 LỊCH SỬ DỮ LIỆU")

display_columns = (
    ["Thời_gian"] + SENSOR_COLUMNS + ["Ket_qua_tong_hop"]
)

st.dataframe(
    history[display_columns].tail(100),
    use_container_width=True,
    hide_index=True
)

# =====================================================
# 14. THỐNG KÊ TRẠNG THÁI
# =====================================================

st.divider()
st.subheader("📊 THỐNG KÊ TRẠNG THÁI TRÊN TOÀN BỘ DỮ LIỆU")

status_counts = df["Ket_qua_tong_hop"].value_counts().reset_index()
status_counts.columns = ["Trạng thái", "Số lượng"]

fig_status = px.pie(
    status_counts,
    names="Trạng thái",
    values="Số lượng",
    title="Phân bố trạng thái thiết bị"
)

st.plotly_chart(fig_status, use_container_width=True)

# =====================================================
# 15. TẢI DỮ LIỆU
# =====================================================

st.divider()
st.subheader("⬇️ XUẤT DỮ LIỆU")

csv_data = df.to_csv(
    index=False,
    encoding="utf-8-sig"
).encode("utf-8-sig")

st.download_button(
    "Tải toàn bộ dữ liệu CSV",
    data=csv_data,
    file_name="du_lieu_predictive_maintenance.csv",
    mime="text/csv"
)

st.caption(
    "Predictive Maintenance Dashboard | "
    "Hệ thống giám sát và bảo trì dự đoán"
)
