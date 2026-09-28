from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

import gspread
from google.oauth2.service_account import Credentials

# 페이지 기본 설정
st.set_page_config(
    page_title="래디시 성장 관찰 일지 🌱", page_icon="🌱", layout="wide"
)

# 구글 시트 연결 함수 (캐싱 활용 - st.secrets 방식)
@st.cache_resource
def get_google_sheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    # Streamlit Cloud Secrets 또는 로컬 secrets.toml에서 안전하게 가져옴
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

# 구글 시트 데이터 불러오기 및 저장 함수
def load_data():
    try:
        client = get_google_sheet_client()
        sheet = client.open("Radish_Growth_Data").sheet1  # 구글 시트 이름
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(
                columns=[
                    "조",
                    "날짜",
                    "키(cm)",
                    "본잎개수",
                    "평균온도(C)",
                    "주간조도(lux)",
                    "물준양(ml)",
                ]
            )
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"구글 시트를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

def append_data(row_data):
    try:
        client = get_google_sheet_client()
        sheet = client.open("Radish_Growth_Data").sheet1
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"데이터 저장 중 오류가 발생했습니다: {e}")
        return False

# --- 사이드바: 로그인 및 조 선택 ---
st.sidebar.title("🌱 래디시 관찰 시스템")
st.sidebar.markdown("---")
selected_group = st.sidebar.selectbox(
    "소속 조를 선택하세요", ["1조", "2조", "3조", "4조", "5조"]
)
st.sidebar.success(f"현재 로그인: **{selected_group}**")

# --- 메인 화면 구성 ---
st.title("🌱 초등학교 래디시(무) 성장 기록장")
st.markdown(
    "우리 조의 래디시가 어떻게 자라고 있는지 기록하고, 다른 조들과 비교해 보세요!"
)

# 데이터 로드
df = load_data()

# 탭 생성 (1. 데이터 입력, 2. 비교 시각화, 3. 전체 요약)
tab1, tab2, tab3 = st.tabs(
    ["📝 데이터 입력하기", "📈 조별/전체 비교 분석", "📊 전체 데이터 요약"]
)

with tab1:
    st.header(f"[{selected_group}] 성장 기록 입력")

    with st.form("growth_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            input_date = st.date_input("관찰 날짜", datetime.now())
            height = st.text_input("키 (cm)", value="0.0")
            leaves = st.text_input("본잎 개수 (개)", value="0")
        with col2:
            temperature = st.text_input("평균 온도 (°C)", value="20.0")
            lux = st.text_input("주간 조도 (lux)", value="500")
            water = st.text_input("준 물의 양 (ml)", value="50")

        submit_button = st.form_submit_button(label="데이터 제출하기")

        if submit_button:
            try:
                h_val = float(height)
                l_val = int(leaves)
                t_val = float(temperature)
                lux_val = float(lux)
                w_val = float(water)

                row = [
                    selected_group,
                    str(input_date),
                    h_val,
                    l_val,
                    t_val,
                    lux_val,
                    w_val,
                ]

                if append_data(row):
                    st.success("데이터가 구글 시트에 성공적으로 저장되었습니다! 🎉")
                    st.rerun()
            except ValueError:
                st.error(
                    "⚠️ 입력값 형식 오류: 키, 온도, 조도, 물 양은 숫자만, 본잎 개수는 정수로 입력해주세요."
                )

with tab2:
    st.header("📈 조별 데이터 비교 시각화")

    if df.empty:
        st.info("아직 입력된 데이터가 없습니다. 데이터를 먼저 입력해주세요.")
    else:
        # X축 선택 항목 확장 (날짜, 주간조도, 평균온도, 물준양 등 선택 가능)
        col_x, _ = st.columns(2)
        with col_x:
            x_axis = st.selectbox(
                "X축 기준 선택", 
                ["날짜", "주간조도(lux)", "평균온도(C)", "물준양(ml)", "키(cm)"], 
                index=0
            )

        st.markdown("---")
        st.subheader("🔍 조별 그래프 비교")

        g_col1, g_col2 = st.columns(2)
        metrics_to_compare = ["키(cm)", "본잎개수", "평균온도(C)", "물준양(ml)"]

        for i, metric in enumerate(metrics_to_compare[:4]):
            target_col = g_col1 if i % 2 == 0 else g_col2
            with target_col:
                st.markdown(f"**[{metric}] 비교 추이**")
                
                # X축이 날짜가 아닐 수도 있으므로 산점도(Scatter)나 선 그래프 유연하게 처리
                if x_axis == "날짜" and len(df) > 1:
                    fig = px.line(
                        df, x=x_axis, y=metric, color="조", markers=True,
                        title=f"{x_axis}별 {metric} 비교", labels={metric: metric, x_axis: x_axis}
                    )
                else:
                    fig = px.scatter(
                        df, x=x_axis, y=metric, color="조",
                        title=f"{x_axis}별 {metric} 비교", labels={metric: metric, x_axis: x_axis}
                    )
                    fig.update_traces(marker=dict(size=10))

                fig.update_layout(
                    dragmode="zoom",
                    hovermode="x unified",
                    margin=dict(l=20, r=20, t=40, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("📊 전체 데이터 요약 및 통계")

    if df.empty:
        st.info("표시할 데이터가 없습니다.")
    else:
        numeric_cols = [
            "키(cm)",
            "본잎개수",
            "평균온도(C)",
            "주간조도(lux)",
            "물준양(ml)",
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        st.subheader("📌 주요 지표 통계 요약")
        summary_df = df[numeric_cols].describe().T[["mean", "max", "min", "std"]]
        summary_df.columns = ["평균", "최대값", "최소값", "표준편차"]
        st.dataframe(summary_df.style.format("{:.2f}"))

        st.subheader("📋 전체 제출 데이터 목록")
        st.dataframe(df, use_container_width=True)