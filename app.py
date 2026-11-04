
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CẤU HÌNH TRANG
# ==========================================

st.set_page_config(
    page_title="Predictive Maintenance",
    page_icon="⚙️",
    layout="wide"
)

st.title("HỆ THỐNG GIÁM SÁT VÀ BẢO TRÌ DỰ ĐOÁN")
st.caption("Predictive Maintenance System")

# ==========================================
# 2. CÁC CỘT DỮ LIỆU
# ==========================================

required_columns = [
    "Thời_gian",
    "Độ_rung_RMS_mm_s",
    "Độ_rung_đỉnh_mm_s",
    "Nhiệt_độ_ổ_trục_C",
    "Dòng_điện_động_cơ_A",
    "Lưu_lượng_m3_h",
    "Áp_suất_đầu_ra_bar",
    "Ket_qua_tong_hop"
]

sensor_columns = [
    "Độ_rung_RMS_mm_s",
    "Độ_rung_đỉnh_mm_s",
    "Nhiệt_độ_ổ_trục_C",
    "Dòng_điện_động_cơ_A",
    "Lưu_lượng_m3_h",
    "Áp_suất_đầu_ra_bar"
]

sensor_names = {
    "Độ_rung_RMS_mm_s": "Độ rung RMS",
    "Độ_rung_đỉnh_mm_s": "Độ rung đỉnh",
    "Nhiệt_độ_ổ_trục_C": "Nhiệt độ ổ trục",
    "Dòng_điện_động_cơ_A": "Dòng điện động cơ",
    "Lưu_lượng_m3_h": "Lưu lượng",
    "Áp_suất_đầu_ra_bar": "Áp suất đầu ra"
}

sensor_units = {
    "Độ_rung_RMS_mm_s": "mm/s",
    "Độ_rung_đỉnh_mm_s": "mm/s",
    "Nhiệt_độ_ổ_trục_C": "°C",
    "Dòng_điện_động_cơ_A": "A",
    "Lưu_lượng_m3_h": "m³/h",
    "Áp_suất_đầu_ra_bar": "bar"
}

# ==========================================
# 3. ĐỌC DỮ LIỆU MẶC ĐỊNH
# ==========================================

@st.cache_data
def load_default_data():
    return pd.read_csv("ket_qua_canh_bao.csv")


# ==========================================
# 4. TẢI FILE CSV
# ==========================================

st.sidebar.header("QUẢN LÝ DỮ LIỆU")

uploaded_file = st.sidebar.file_uploader(
    "Tải file CSV mới",
    type=["csv"]
)

