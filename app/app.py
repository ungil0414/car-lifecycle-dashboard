"""
app.py — 자동차 생애주기 분석 대시보드 (Streamlit)

실행: streamlit run app/app.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import cost_model, data_loader, sensitivity

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

tab1, tab2, tab3, tab4, tab5, tab_model, tab_sens, tab6 = st.tabs([
    "📊 차급별 평균 사용기간", "🛣️ 주행거리 분석", "👥 연령대별 보유 현황",
    "💰 유지비 분석", "🧮 총소유비용(TCO) 계산기", "🚗 모델별 TCO 비교", "🎯 민감도 분석", "🔍 내 차 비교",
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
            "> ⚠️ 이 탭의 유지비는 자동차세+유류비만 포함합니다(보험료는 🧮 TCO 계산기 탭에서 반영). 실제 체감 유지비보다 낮게 나올 수 있습니다."
        )

# ── Tab 5: TCO 계산기 ────────────────────────────────────
with tab5:
    st.subheader("총소유비용(TCO) 계산기 — 이 차를 N년 타면 얼마가 들까?")
    st.caption(
        "세금과 기름값처럼 '타는 동안 계속 나가는 돈'을 보유 기간만큼 합산합니다. "
        "차를 살 때 드는 구매가·감가상각, 정비비는 포함하지 않습니다."
    )

    km_by_class = cost_model.annual_km_by_class(df_lifespan, df_mileage)
    classes = [c for c in cost_model.CAR_CLASSES if c in km_by_class]

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        tco_class = st.selectbox("차급", classes, index=min(2, len(classes) - 1), key="tco_class")
    with c2:
        tco_fuel = st.selectbox("연료", cost_model.FUELS, key="tco_fuel")
    with c3:
        tco_years = st.slider("보유 예상 기간(년)", 1, 20, 10, key="tco_years")
    with c4:
        tco_buy_age = st.number_input("구매 시점의 차령(새 차=0년)", min_value=0, max_value=15, value=0, key="tco_buy_age")
    with c5:
        tco_ins_man = st.number_input(
            "연 보험료(만원)", min_value=0, max_value=300,
            value=int(cost_model.AVG_INSURANCE_PREMIUM_WON / 10_000), step=5, key="tco_insurance",
            help="기본값은 보험개발원 2025년 개인용 자동차보험 1대당 평균(약 68만원). 나이·경력·차종에 따라 달라지니 본인 조건에 맞게 바꿔보세요.",
        )
    insurance_won = tco_ins_man * 10_000

    start_age = int(tco_buy_age) + 1  # 새 차 = 1년차부터
    table = cost_model.yearly_cost_table(tco_class, tco_fuel, km_by_class[tco_class], tco_years, start_age, insurance_won)

    total_man = table["누적합계_원"].iloc[-1] / 10_000
    m1, m2, m3 = st.columns(3)
    m1.metric(f"{tco_years}년 총소유비용", f"{total_man:,.0f}만원")
    m2.metric("연평균", f"{total_man / tco_years:,.0f}만원")
    m3.metric("월평균", f"{total_man / tco_years / 12:,.1f}만원")

    st.markdown("#### 연도별 비용 구성 (자동차세 · 유류비 · 보험료)")
    long_df = table.melt(
        id_vars=["보유연차", "차령"], value_vars=["자동차세_원", "유류비_원", "보험료_원"],
        var_name="항목", value_name="금액_원",
    )
    long_df["금액_만원"] = long_df["금액_원"] / 10_000
    long_df["항목"] = long_df["항목"].map({"자동차세_원": "자동차세", "유류비_원": "유류비", "보험료_원": "보험료"})
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
    cmp_df = cost_model.compare_classes(km_by_class, tco_fuel, tco_years, start_age, insurance_won)
    selected_total = cmp_df.loc[cmp_df["차급"] == tco_class, "총소유비용_만원"].iloc[0]
    cmp_df["선택 차급 대비(만원)"] = (cmp_df["총소유비용_만원"] - selected_total).round(0)

    cmp_long = cmp_df.melt(
        id_vars="차급", value_vars=["자동차세_합계_만원", "유류비_합계_만원", "보험료_합계_만원"],
        var_name="항목", value_name="금액_만원",
    )
    cmp_long["항목"] = cmp_long["항목"].map({"자동차세_합계_만원": "자동차세", "유류비_합계_만원": "유류비", "보험료_합계_만원": "보험료"})
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
**연간 비용(n년차) = 자동차세(n년차) + 유류비 + 보험료** → **TCO = 연간 비용의 N년 합계**

- **자동차세** = 배기량 × cc당 세율(1,000cc 이하 80원 / 1,600cc 이하 140원 / 초과 200원) × (1 − 차령 경감률) × 1.3(지방교육세 30%)
- **차령 경감률** = 3년차 5%, 이후 매년 +5%p, 최대 50%(12년차 이상)
- **유류비** = 연간 주행거리 ÷ 연비 × 유가 (휘발유 {cost_model.FUEL_PRICE_PER_LITER['휘발유']:,}원/L, 경유 {cost_model.FUEL_PRICE_PER_LITER['경유']:,}원/L — 오피넷 2026년 9월 전국 평균)
- **보험료** = 개인용 자동차보험 1대당 연평균 보험료 약 68만원(보험개발원, 2025년)을 기본값으로 쓰고 직접 조정 가능. 차급·연령·경력별 공식 평균은 확인하지 못해 모든 차급에 같은 값을 적용
- **연간 주행거리** = 평균 누적주행거리 ÷ 평균 사용연수 → {km_txt}

**가정(공식 통계 아님)**: 차급별 대표 배기량(모닝·아반떼·쏘나타·그랜저), 차급별 대표 연비, 연료·세율·유가·보험료가 보유 기간 동안 변하지 않는다는 가정
**제외 항목**: 구매가·감가상각, 정비·소모품비, 주차·통행료
"""
        )

