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

from src import cost_model, data_loader

st.set_page_config(page_title="자동차 생애주기 분석 대시보드", layout="wide")

st.title("🚗 자동차 생애주기 분석 대시보드")
st.caption("공공데이터(KOSIS·서울 열린데이터광장) 기반 차량 교체주기 · 주행거리 · 연령대별 보유 현황 · 유지비 · 총소유비용 분석")


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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 차급별 평균 사용기간", "🛣️ 주행거리 분석", "👥 연령대별 보유 현황",
    "💰 유지비 분석", "🧮 총소유비용(TCO) 계산기", "🔍 내 차 비교",
])

# ── Tab 1: 차급별 평균 사용기간 ──────────────────────────
with tab1:
    st.subheader("차급별 평균 사용(교체) 기간")
    source_badge(is_real_lifespan)

    fig = px.bar(
        df_lifespan.sort_values("평균_사용연수"),
        x="차급", y="평균_사용연수", text="평균_사용연수",
        labels={"평균_사용연수": "평균 사용연수 (년)"}, color="차급",
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df_lifespan, width="stretch")

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
        st.plotly_chart(fig_trend, width="stretch")

# ── Tab 2: 주행거리 분석 ─────────────────────────────────
with tab2:
    st.subheader("차급별 평균 누적주행거리")
    source_badge(is_real_mileage)

    fig_m = px.bar(
        df_mileage.sort_values("평균_누적주행거리_km"),
        x="차급", y="평균_누적주행거리_km", text="평균_누적주행거리_km",
        labels={"평균_누적주행거리_km": "평균 누적주행거리 (km)"}, color="차급",
    )
    fig_m.update_traces(textposition="outside")
    st.plotly_chart(fig_m, width="stretch")
    st.dataframe(df_mileage, width="stretch")

# ── Tab 3: 연령대별 자동차 보유 현황 ─────────────────────
with tab3:
    st.subheader("연령대별 자동차 등록(보유) 현황")
    source_badge(is_real_age)
    if is_real_age:
        st.caption("출처: 서울 열린데이터광장 — 자동차등록현황(성별/연령별), 2025년 기준 (서울시 한정)")

    fig2 = px.bar(
        df_age, x="연령대", y="등록대수", text="비중(%)",
        labels={"등록대수": "등록대수 (대)"}, color="연령대",
    )
    fig2.update_traces(texttemplate="%{text}%", textposition="outside")
    st.plotly_chart(fig2, width="stretch")
    st.dataframe(df_age, width="stretch")

    if is_real_age_gender and not df_age_gender.empty:
        age_order = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대 이상"]

        st.markdown("#### 성별 비교 (최신연도)")
        latest_year = df_age_gender["연도"].max()
        sub = df_age_gender[df_age_gender["연도"] == latest_year]
        fig2b = px.bar(
            sub, x="연령대", y="등록대수", color="성별", barmode="group",
            category_orders={"연령대": age_order}, labels={"등록대수": "등록대수 (대)"},
        )
        st.plotly_chart(fig2b, width="stretch")

        st.markdown("#### 연도별 추이 (2023~2025)")
        trend_sub = df_age_gender.groupby(["연도", "연령대"], as_index=False)["등록대수"].sum()
        fig2c = px.line(
            trend_sub, x="연도", y="등록대수", color="연령대", markers=True,
            category_orders={"연령대": age_order},
        )
        st.plotly_chart(fig2c, width="stretch")

# ── Tab 4: 유지비 분석 ───────────────────────────────────
with tab4:
    st.subheader("차급 · 연료별 연간 예상 유지비 (새 차 기준)")
    source_badge(is_real_cost)

    fig3 = px.bar(
        df_cost, x="차급", y="연간_예상유지비_만원", color="연료", barmode="group",
        labels={"연간_예상유지비_만원": "연간 예상 유지비 (만원)"},
    )
    st.plotly_chart(fig3, width="stretch")
    st.dataframe(df_cost, width="stretch")

    if is_real_cost:
        st.markdown(
            "> **계산 방법**: 연간 유지비 = **자동차세**(배기량 기준, 차급별 대표 모델 배기량 적용, 지방교육세 포함) "
            "+ **유류비**(연간 주행거리 ÷ 연비 × 오피넷 전국 평균 유가, 2026년 9월). "
            "연간 주행거리는 실제 데이터(평균 누적주행거리 ÷ 평균 사용연수)로 역산했고, "
            "연비는 차급별 대표값을 **가정**했습니다.\n>\n"
            "> ⚠️ 보험료·정비비는 운전자 편차가 커서 제외했습니다. 실제 체감 유지비보다 낮게 나올 수 있습니다."
        )

