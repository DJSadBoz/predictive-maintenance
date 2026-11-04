
import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit_autorefresh
import io
import datetime
from pathlib import Path


# =========================================================
# 1. CẤU HÌNH TRANG
# =========================================================

st.set_page_config(
    page_title="Predictive Maintenance",
    page_icon="⚙️",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent

PARQUET_FILE = BASE_DIR / "ket_qua_canh_bao.parquet"

SENSOR_COLUMNS = [
    "Độ_rung_RMS_mm_s",
    "Độ_rung_đỉnh_mm_s",
    "Nhiệt_độ_ổ_trục_C",
    "Dòng_điện_động_cơ_A",
    "Lưu_lượng_m3_h",
    "Áp_suất_đầu_ra_bar"
]

REQUIRED_COLUMNS = ["Thời_gian"] + SENSOR_COLUMNS


# =========================================================
# 2. ĐỌC DỮ LIỆU PARQUET
# =========================================================

@st.cache_data(show_spinner="Đang đọc dữ liệu Parquet...")
def load_parquet(file_path, modified_time):
    return pd.read_parquet(file_path)


# =========================================================
# 3. ĐỌC DỮ LIỆU CSV ĐƯỢC TẢI LÊN
# =========================================================

@st.cache_data(show_spinner="Đang đọc file CSV...")
def load_uploaded_csv(file_bytes):

    try:
        return pd.read_csv(
            io.BytesIO(file_bytes),
            encoding="utf-8-sig"
        )

    except UnicodeDecodeError:
        return pd.read_csv(
            io.BytesIO(file_bytes),
            encoding="cp1258"
        )


# =========================================================
# 4. KIỂM TRA VÀ CHUẨN HÓA DỮ LIỆU
# =========================================================

def prepare_data(df):

    df = df.copy()

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        st.error(
            "File dữ liệu thiếu các cột bắt buộc: "
            + ", ".join(missing_columns)
        )
        st.stop()

    df["Thời_gian"] = pd.to_datetime(
        df["Thời_gian"],
        errors="coerce"
    )

    invalid_rows = df["Thời_gian"].isna().sum()

    if invalid_rows > 0:
        st.warning(
            f"Có {invalid_rows:,} bản ghi không có thời gian hợp lệ. "
            "Các bản ghi này sẽ được bỏ qua."
        )

        df = df.dropna(subset=["Thời_gian"])

    for col in SENSOR_COLUMNS:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.sort_values("Thời_gian")
    df = df.reset_index(drop=True)

    if "Ket_qua_tong_hop" not in df.columns:
        df["Ket_qua_tong_hop"] = "Chưa xác định"

    if len(df) == 0:
        st.error("Không có dữ liệu hợp lệ để hiển thị.")
        st.stop()

    return df


# =========================================================
# 5. TIÊU ĐỀ HỆ THỐNG
# =========================================================

st.title("⚙️ HỆ THỐNG GIÁM SÁT VÀ BẢO TRÌ DỰ ĐOÁN")

st.caption(
    "PREDICTIVE MAINTENANCE SYSTEM | "
    "GIÁM SÁT TÌNH TRẠNG THIẾT BỊ"
)

st.divider()


# =========================================================
# 6. SIDEBAR - NGUỒN DỮ LIỆU
# =========================================================

st.sidebar.header("📂 QUẢN LÝ DỮ LIỆU")

uploaded_file = st.sidebar.file_uploader(
    "Tải lên dữ liệu CSV mới",
    type=["csv"]
)

if uploaded_file is not None:

    file_bytes = uploaded_file.getvalue()

    try:
        raw_df = load_uploaded_csv(file_bytes)

        source_key = (
            "uploaded",
            uploaded_file.name,
            uploaded_file.size
        )

        st.sidebar.success(
            f"Đang sử dụng: {uploaded_file.name}"
        )

    except Exception as e:
        st.error(f"Không thể đọc file CSV: {e}")
        st.stop()

else:

    if not PARQUET_FILE.exists():

        st.error(
            "Không tìm thấy ket_qua_canh_bao.parquet. "
            "Hãy kiểm tra file trong GitHub."
        )

        st.stop()

    try:
        modified_time = PARQUET_FILE.stat().st_mtime_ns

        raw_df = load_parquet(
            str(PARQUET_FILE),
            modified_time
        )

        source_key = (
            "parquet",
            str(PARQUET_FILE),
            modified_time
        )

        st.sidebar.success(
            "Đang sử dụng dữ liệu Parquet mặc định"
        )

    except Exception as e:
        st.error(f"Không thể đọc dữ liệu Parquet: {e}")
        st.stop()


# =========================================================
# 7. CHUẨN HÓA DỮ LIỆU
# =========================================================

try:
    df = prepare_data(raw_df)

except Exception as e:
    st.error(f"Lỗi xử lý dữ liệu: {e}")
    st.stop()


total_rows = len(df)

min_time = df["Thời_gian"].iloc[0]
max_time = df["Thời_gian"].iloc[-1]


# =========================================================
# 8. KHỞI TẠO TRẠNG THÁI PHÁT LẠI
# =========================================================

if "data_source" not in st.session_state:
    st.session_state.data_source = None

if st.session_state.data_source != source_key:

    st.session_state.data_source = source_key
    st.session_state.current_index = 0
    st.session_state.playing = False
    st.session_state.last_refresh_count = None

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "playing" not in st.session_state:
    st.session_state.playing = False

if "last_refresh_count" not in st.session_state:
    st.session_state.last_refresh_count = None

st.session_state.current_index = max(
    0,
    min(st.session_state.current_index, total_rows - 1)
)


# =========================================================
# 9. ĐIỀU KHIỂN TỐC ĐỘ PHÁT
# =========================================================

st.sidebar.divider()

st.sidebar.subheader("⏩ TỐC ĐỘ PHÁT LẠI")

speed_options = {
    "1x - 1 giây = 1 bản ghi": 1,
    "2x - 2 bản ghi/giây": 2,
    "5x - 5 bản ghi/giây": 5,
    "10x - 10 bản ghi/giây": 10,
    "30x - 30 bản ghi/giây": 30,
    "60x - 60 bản ghi/giây": 60
}

selected_speed = st.sidebar.selectbox(
    "Chọn tốc độ",
    list(speed_options.keys())
)

speed = speed_options[selected_speed]


# =========================================================
# 10. CÁC NÚT ĐIỀU KHIỂN
# =========================================================

st.subheader("🎮 ĐIỀU KHIỂN PHÁT LẠI")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("▶ BẮT ĐẦU", use_container_width=True):
        st.session_state.playing = True
        st.session_state.current_index = 0
        st.session_state.last_refresh_count = None
        st.rerun()

with col2:
    if st.button("⏸ TẠM DỪNG", use_container_width=True):
        st.session_state.playing = False
        st.session_state.last_refresh_count = None
        st.rerun()

with col3:
    if st.button("▶ TIẾP TỤC", use_container_width=True):
        st.session_state.playing = True
        st.session_state.last_refresh_count = None
        st.rerun()

with col4:
    if st.button("↺ ĐẶT LẠI", use_container_width=True):
        st.session_state.playing = False
        st.session_state.current_index = 0
        st.session_state.last_refresh_count = None
        st.rerun()


# =========================================================
# 11. TUA LÙI VÀ TUA NHANH
# =========================================================

st.divider()

st.subheader("⏪ TUA LÙI / TUA NHANH")

col1, col2 = st.columns(2)

with col1:
    if st.button("⏪ LÙI 60 BẢN GHI", use_container_width=True):
        st.session_state.current_index = max(
            0,
            st.session_state.current_index - 60
        )
        st.session_state.last_refresh_count = None
        st.rerun()

with col2:
    if st.button("⏩ TIẾN 60 BẢN GHI", use_container_width=True):
        st.session_state.current_index = min(
            total_rows - 1,
            st.session_state.current_index + 60
        )
        st.session_state.last_refresh_count = None
        st.rerun()


# =========================================================
# 12. CHUYỂN ĐẾN THỜI ĐIỂM CỤ THỂ
# =========================================================

st.divider()

st.subheader("📅 CHUYỂN ĐẾN THỜI ĐIỂM BẤT KỲ")

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    selected_date = st.date_input(
        "Chọn ngày",
        value=min_time.date(),
        min_value=min_time.date(),
        max_value=max_time.date()
    )

with col2:
    selected_time = st.time_input(
        "Chọn giờ",
        value=min_time.time().replace(microsecond=0)
    )

with col3:
    st.write("")
    st.write("")

    if st.button("ĐI ĐẾN", use_container_width=True):

        target_time = pd.Timestamp(
            datetime.datetime.combine(
                selected_date,
                selected_time
            )
        )

        position = df["Thời_gian"].searchsorted(target_time)

        left = max(0, position - 1)
        right = min(total_rows - 1, position)

        if abs(
            df["Thời_gian"].iloc[left] - target_time
        ) <= abs(
            df["Thời_gian"].iloc[right] - target_time
        ):
            chosen_index = left
        else:
            chosen_index = right

        st.session_state.current_index = chosen_index
        st.session_state.playing = False
        st.session_state.last_refresh_count = None

        st.rerun()


# =========================================================
# 13. CHỌN BẢN GHI BẰNG SỐ THỨ TỰ
# =========================================================

st.subheader("🎯 CHỌN VỊ TRÍ DỮ LIỆU")

selected_index = st.number_input(
    "Số thứ tự bản ghi",
    min_value=0,
    max_value=total_rows - 1,
    value=int(st.session_state.current_index),
    step=1
)

if st.button("CHUYỂN ĐẾN BẢN GHI"):
    st.session_state.current_index = int(selected_index)
    st.session_state.playing = False
    st.session_state.last_refresh_count = None
    st.rerun()


# =========================================================
# 14. TỰ ĐỘNG PHÁT LẠI
# =========================================================

if st.session_state.playing:

    refresh_count = streamlit_autorefresh.st_autorefresh(
        interval=1000,
        key="playback_refresh"
    )

    last_count = st.session_state.last_refresh_count

    if last_count is None:
        st.session_state.last_refresh_count = refresh_count

    elif refresh_count != last_count:

        elapsed = refresh_count - last_count

        st.session_state.current_index += speed * elapsed

        st.session_state.last_refresh_count = refresh_count

    if st.session_state.current_index >= total_rows - 1:

        st.session_state.current_index = total_rows - 1
        st.session_state.playing = False
        st.session_state.last_refresh_count = None

        st.warning("Đã phát đến bản ghi cuối cùng.")

        st.rerun()


# =========================================================
# 15. LẤY DỮ LIỆU TẠI THỜI ĐIỂM HIỆN TẠI
# =========================================================

current_index = st.session_state.current_index

current_data = df.iloc[current_index]

current_time = current_data["Thời_gian"]


# =========================================================
# 16. THÔNG TIN TIẾN TRÌNH
# =========================================================

st.divider()

st.subheader("📊 TIẾN TRÌNH PHÁT LẠI")

progress = (current_index + 1) / total_rows

st.progress(progress)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Bản ghi hiện tại",
    f"{current_index + 1:,} / {total_rows:,}"
)