# ── Tab: 모델별 TCO 비교 ─────────────────────────────────
with tab_model:
    st.subheader("모델별 TCO 비교 — 그랜저 vs K5 vs 쏘나타, 몇 년 타면 얼마?")
    st.caption(
        "현대·기아 대표 모델의 실제 배기량과 공식 복합연비를 넣어 자동차세·유류비·보험료를 계산합니다. "
        "신차 구매가와 중고 매각가의 차이(감가상각)도 포함합니다. (가솔린 기본 엔진·기본 트림 기준, 정비비·옵션 제외)"
    )
    km_by_class_m = cost_model.annual_km_by_class(df_lifespan, df_mileage)

    m_c1, m_c2, m_c3, m_c4, m_c5 = st.columns(5)
    with m_c1:
        picked = st.multiselect(
            "비교할 모델 (2개 이상)", list(cost_model.MODEL_SPECS.keys()),
            default=["쏘나타", "K5", "그랜저"], key="model_pick",
        )
    with m_c2:
        m_years = st.slider("보유 예상 기간(년)", 1, 20, 10, key="model_years")
    with m_c3:
        m_buy_age = st.number_input("구매 시점의 차령(새 차=0년)", min_value=0, max_value=15, value=0, key="model_buy_age")
    with m_c4:
        m_ins = st.number_input(
            "연 보험료(만원)", min_value=0, max_value=300,
            value=int(cost_model.AVG_INSURANCE_PREMIUM_WON / 10_000), step=5, key="model_insurance",
        )
    with m_c5:
        scenario = st.radio(
            "중고 시세 시나리오", cost_model.RESIDUAL_SCENARIOS, index=1, key="model_scenario",
            help="낙관=값이 덜 떨어짐, 비관=더 떨어짐. 아래 '제원 출처와 한계'에서 잔존가치율을 볼 수 있어요.",
        )

    if len(picked) < 2:
        st.info("모델을 2개 이상 골라주세요.")
    else:
        res = cost_model.compare_models(picked, km_by_class_m, m_years, int(m_buy_age) + 1, m_ins * 10_000, scenario=scenario)
        cheapest = res.iloc[0]
        priciest = res.iloc[-1]
        k1, k2, k3 = st.columns(3)
        k1.metric("가장 저렴", f"{cheapest['모델']} {cheapest['총소유비용_만원']:,.0f}만원")
        k2.metric("가장 비쌈", f"{priciest['모델']} {priciest['총소유비용_만원']:,.0f}만원")
        k3.metric(f"{m_years}년 차이", f"{priciest['총소유비용_만원'] - cheapest['총소유비용_만원']:,.0f}만원")
        st.caption(
            f"시세 시나리오({scenario}) 기준입니다. 낙관~비관 범위로 보면 "
            + ", ".join(f"{r['모델']} {r['총소유비용_낙관_만원']:,.0f}~{r['총소유비용_비관_만원']:,.0f}만원" for _, r in res.iterrows())
            + "."
        )

        long_m = res.melt(
            id_vars="모델", value_vars=["감가상각_합계_만원", "자동차세_합계_만원", "유류비_합계_만원", "보험료_합계_만원"],
            var_name="항목", value_name="금액_만원",
        )
        long_m["항목"] = long_m["항목"].map(
            {"감가상각_합계_만원": "감가상각", "자동차세_합계_만원": "자동차세", "유류비_합계_만원": "유류비", "보험료_합계_만원": "보험료"})
        fig_m = px.bar(
            long_m, x="모델", y="금액_만원", color="항목", barmode="stack",
            category_orders={"모델": res["모델"].tolist()},
            labels={"금액_만원": f"{m_years}년 총비용 (만원)"},
        )
        st.plotly_chart(fig_m, width="stretch")
        st.dataframe(
            res.assign(총소유비용_만원=res["총소유비용_만원"].round(0)).round(0),
            width="stretch", hide_index=True,
        )

    with st.expander("제원 출처와 한계 (발표/보고서 근거)"):
        spec_df = pd.DataFrame(cost_model.MODEL_SPECS).T.reset_index().rename(columns={"index": "모델"})
        st.dataframe(spec_df, width="stretch", hide_index=True)
        resid_df = pd.DataFrame({
            sc: {f"{y}년": f"{cost_model.residual_rate(y, sc) * 100:.0f}%" for y in (1, 3, 5, 7, 10)}
            for sc in cost_model.RESIDUAL_SCENARIOS
        })
        st.markdown("**신차 대비 중고 잔존가치율 (시나리오)**")
        st.dataframe(resid_df, width="stretch")
        st.markdown(
            """
- 배기량·복합연비는 제조사 공식 제원(기아 공식 사이트, 카눈 제원 페이지)에서 확인한 값입니다. 연비는 타이어 크기에 따라 달라 **중간 크기 타이어 기준**을 썼고, 스포티지는 범위(10.5~12.3)의 중간값입니다.
- **모델별 사용기간·주행거리 통계는 공공데이터에 없어서**, 연간 주행거리는 모델이 속한 **차급의 평균값**을 그대로 썼습니다. 즉 모델 간 차이는 배기량(자동차세)·연비(유류비)에서만 생깁니다.
- 차급은 승용차 배기량 구분(경형 1,000cc 미만 / 소형 1,600cc 미만 / 중형 2,000cc 미만 / 대형 2,000cc 이상)을 따랐습니다. 그래서 1,598cc인 투싼·스포티지도 **'소형'**으로 분류되어, 표본이 적고 사용연수가 길게 나오는 소형 차급의 주행거리가 적용됩니다.
- 보험료는 모든 모델에 같은 평균값을 적용했습니다(앱에서 조정 가능). 정비비와 옵션은 제외했습니다.
- **감가상각** = 신차가 × (구매 시점 잔존율 − 매각 시점 잔존율). 신차가는 가솔린 **기본(최저) 트림** 가격이며 조사 시점이 모델마다 다릅니다(투싼은 2024년형 가격, 그랜저는 2025년형 개소세 인하가).
- **잔존가치율은 공식 통계가 아니라 가정입니다.** 공개된 두 참고자료(calcmo.kr, telarum.com)의 곡선을 낙관/비관 시나리오로 쓰고 기본은 둘의 평균입니다. 두 자료 모두 조사기관·표본이 명확하지 않아 단정하지 않고 범위로 제시했습니다. 7·10년 값(비관)과 10년 초과 구간은 추정입니다.
- K3는 신차 가격을 확인하지 못해 비교 목록에서 뺐습니다.
"""
        )