# ── Tab 5: TCO 계산기 ────────────────────────────────────
with tab5:
    st.subheader("총소유비용(TCO) 계산기 — 이 차를 N년 타면 얼마가 들까?")
    st.caption(
        "세금과 기름값처럼 '타는 동안 계속 나가는 돈'을 보유 기간만큼 합산합니다. "
        "차를 살 때 드는 구매가·감가상각, 보험료·정비비는 포함하지 않습니다."
    )

    km_by_class = cost_model.annual_km_by_class(df_lifespan, df_mileage)
    classes = [c for c in cost_model.CAR_CLASSES if c in km_by_class]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        tco_class = st.selectbox("차급", classes, index=min(2, len(classes) - 1), key="tco_class")
    with c2:
        tco_fuel = st.selectbox("연료", cost_model.FUELS, key="tco_fuel")
    with c3:
        tco_years = st.slider("보유 예상 기간(년)", 1, 20, 10, key="tco_years")
    with c4:
        tco_buy_age = st.number_input("구매 시점의 차령(새 차=0년)", min_value=0, max_value=15, value=0, key="tco_buy_age")

    start_age = int(tco_buy_age) + 1  # 새 차 = 1년차부터
    table = cost_model.yearly_cost_table(tco_class, tco_fuel, km_by_class[tco_class], tco_years, start_age)

    total_man = table["누적합계_원"].iloc[-1] / 10_000
    m1, m2, m3 = st.columns(3)
    m1.metric(f"{tco_years}년 총소유비용", f"{total_man:,.0f}만원")
    m2.metric("연평균", f"{total_man / tco_years:,.0f}만원")
    m3.metric("월평균", f"{total_man / tco_years / 12:,.1f}만원")

    st.markdown("#### 연도별 비용 구성 (자동차세 vs 유류비)")
    long_df = table.melt(
        id_vars=["보유연차", "차령"], value_vars=["자동차세_원", "유류비_원"],
        var_name="항목", value_name="금액_원",
    )
    long_df["금액_만원"] = long_df["금액_원"] / 10_000
    long_df["항목"] = long_df["항목"].map({"자동차세_원": "자동차세", "유류비_원": "유류비"})
    fig_year = px.bar(
        long_df, x="보유연차", y="금액_만원", color="항목", barmode="stack",
        labels={"금액_만원": "연간 비용 (만원)", "보유연차": "보유 N년차"},
    )
    st.plotly_chart(fig_year, width="stretch")
    st.caption("차령 3년차부터 자동차세가 매년 5%씩 줄어(최대 50%) 막대의 자동차세 부분이 점점 작아집니다.")

    st.markdown("#### 누적 비용 추이")
    table_view = table.assign(누적합계_만원=table["누적합계_원"] / 10_000)
    fig_cum = px.line(
        table_view, x="보유연차", y="누적합계_만원", markers=True,
        labels={"누적합계_만원": "누적 비용 (만원)", "보유연차": "보유 N년차"},
    )
    st.plotly_chart(fig_cum, width="stretch")

    st.markdown(f"#### 같은 조건({tco_fuel}, {tco_years}년 보유)에서 차급 비교")
    cmp_df = cost_model.compare_classes(km_by_class, tco_fuel, tco_years, start_age)
    selected_total = cmp_df.loc[cmp_df["차급"] == tco_class, "총소유비용_만원"].iloc[0]
    cmp_df["선택 차급 대비(만원)"] = (cmp_df["총소유비용_만원"] - selected_total).round(0)

    cmp_long = cmp_df.melt(
        id_vars="차급", value_vars=["자동차세_합계_만원", "유류비_합계_만원"],
        var_name="항목", value_name="금액_만원",
    )
    cmp_long["항목"] = cmp_long["항목"].map({"자동차세_합계_만원": "자동차세", "유류비_합계_만원": "유류비"})
    fig_cmp = px.bar(
        cmp_long, x="차급", y="금액_만원", color="항목", barmode="stack",
        category_orders={"차급": cmp_df["차급"].tolist()},
        labels={"금액_만원": f"{tco_years}년 총비용 (만원)"},
    )
    st.plotly_chart(fig_cmp, width="stretch")
    st.dataframe(
        cmp_df.assign(총소유비용_만원=cmp_df["총소유비용_만원"].round(0)).round(0),
        width="stretch", hide_index=True,
    )

    with st.expander("계산식과 가정 보기 (발표/보고서 근거)"):
        km_txt = ", ".join(f"{c} {km_by_class[c]:,.0f}km" for c in classes)
        st.markdown(
            f"""
**연간 비용(n년차) = 자동차세(n년차) + 유류비** → **TCO = 연간 비용의 N년 합계**

- **자동차세** = 배기량 × cc당 세율(1,000cc 이하 80원 / 1,600cc 이하 140원 / 초과 200원) × (1 − 차령 경감률) × 1.3(지방교육세 30%)
- **차령 경감률** = 3년차 5%, 이후 매년 +5%p, 최대 50%(12년차 이상)
- **유류비** = 연간 주행거리 ÷ 연비 × 유가 (휘발유 {cost_model.FUEL_PRICE_PER_LITER['휘발유']:,}원/L, 경유 {cost_model.FUEL_PRICE_PER_LITER['경유']:,}원/L — 오피넷 2026년 9월 전국 평균)
- **연간 주행거리** = 평균 누적주행거리 ÷ 평균 사용연수 → {km_txt}

**가정(공식 통계 아님)**: 차급별 대표 배기량(모닝·아반떼·쏘나타·그랜저), 차급별 대표 연비, 연료·세율·유가가 보유 기간 동안 변하지 않는다는 가정
**제외 항목**: 구매가·감가상각, 보험료, 정비·소모품비, 주차·통행료
"""
        )

