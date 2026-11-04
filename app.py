
import io
from pathlib import Path
from datetime import datetime, date, time, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from streamlit_autorefresh import st_autorefresh


# =========================================================
# 1. CẤU HÌNH TRANG
# =========================================================

st.set_page_config(
    page_title="Predictive Maintenance",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ HỆ THỐNG BẢO TRÌ DỰ ĐOÁN")
st.caption(
    "Giám sát tình trạng máy bơm và phát hiện nguy cơ sự cố "
    "bằng dữ liệu cảm biến"
)


# =========================================================
# 2. CẤU HÌNH DỮ LIỆU
# =========================================================

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "ket_qua_canh_bao.parquet"

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


# =========================================================
# 3. ĐỌC VÀ XỬ LÝ DỮ LIỆU
# =========================================================

@st.cache_data(show_spinner="Đang đọc dữ liệu Parquet...")
def load_parquet(file_bytes):
    return pd.read_parquet(io.BytesIO(file_bytes))


@st.cache_data(show_spinner="Đang đọc dữ liệu CSV...")
def load_csv(file_bytes):
    return pd.read_csv(io.BytesIO(file_bytes))


def prepare_data(df):

    df = df.copy()

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Thiếu các cột bắt buộc: "
            + ", ".join(missing_columns)
        )

    df["Thời_gian"] = pd.to_datetime(
        df["Thời_gian"],
        errors="coerce"
    )

    for col in SENSOR_COLUMNS:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(subset=["Thời_gian"])

    df = df.sort_values(
        "Thời_gian"
    ).reset_index(drop=True)

    if "Ket_qua_tong_hop" not in df.columns:
        df["Ket_qua_tong_hop"] = "Chưa xác định"

    return df


# =========================================================
# 4. CHỌN NGUỒN DỮ LIỆU
# =========================================================

st.sidebar.header("📂 NGUỒN DỮ LIỆU")

uploaded_file = st.sidebar.file_uploader(
    "Tải dữ liệu CSV từ máy tính",
    type=["csv"]
)

try:

    if uploaded_file is not None:

        df = load_csv(
            uploaded_file.getvalue()
        )

        df = prepare_data(df)

        source_name = uploaded_file.name

    elif DATA_FILE.exists():

        df = load_parquet(
            DATA_FILE.read_bytes()
        )

        df = prepare_data(df)

        source_name = DATA_FILE.name

    else:

        st.error(
            "Không tìm thấy ket_qua_canh_bao.parquet. "
            "Hãy kiểm tra file trên GitHub."
        )

        st.stop()

except Exception as error:

    st.error(f"Lỗi đọc dữ liệu: {error}")
    st.stop()


if df.empty:

    st.error("Không có dữ liệu hợp lệ.")
    st.stop()


total_rows = len(df)

min_time = df["Thời_gian"].min()
max_time = df["Thời_gian"].max()

st.sidebar.success(
    f"Đang sử dụng: {source_name}"
)

st.sidebar.write(
    f"**Tổng số bản ghi:** {total_rows:,}"
)

st.sidebar.write(
    f"**Thời gian bắt đầu:** "
    f"{min_time.strftime('%d/%m/%Y %H:%M:%S')}"
)

st.sidebar.write(
    f"**Thời gian kết thúc:** "
    f"{max_time.strftime('%d/%m/%Y %H:%M:%S')}"
)


# =========================================================
# 5. KHỞI TẠO TRẠNG THÁI
# =========================================================

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "playing" not in st.session_state:
    st.session_state.playing = False

if "playback_speed" not in st.session_state:
    st.session_state.playback_speed = 1

st.session_state.current_index = min(
    max(0, st.session_state.current_index),
    total_rows - 1
)


# =========================================================
# 6. HÀM TÌM BẢN GHI GẦN NHẤT
# =========================================================

def find_nearest_index(target_time):

    distances = (
        df["Thời_gian"] - pd.Timestamp(target_time)
    ).abs()

    return int(distances.idxmin())


# =========================================================
# 7. CHỌN THỜI ĐIỂM CỤ THỂ
# =========================================================

st.sidebar.divider()

st.sidebar.header("📅 ĐI ĐẾN THỜI ĐIỂM CỤ THỂ")