# ── Tab: 민감도 분석 ─────────────────────────────────────
@st.cache_data(show_spinner=False)
def _cached_rank(names, km_items, years, buy_age, insurance_won, scenario, swing):
    return sensitivity.rank_stability(list(names), dict(km_items), years, buy_age, insurance_won,
                                      scenario=scenario, swing=swing, n_draws=1000)


with tab_sens:
    st.subheader("민감도 분석 — 가정이 틀려도 결론이 유지될까?")
    st.caption(
        "TCO에는 공식 통계가 아닌 가정(연비·유가·보험료·감가상각·주행거리)이 들어갑니다. "
        "이 가정들을 흔들어서 ① 어떤 가정이 결과에 가장 큰 영향을 주는지, ② 모델 순위가 얼마나 유지되는지 확인합니다."
    )
    km_by_class_s = cost_model.annual_km_by_class(df_lifespan, df_mileage)

    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        s_years = st.slider("보유 기간(년)", 1, 20, 5, key="sens_years")
    with s2:
        s_swing = st.slider("가정 변동폭(±%)", 5, 40, 20, step=5, key="sens_swing") / 100
    with s3:
        s_ins = st.number_input("연 보험료(만원)", min_value=0, max_value=300,
                                value=int(cost_model.AVG_INSURANCE_PREMIUM_WON / 10_000), step=5, key="sens_ins")
    with s4:
        s_scn = st.radio("시세 시나리오", cost_model.RESIDUAL_SCENARIOS, index=1, key="sens_scn")
    with s5:
        s_buy = st.number_input("구매 시 차령(새 차=0)", min_value=0, max_value=15, value=0, key="sens_buy")

    all_models = list(cost_model.MODEL_SPECS.keys())
    s_models = st.multiselect("분석할 모델 (2개 이상)", all_models, default=all_models, key="sens_models")

    if len(s_models) < 2:
        st.info("모델을 2개 이상 골라주세요.")
    else:
        st.markdown("#### ① 어떤 가정이 가장 중요할까? (가정 하나씩만 흔들기)")
        t_model = st.selectbox("모델 선택", s_models, index=len(s_models) - 1, key="sens_tornado_model")
        torn = sensitivity.tornado(t_model, km_by_class_s, s_years, int(s_buy), s_ins * 10_000,
                                   scenario=s_scn, swing=s_swing)
        base_man = torn.attrs["base_man"]
        torn_plot = torn.iloc[::-1]
        fig_t = go.Figure()
        fig_t.add_bar(y=torn_plot["가정"], x=torn_plot["−시나리오_변화_만원"], orientation="h",
                      name=f"가정 −{s_swing:.0%}", marker_color="#4C78A8")
        fig_t.add_bar(y=torn_plot["가정"], x=torn_plot["+시나리오_변화_만원"], orientation="h",
                      name=f"가정 +{s_swing:.0%}", marker_color="#E45756")
        fig_t.update_layout(barmode="overlay", xaxis_title="TCO 변화 (만원)", yaxis_title="",
                            legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_t, width="stretch")
        top = torn.iloc[0]
        st.caption(
            f"{t_model}의 {s_years}년 기준 TCO는 {base_man:,.0f}만원입니다. "
            f"가장 영향이 큰 가정은 **{top['가정']}**(±{s_swing:.0%} → 약 ±{top['변동폭_만원'] / 2:,.0f}만원)입니다. "
            "연비를 올리면 비용이 줄어드는 것처럼, 막대가 왼쪽이면 TCO 감소, 오른쪽이면 증가입니다."
        )

        st.markdown("#### ② 가정을 동시에 흔들어도 모델 순위가 유지될까? (무작위 1,000회 시뮬레이션)")
        km_items = tuple(sorted(km_by_class_s.items()))
        res_s = _cached_rank(tuple(s_models), km_items, s_years, int(s_buy), s_ins * 10_000, s_scn, s_swing)
        rs = res_s["rank_share"].reindex(res_s["base_order"])
        fig_h = px.imshow(
            rs, text_auto=".0f", aspect="auto", color_continuous_scale="Blues",
            labels=dict(x="순위(1위=가장 저렴)", y="모델", color="비율(%)"),
        )
        st.plotly_chart(fig_h, width="stretch")

        pw = res_s["pairwise"]
        order = res_s["base_order"]
        close_pairs = []
        for a, b in zip(order, order[1:]):
            close_pairs.append((a, b, pw.loc[a, b]))
        solid = [f"{a}<{b}" for a, b, pr in close_pairs if pr >= 90]
        shaky = [f"{a} vs {b}({pr:.0f}%)" for a, b, pr in close_pairs if pr < 75]
        cheapest, priciest = order[0], order[-1]
        st.markdown(
            f"**읽는 법**: 가정을 ±{s_swing:.0%}씩 무작위로 바꿔도 기준 순위(저렴한 순: {' → '.join(order)})와 "
            f"**완전히 같은 순서**가 나온 비율은 **{res_s['same_order']:.0f}%**입니다. "
            f"가장 저렴한 모델({cheapest})이 1위를 유지한 비율은 {res_s['rank_share'].loc[cheapest, '1위']:.0f}%, "
            f"가장 비싼 모델({priciest})이 꼴찌를 유지한 비율은 "
            f"{res_s['rank_share'].loc[priciest, f'{len(order)}위']:.0f}%입니다."
        )
        if solid:
            st.success("순위가 거의 확실한 이웃 비교(90% 이상): " + ", ".join(solid))
        if shaky:
            st.warning("가정에 따라 뒤바뀔 수 있는 이웃 비교(75% 미만): " + ", ".join(shaky)
                       + " → 이 모델들은 '어느 쪽이 확실히 저렴하다'고 말하기 어렵습니다.")

        with st.expander("분석 방법과 한계 (발표/보고서 근거)"):
            st.markdown(
                f"""
- **①번**: 가정 하나만 기준값의 ±{s_swing:.0%}로 바꾸고 나머지는 고정해 TCO가 얼마나 변하는지 계산했습니다.
- **②번**: 유가는 모든 모델에 같은 비율로, **연비·보험료·감가상각액·연간 주행거리는 모델마다 독립적으로** ±{s_swing:.0%} 범위(균등분포)에서 1,000번 뽑아 TCO와 순위를 다시 계산했습니다.
  모든 모델을 같은 방향으로만 흔들면 순위가 절대 안 바뀌는 착시가 생기기 때문에 모델별로 따로 흔들었습니다.
- '감가상각액'은 신차 가격 오차와 중고 시세 오차를 함께 담은 값입니다(신차가 × 감가율이라 효과가 같음).
- **한계**: 변동폭(±{s_swing:.0%})과 균등분포는 분석자가 정한 가정이며, 가정들 사이의 상관(예: 유가↑ 시 중고 시세 변화)은 반영하지 않았습니다.
  보험료는 모든 모델에 같은 평균값에서 출발하고, 모델별 연간 주행거리는 차급 평균을 기준으로 합니다.
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
