"""
app.py — 자동차 생애주기 분석 대시보드 (Streamlit)

실행: streamlit run app/app.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src import data_loader

st.set_page_config(page_title="자동차 생애주기 분석 대시보드", layout="wide")

st.title("🚗 자동차 생애주기 분석 대시보드")
st.caption("공공데이터(KOSIS·서울 열린데이터광장) 기반 차량 교체주기 · 주행거리 · 연령대별 보유 현황 · 유지비 분석 및 내 차 비교")


def source_badge(is_real: bool):
    if is_real:
        st.caption("✅ 실제 공공데이터 기반")
    else:
        st.caption("⚠️ 샘플(가상) 데이터 — 실제 데이터 미연동 상태")


# ── 데이터 로드 ──────────────────────────────────────────
df_lifespan, is_real_lifespan = data_loader.load_lifespan_data()
df_mileage, is_real_mileage = data_loader.load_mileage_data()
df_trend, is_real_trend = data_loader.load_lifespan_trend()
df_age, is_real_age = data_loader.load_age_distribution_data()
df_age_gender, is_real_age_gender = data_loader.load_age_gender_trend()
df_cost, is_real_cost = data_loader.load_maintenance_cost_data()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 차급별 평균 사용기간", "🛣️ 주행거리 분석", "👥 연령대별 보유 현황", "💰 유지비 분석", "🔍 내 차 비교"]
)

# ── Tab 1: 차급별 평균 사용기간 ──────────────────────────
with tab1:
    st.subheader("차급별 평균 사용(교체) 기간")
    source_badge(is_real_lifespan)

    fig = px.bar(
        df_lifespan.sort_values("평균_사용연수"),
        x="차급", y="평균_사용연수",
        text="평균_사용연수",
        labels={"평균_사용연수": "평균 사용연수 (년)"},
        color="차급",
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_lifespan, use_container_width=True)

    if is_real_lifespan:
        st.caption(
            "⚠️ '소형' 차급은 표본수가 다른 차급 대비 현저히 적어(최근 소형 승용차 판매 급감) "
            "평균값의 대표성이 낮을 수 있습니다. 해석 시 참고하세요."
        )
        st.markdown(
            "> **계산 방법**: KOSIS는 '5~6년', '7~8년' 같은 구간별 검사대수만 제공하므로, "
            "각 구간의 중간값(예: 5~6년 → 5.5년, 15년 이상 → 18년으로 가정)을 검사대수로 "
            "가중평균하여 계산했습니다."
        )

    if is_real_trend and not df_trend.empty:
        st.markdown("#### 연도별 추이 (2015~2024)")
        fig_trend = px.line(
            df_trend, x="연도", y="평균_사용연수", color="차급", markers=True,
            labels={"평균_사용연수": "평균 사용연수 (년)"},
        )
        st.plotly_chart(fig_trend, use_container_width=True)

# ── Tab 2: 주행거리 분석 ─────────────────────────────────
with tab2:
    st.subheader("차급별 평균 누적주행거리")
    source_badge(is_real_mileage)

    fig_m = px.bar(
        df_mileage.sort_values("평균_누적주행거리_km"),
        x="차급", y="평균_누적주행거리_km",
        text="평균_누적주행거리_km",
        labels={"평균_누적주행거리_km": "평균 누적주행거리 (km)"},
        color="차급",
    )
    fig_m.update_traces(textposition="outside")
    st.plotly_chart(fig_m, use_container_width=True)
    st.dataframe(df_mileage, use_container_width=True)

# ── Tab 3: 연령대별 자동차 보유 현황 ─────────────────────
with tab3:
    st.subheader("연령대별 자동차 등록(보유) 현황")
    source_badge(is_real_age)
    if is_real_age:
        st.caption("출처: 서울 열린데이터광장 — 자동차등록현황(성별/연령별), 2025년 기준")

    fig2 = px.bar(
        df_age, x="연령대", y="등록대수",
        text="비중(%)",
        labels={"등록대수": "등록대수 (대)"},
        color="연령대",
    )
    fig2.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df_age, use_container_width=True)

    if is_real_age_gender and not df_age_gender.empty:
        st.markdown("#### 성별 비교 (최신연도)")
        latest_year = df_age_gender["연도"].max()
        sub = df_age_gender[df_age_gender["연도"] == latest_year]
        order = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대 이상"]
        fig2b = px.bar(
            sub, x="연령대", y="등록대수", color="성별", barmode="group",
            category_orders={"연령대": order},
            labels={"등록대수": "등록대수 (대)"},
        )
        st.plotly_chart(fig2b, use_container_width=True)

        st.markdown("#### 연도별 추이 (2023~2025)")
        trend_sub = df_age_gender.groupby(["연도", "연령대"], as_index=False)["등록대수"].sum()
        fig2c = px.line(
            trend_sub, x="연도", y="등록대수", color="연령대", markers=True,
            category_orders={"연령대": order},
        )
        st.plotly_chart(fig2c, use_container_width=True)

# ── Tab 4: 유지비 분석 ───────────────────────────────────
with tab4:
    st.subheader("차급 · 연료별 연간 예상 유지비")
    source_badge(is_real_cost)

    fig3 = px.bar(
        df_cost, x="차급", y="연간_예상유지비_만원", color="연료",
        barmode="group",
        labels={"연간_예상유지비_만원": "연간 예상 유지비 (만원)"},
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(df_cost, use_container_width=True)

    if is_real_cost:
        st.markdown(
            "> **계산 방법**: 유지비 = **자동차세**(지방세법 시행령, 배기량 기준 — 차급별 대표 모델 "
            "배기량 적용) + **유류비**(실제 평균 주행거리 ÷ 공인연비 × 오피넷 전국 평균 유가, "
            "2026년 9월 기준). 연간 주행거리는 실제 데이터(평균 누적주행거리 ÷ 평균 사용연수)로 "
            "역산했습니다.\n>\n"
            "> ⚠️ **보험료·정비비는 운전자 개인/이력에 따른 편차가 너무 커서 신뢰할 수 있는 공식 "
            "평균 통계가 없어 이번 분석에서는 제외했습니다.** 따라서 실제 체감 유지비보다는 낮게 "
            "나올 수 있습니다."
        )

# ── Tab 5: 내 차 비교 ────────────────────────────────────
with tab5:
    st.subheader("내 차 정보를 입력하고 평균과 비교해보세요")

    col1, col2, col3 = st.columns(3)
    with col1:
        my_class = st.selectbox("차급", df_lifespan["차급"].unique())
    with col2:
        my_fuel = st.selectbox("연료 타입", df_cost["연료"].unique())
    with col3:
        my_years = st.number_input("현재까지 사용 연수", min_value=0, max_value=30, value=5)

    my_km = st.number_input("현재까지 누적 주행거리 (km)", min_value=0, max_value=500_000, value=60_000, step=1_000)

    avg_lifespan = df_lifespan.loc[df_lifespan["차급"] == my_class, "평균_사용연수"].values[0]
    avg_km = df_mileage.loc[df_mileage["차급"] == my_class, "평균_누적주행거리_km"].values[0] \
        if my_class in df_mileage["차급"].values else None
    avg_cost = df_cost.loc[
        (df_cost["차급"] == my_class) & (df_cost["연료"] == my_fuel),
        "연간_예상유지비_만원",
    ].values[0]

    remaining = avg_lifespan - my_years

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균 교체 시점(연수)", f"{avg_lifespan:.1f}년")
    c2.metric(
        "예상 잔여 사용 기간",
        f"{remaining:.1f}년" if remaining > 0 else "교체 시기 도래",
        delta=f"{-remaining:.1f}년 초과" if remaining < 0 else None,
    )
    if avg_km is not None:
        km_diff = my_km - avg_km
        c3.metric("같은 차급 평균 누적주행거리", f"{avg_km:,.0f}km", delta=f"{km_diff:+,.0f}km (내 차 대비)")
    c4.metric("같은 조건 평균 연간 유지비", f"{avg_cost:.0f}만원")

    if remaining <= 0:
        st.info("📌 같은 차급 평균 사용연수를 이미 넘어섰어요. 교체를 고려해볼 시점일 수 있어요.")
    elif remaining <= 2:
        st.info("📌 평균 교체 시점이 얼마 남지 않았어요. 슬슬 다음 차량을 알아볼 시기예요.")
    else:
        st.success("📌 아직 평균 대비 여유가 있는 편이에요.")

st.markdown("---")
st.caption(
    "데이터 출처: KOSIS(국가통계포털) 자동차검사현황(한국교통안전공단), "
    "서울 열린데이터광장(자동차등록현황 성별/연령별), 지방세법 시행령(자동차세), "
    "오피넷/한국석유공사(유가)"
)