# ── Tab 6: 내 차 비교 ────────────────────────────────────
with tab6:
    st.subheader("내 차 정보를 입력하고 평균과 비교해보세요")

    col1, col2, col3 = st.columns(3)
    with col1:
        my_class = st.selectbox("차급", df_lifespan["차급"].unique(), key="my_class")
    with col2:
        my_fuel = st.selectbox("연료 타입", df_cost["연료"].unique(), key="my_fuel")
    with col3:
        my_years = st.number_input("현재까지 사용 연수", min_value=0, max_value=30, value=5, key="my_years")

    my_km = st.number_input("현재까지 누적 주행거리 (km)", min_value=0, max_value=500_000, value=60_000, step=1_000, key="my_km")

    avg_lifespan = df_lifespan.loc[df_lifespan["차급"] == my_class, "평균_사용연수"].values[0]
    avg_km = (
        df_mileage.loc[df_mileage["차급"] == my_class, "평균_누적주행거리_km"].values[0]
        if my_class in df_mileage["차급"].values else None
    )
    avg_cost = df_cost.loc[
        (df_cost["차급"] == my_class) & (df_cost["연료"] == my_fuel), "연간_예상유지비_만원"
    ].values[0]

    remaining = avg_lifespan - my_years

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("평균 교체 시점(연수)", f"{avg_lifespan:.1f}년")
    m2.metric(
        "예상 잔여 사용 기간",
        f"{remaining:.1f}년" if remaining > 0 else "교체 시기 도래",
        delta=f"{-remaining:.1f}년 초과" if remaining < 0 else None,
    )
    if avg_km is not None:
        m3.metric("같은 차급 평균 누적주행거리", f"{avg_km:,.0f}km", delta=f"{my_km - avg_km:+,.0f}km (내 차 대비)")
    m4.metric("같은 조건 평균 연간 유지비", f"{avg_cost:.0f}만원")

    if remaining <= 0:
        st.info("📌 같은 차급 평균 사용연수를 이미 넘어섰어요. 교체를 고려해볼 시점일 수 있어요.")
    elif remaining <= 2:
        st.info("📌 평균 교체 시점이 얼마 남지 않았어요. 슬슬 다음 차량을 알아볼 시기예요.")
    else:
        st.success("📌 아직 평균 대비 여유가 있는 편이에요.")

st.markdown("---")
st.caption(
    "데이터 출처: KOSIS(국가통계포털) 자동차검사현황(한국교통안전공단), "
    "서울 열린데이터광장(자동차등록현황 성별/연령별), 지방세법(자동차세), 오피넷/한국석유공사(유가)"
)