st.sidebar.caption(
    "Chọn ngày và nhập giờ muốn xem. "
    "Không cần sử dụng thanh trượt."
)

selected_date = st.sidebar.date_input(
    "Chọn ngày",
    value=min_time.date(),
    min_value=min_time.date(),
    max_value=max_time.date(),
    format="DD/MM/YYYY",
    key="selected_date"
)

selected_time = st.sidebar.time_input(
    "Nhập giờ, phút, giây",
    value=time(0, 0, 0),
    step=1,
    key="selected_time"
)

if st.sidebar.button(
    "📍 ĐI ĐẾN THỜI ĐIỂM",
    use_container_width=True
):

    target_time = datetime.combine(
        selected_date,
        selected_time
    )

    if target_time < min_time.to_pydatetime():

        st.sidebar.warning(
            "Thời điểm nằm trước dữ liệu bắt đầu."
        )

    elif target_time > max_time.to_pydatetime():

        st.sidebar.warning(
            "Thời điểm nằm sau dữ liệu kết thúc."
        )

    else:

        st.session_state.current_index = (
            find_nearest_index(target_time)
        )

        st.session_state.playing = False

        st.rerun()


# =========================================================
# 8. ĐIỀU KHIỂN PHÁT LẠI
# =========================================================

st.sidebar.divider()

st.sidebar.header("⏯️ ĐIỀU KHIỂN PHÁT LẠI")

speed = st.sidebar.selectbox(
    "Tốc độ phát",
    options=[1, 2, 5, 10, 30, 60],
    format_func=lambda x: f"{x}x",
    index=0
)

st.session_state.playback_speed = speed

col1, col2 = st.sidebar.columns(2)

if col1.button(
    "▶ Phát",
    use_container_width=True
):

    st.session_state.playing = True
    st.rerun()


if col2.button(
    "⏸ Tạm dừng",
    use_container_width=True
):

    st.session_state.playing = False
    st.rerun()


# =========================================================
# 9. TUA THEO KHOẢNG THỜI GIAN
# =========================================================

def move_time(minutes):

    current_time = df.iloc[
        st.session_state.current_index
    ]["Thời_gian"]

    target = current_time + pd.Timedelta(
        minutes=minutes
    )

    target = min(
        max(target, min_time),
        max_time
    )

    st.session_state.current_index = (
        find_nearest_index(target)
    )

    st.session_state.playing = False


st.sidebar.subheader("⏩ Tua thời gian")

col1, col2 = st.sidebar.columns(2)

if col1.button("↶ -1 phút", use_container_width=True):
    move_time(-1)

if col2.button("+1 phút ↷", use_container_width=True):
    move_time(1)

col3, col4 = st.sidebar.columns(2)

if col3.button("-1 giờ", use_container_width=True):
    move_time(-60)

if col4.button("+1 giờ", use_container_width=True):
    move_time(60)


col5, col6 = st.sidebar.columns(2)

if col5.button("⏮ Về đầu", use_container_width=True):

    st.session_state.current_index = 0
    st.session_state.playing = False

if col6.button("⏭ Đến cuối", use_container_width=True):

    st.session_state.current_index = total_rows - 1
    st.session_state.playing = False


# =========================================================
# 10. PHÁT LẠI TỰ ĐỘNG
# =========================================================

if st.session_state.playing:

    st_autorefresh(
        interval=1000,
        key="playback_refresh"
    )

    new_index = (
        st.session_state.current_index
        + st.session_state.playback_speed
    )

    st.session_state.current_index = min(
        new_index,
        total_rows - 1
    )

    if st.session_state.current_index >= total_rows - 1:

        st.session_state.playing = False


# =========================================================
# 11. LẤY DỮ LIỆU HIỆN TẠI
# =========================================================

current_index = st.session_state.current_index

current = df.iloc[current_index]

current_time = current["Thời_gian"]

current_status = str(
    current["Ket_qua_tong_hop"]
)


# =========================================================
# 12. THÔNG TIN TỔNG QUAN
# =========================================================

st.divider()

st.subheader("📊 TRẠNG THÁI THIẾT BỊ")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Thời gian hiện tại",
    current_time.strftime("%d/%m/%Y %H:%M:%S")
)