col2.metric(
    "Thời điểm dữ liệu",
    current_time.strftime("%d/%m/%Y %H:%M:%S")
)

col3.metric(
    "Trạng thái phát",
    "ĐANG PHÁT" if st.session_state.playing else "ĐÃ TẠM DỪNG"
)

st.caption(
    f"Thời gian dữ liệu: {min_time} đến {max_time}"
)


# =========================================================
# 17. TRẠNG THÁI THIẾT BỊ
# =========================================================

st.divider()

st.subheader("🚨 TRẠNG THÁI THIẾT BỊ")

device_name = current_data.get(
    "Mã_thiết_bị",
    "PUMP-01"
)

status = str(current_data["Ket_qua_tong_hop"])

col1, col2 = st.columns(2)

col1.metric(
    "Thiết bị",
    str(device_name)
)

col2.metric(
    "Kết quả tổng hợp",
    status
)


# =========================================================
# 18. CÁC CHỈ SỐ CẢM BIẾN
# =========================================================

st.divider()

st.subheader("📡 DỮ LIỆU CẢM BIẾN")

def display_value(value):

    if pd.isna(value):
        return "Không có dữ liệu"

    return f"{value:,.3f}"


sensor_labels = [
    ("Độ rung RMS", "Độ_rung_RMS_mm_s", "mm/s"),
    ("Độ rung đỉnh", "Độ_rung_đỉnh_mm_s", "mm/s"),
    ("Nhiệt độ ổ trục", "Nhiệt_độ_ổ_trục_C", "°C"),
    ("Dòng điện động cơ", "Dòng_điện_động_cơ_A", "A"),
    ("Lưu lượng", "Lưu_lượng_m3_h", "m³/h"),
    ("Áp suất đầu ra", "Áp_suất_đầu_ra_bar", "bar")
]