try:

    if uploaded_file is not None:

        df = pd.read_csv(uploaded_file)

        source = uploaded_file.name

    else:

        df = load_default_data()

        source = "ket_qua_canh_bao.csv"

    # ==========================================
    # 5. KIỂM TRA CẤU TRÚC
    # ==========================================

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        st.error(
            "File thiếu các cột bắt buộc: "
            + ", ".join(missing_columns)
        )

        st.stop()

    # ==========================================
    # 6. LÀM SẠCH DỮ LIỆU CƠ BẢN
    # ==========================================

    df["Thời_gian"] = pd.to_datetime(
        df["Thời_gian"],
        errors="coerce"
    )

    for col in sensor_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(
        subset=["Thời_gian"] + sensor_columns
    )

    df = df.sort_values(
        "Thời_gian"
    ).reset_index(drop=True)

    if df.empty:

        st.error("Không có dữ liệu hợp lệ.")

        st.stop()

    # ==========================================
    # 7. KHỞI TẠO TRẠNG THÁI
    # ==========================================

    current_source = (
        source,
        uploaded_file.name if uploaded_file is not None else "default",
        len(df),
        str(df["Thời_gian"].iloc[0]),
        str(df["Thời_gian"].iloc[-1])
    )

    if "data_source" not in st.session_state:
        st.session_state.data_source = None

    if "current_index" not in st.session_state:
        st.session_state.current_index = 0

    if "playing" not in st.session_state:
        st.session_state.playing = False

    if st.session_state.data_source != current_source:

        st.session_state.data_source = current_source
        st.session_state.current_index = 0
        st.session_state.playing = False

    # ==========================================
    # 8. THÔNG TIN NGUỒN DỮ LIỆU
    # ==========================================

    st.sidebar.success(f"Đang sử dụng: {source}")

    st.sidebar.metric(
        "Tổng số bản ghi",
        f"{len(df):,}"
    )

    st.sidebar.write(
        "**Thời gian bắt đầu:**",
        df["Thời_gian"].min().strftime("%d/%m/%Y %H:%M")
    )

    st.sidebar.write(
        "**Thời gian kết thúc:**",
        df["Thời_gian"].max().strftime("%d/%m/%Y %H:%M")
    )

    # ==========================================
    # 9. ĐIỀU KHIỂN TỐC ĐỘ
    # ==========================================

    st.header("1. Điều khiển mô phỏng")

    speed_options = {
        "1x - 1 giây = 1 phút": 1,
        "2x - 1 giây = 2 phút": 2,
        "5x - 1 giây = 5 phút": 5,
        "10x - 1 giây = 10 phút": 10,
        "30x - 1 giây = 30 phút": 30,
        "60x - 1 giây = 1 giờ": 60
    }

    selected_speed = st.selectbox(
        "Tốc độ phát dữ liệu",
        list(speed_options.keys()),
        index=0
    )

    speed = speed_options[selected_speed]

    # ==========================================
    # 10. CÁC NÚT ĐIỀU KHIỂN
    # ==========================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        if st.button("▶ BẮT ĐẦU", use_container_width=True):

            st.session_state.playing = True
            st.rerun()

    with col2:

        if st.button("⏸ TẠM DỪNG", use_container_width=True):

            st.session_state.playing = False
            st.rerun()

    with col3:

        if st.button("▶ TIẾP TỤC", use_container_width=True):

            if st.session_state.current_index >= len(df) - 1:
                st.session_state.current_index = 0

            st.session_state.playing = True
            st.rerun()

    with col4:

        if st.button("↺ ĐẶT LẠI", use_container_width=True):

            st.session_state.playing = False
            st.session_state.current_index = 0
            st.rerun()

    # ==========================================
    # 11. ĐIỀU HƯỚNG THỜI GIAN
    # ==========================================

    st.subheader("Điều hướng thời gian")

    min_time = df["Thời_gian"].min()
    max_time = df["Thời_gian"].max()

    selected_time = st.datetime_input(
        "Chọn ngày và giờ muốn xem",
        value=df.iloc[
            st.session_state.current_index
        ]["Thời_gian"].to_pydatetime(),
        min_value=min_time.to_pydatetime(),
        max_value=max_time.to_pydatetime(),
        key="selected_datetime"
    )

    if st.button("⏩ CHUYỂN ĐẾN THỜI ĐIỂM"):

        target_time = pd.Timestamp(selected_time)

        target_index = (
            df["Thời_gian"] - target_time
        ).abs().idxmin()

        st.session_state.current_index = int(target_index)

        st.rerun()

    # ==========================================
    # 12. TUA NHANH VÀ TUA LÙI
    # ==========================================

    st.subheader("Tua nhanh / Tua lùi")

    col_back, col_forward = st.columns(2)

    with col_back:

        if st.button("⏪ LÙI 60 BẢN GHI", use_container_width=True):

            st.session_state.current_index = max(
                0,
                st.session_state.current_index - 60
            )

            st.rerun()

    with col_forward:

        if st.button("⏩ TIẾN 60 BẢN GHI", use_container_width=True):

            st.session_state.current_index = min(
                len(df) - 1,
                st.session_state.current_index + 60
            )

            st.rerun()

    # ==========================================
    # 13. TỰ ĐỘNG PHÁT DỮ LIỆU
    # ==========================================

    if st.session_state.playing:

        st_autorefresh(
            interval=1000,
            key="auto_refresh"
        )

        st.session_state.current_index = min(
            st.session_state.current_index + speed,
            len(df) - 1
        )

        if st.session_state.current_index >= len(df) - 1:

            st.session_state.playing = False

            st.warning("Đã phát hết dữ liệu!")

    # ==========================================
    # 14. LẤY BẢN GHI HIỆN TẠI
    # ==========================================

    current_index = st.session_state.current_index

    latest = df.iloc[current_index]

    current_time = latest["Thời_gian"]

    st.divider()

    st.progress(
        (current_index + 1) / len(df)
    )

    st.caption(
        f"Đang xem bản ghi {current_index + 1:,} / {len(df):,}"
    )

    # ==========================================
    # 15. TỔNG QUAN THIẾT BỊ
    # ==========================================

    st.header("2. Tổng quan thiết bị")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Thiết bị",
            "PUMP-01"
        )

    with col2:

        st.metric(
            "Trạng thái",
            str(latest["Ket_qua_tong_hop"])
        )

    with col3:

        st.metric(
            "Thời gian mô phỏng",
            current_time.strftime("%H:%M:%S %d/%m/%Y")
        )

    # ==========================================
    # 16. THÔNG SỐ CẢM BIẾN
    # ==========================================

    st.divider()

    st.header("3. Thông số cảm biến")

    cols = st.columns(3)

    for i, sensor in enumerate(sensor_columns):

        with cols[i % 3]:

            st.metric(
                sensor_names[sensor],
                f'{latest[sensor]:.2f} {sensor_units[sensor]}'
            )

    # ==========================================
    # 17. BIỂU ĐỒ LỊCH SỬ
    # ==========================================

    st.divider()

    st.header("4. Biểu đồ cảm biến")

    history = df.iloc[:current_index + 1].tail(500)

    selected_sensor = st.selectbox(
        "Chọn cảm biến để xem biểu đồ",
        sensor_columns,
        format_func=lambda x: sensor_names[x]
    )

    fig = px.line(
        history,
        x="Thời_gian",
        y=selected_sensor,
        title=sensor_names[selected_sensor]
    )

    fig.update_layout(
        xaxis_title="Thời gian",
        yaxis_title=sensor_units[selected_sensor],
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==========================================
    # 18. LỊCH SỬ DỮ LIỆU
    # ==========================================

    st.divider()

    st.header("5. Lịch sử dữ liệu đã phát")

    st.dataframe(
        df.iloc[:current_index + 1].tail(10),
        use_container_width=True
    )

except FileNotFoundError:

    st.error(
        "Không tìm thấy ket_qua_canh_bao.csv. "
        "Hãy kiểm tra vị trí file."
    )

except Exception as e:

    st.error(f"Có lỗi xảy ra: {e}")