col2.metric(
    "Vị trí bản ghi",
    f"{current_index + 1:,}/{total_rows:,}"
)

col3.metric(
    "Trạng thái máy",
    current_status
)

st.progress(
    (current_index + 1) / total_rows
)


# =========================================================
# 13. HIỂN THỊ CẢNH BÁO
# =========================================================

st.divider()

st.subheader("🚨 KẾT QUẢ GIÁM SÁT")

if current_status == "Bình thường":

    st.success("Thiết bị đang ở trạng thái bình thường.")

elif current_status == "Cần theo dõi":

    st.warning("Thiết bị cần được theo dõi.")

elif current_status == "Cảnh báo":

    st.warning("Phát hiện trạng thái cảnh báo.")

elif current_status == "Nguy cơ cao":

    st.error("Phát hiện nguy cơ sự cố cao.")

else:

    st.info(
        f"Trạng thái thiết bị: {current_status}"
    )


# =========================================================
# 14. THÔNG SỐ 6 CẢM BIẾN
# =========================================================

st.divider()

st.subheader("📡 THÔNG SỐ CẢM BIẾN")

sensor_cols = st.columns(3)

for i, sensor in enumerate(SENSOR_COLUMNS):

    value = current[sensor]

    if pd.notna(value):
        display_value = f"{value:.3f}"
    else:
        display_value = "N/A"

    with sensor_cols[i % 3]:

        st.metric(
            SENSOR_NAMES[sensor],
            display_value
        )


# =========================================================
# 15. BIỂU ĐỒ 6 CẢM BIẾN
# =========================================================

st.divider()

st.subheader("📈 BIỂU ĐỒ DIỄN BIẾN CẢM BIẾN")

history_size = st.selectbox(
    "Số bản ghi lịch sử hiển thị",
    options=[60, 120, 300, 600, 1000],
    index=2
)

start_index = max(
    0,
    current_index - history_size + 1
)

history = df.iloc[
    start_index:current_index + 1
].copy()

for sensor in SENSOR_COLUMNS:

    st.markdown(
        f"**{SENSOR_NAMES[sensor]}**"
    )

    fig = px.line(
        history,
        x="Thời_gian",
        y=sensor,
        labels={
            "Thời_gian": "Thời gian",
            sensor: SENSOR_NAMES[sensor]
        }
    )

    fig.update_layout(
        height=300,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=20, b=20)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# =========================================================
# 16. BẢNG LỊCH SỬ DỮ LIỆU
# =========================================================

st.divider()

st.subheader("📋 LỊCH SỬ DỮ LIỆU")

display_columns = (
    ["Thời_gian"]
    + SENSOR_COLUMNS
    + ["Ket_qua_tong_hop"]
)

st.dataframe(
    history[display_columns].tail(100),
    use_container_width=True,
    hide_index=True
)


# =========================================================
# 17. THỐNG KÊ TRẠNG THÁI
# =========================================================

st.divider()

st.subheader("📊 THỐNG KÊ TRẠNG THÁI TOÀN BỘ DỮ LIỆU")

status_counts = (
    df["Ket_qua_tong_hop"]
    .value_counts()
    .reset_index()
)

status_counts.columns = [
    "Trạng thái",
    "Số lượng"
]

fig_status = px.pie(
    status_counts,
    names="Trạng thái",
    values="Số lượng",
    title="Phân bố trạng thái thiết bị"
)

st.plotly_chart(
    fig_status,
    use_container_width=True
)


# =========================================================
# 18. TẢI DỮ LIỆU CSV
# =========================================================

st.divider()

st.subheader("⬇️ XUẤT DỮ LIỆU")

csv_data = df.to_csv(
    index=False,
    encoding="utf-8-sig"
).encode("utf-8-sig")

st.download_button(
    label="📥 Tải toàn bộ dữ liệu CSV",
    data=csv_data,
    file_name="du_lieu_predictive_maintenance.csv",
    mime="text/csv"
)


# =========================================================
# 19. CHÂN TRANG
# =========================================================

st.divider()

st.caption(
    "Predictive Maintenance Dashboard | "
    "Hệ thống giám sát và bảo trì dự đoán"
)