for row_start in [0, 3]:

    cols = st.columns(3)

    for i, (label, column, unit) in enumerate(
        sensor_labels[row_start:row_start + 3]
    ):

        value = current_data[column]

        with cols[i]:
            st.metric(
                label,
                display_value(value),
                help=f"Đơn vị: {unit}"
            )


# =========================================================
# 19. BIỂU ĐỒ CẢM BIẾN
# =========================================================

st.divider()

st.subheader("📈 BIỂU ĐỒ DIỄN BIẾN CẢM BIẾN")

selected_sensor = st.selectbox(
    "Chọn cảm biến",
    SENSOR_COLUMNS
)

history_start = max(0, current_index - 499)

chart_data = df.iloc[
    history_start:current_index + 1
].copy()

fig = px.line(
    chart_data,
    x="Thời_gian",
    y=selected_sensor,
    title=f"Diễn biến {selected_sensor}"
)

fig.update_layout(
    xaxis_title="Thời gian",
    yaxis_title=selected_sensor,
    hovermode="x unified"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# =========================================================
# 20. LỊCH SỬ DỮ LIỆU
# =========================================================

st.divider()

st.subheader("📋 LỊCH SỬ DỮ LIỆU GẦN NHẤT")

history = df.iloc[
    max(0, current_index - 9):current_index + 1
]

display_columns = [
    "Thời_gian"
] + SENSOR_COLUMNS + [
    "Ket_qua_tong_hop"
]

st.dataframe(
    history[display_columns].iloc[::-1],
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 21. THÔNG TIN CUỐI TRANG
# =========================================================

st.divider()

st.caption(
    "PREDICTIVE MAINTENANCE SYSTEM | "
    "Hệ thống giám sát và bảo trì dự đoán"
)
