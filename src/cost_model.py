"""
cost_model.py — 유지비 / 총소유비용(TCO) 계산 로직

발표 때 설명하기 쉽도록 '식 하나씩'만 쓰는 단순한 모델로 만들었습니다.

    연간 비용(n년차) = 자동차세(n년차) + 유류비 + 보험료
    TCO(N년 보유)    = 연간 비용의 N년 합계

  · 자동차세(n년차) = 배기량 × cc당 세율 × (1 − 차령 경감률) × (1 + 지방교육세 30%)
  · 차령 경감률     = 3년차 5%, 이후 매년 5%p 추가, 최대 50% (12년차 이상)
  · 유류비          = 연간 주행거리 ÷ 연비 × 유가
  · 보험료          = 개인용 자동차보험 1대당 연평균 보험료 (보험개발원 2025년 약 68만원), 사용자가 조정 가능
  · 연간 주행거리   = 평균 누적주행거리 ÷ 평균 사용연수  (KOSIS 실제 데이터로 역산)

⚠️ 아래 '가정' 항목은 공식 통계가 아니라 분석을 위해 둔 값입니다. 보고서/발표에서
   가정임을 밝히고, 수치를 바꿔도 결과가 크게 달라지지 않는지(민감도)를 함께 보여주면 좋습니다.
   정비비·감가상각은 개인 편차가 커서 포함하지 않았습니다.
"""

import pandas as pd

# ── 가정 1: 차급별 대표 배기량(cc) ─────────────────────────
# 승용차 규모 구분(경형 1000cc 미만, 소형 1600cc 미만, 중형 2000cc 미만, 대형 2000cc 이상)에
# 속하는 대표 모델의 배기량을 사용 (경형=모닝 998, 소형=아반떼 1598, 중형=쏘나타 1999, 대형=그랜저 2497)
REPRESENTATIVE_DISPLACEMENT_CC = {"경형": 998, "소형": 1598, "중형": 1999, "대형": 2497}

# ── 가정 2: 차급별 대표 연비(km/L) — 공식 통계가 아닌 가정값 ──
FUEL_EFFICIENCY_KM_PER_L = {"경형": 15.0, "소형": 13.5, "중형": 11.5, "대형": 9.5}

# ── 유가(원/L): 오피넷(한국석유공사) 2026년 9월 전국 평균 판매가격 ──
FUEL_PRICE_PER_LITER = {"휘발유": 1859, "경유": 1844}

# ── 대표 모델 제원 (가솔린 기본 엔진) ─────────────────────────
# 배기량·복합연비는 제조사 공식 제원(기아 공식 사이트, 카눈 가격표/제원 페이지)에서 확인한 값.
# 연비는 타이어 크기에 따라 달라지므로 '중간 크기 타이어' 기준(선택지가 하나면 그 값)을 썼다.
# 신차가_만원: 가솔린 기본(최저) 트림 가격, 옵션 제외. 출처·시점이 모델마다 다름 →
#   모닝(기아 공식, 2026.10 1.0 가솔린 트렌디), 아반떼(2026년형 스마트, 2025.4 보도), 쏘나타(2026년형 프리미엄, 탑라이더),
#   K5(2026년형 스마트 셀렉트, 탑라이더), 스포티지(2026년형 프레스티지, 다음뉴스), 그랜저(2025년형 프리미엄, 개소세 인하 반영가, 카눈),
#   투싼(2024년형 최저가, 카이즈유 — 2026년형 공식 가격은 확인 못함)
# 스포티지는 2WD/4WD·타이어에 따라 10.5~12.3이라 범위 중간값(11.4)을 사용.
# 차급은 승용차 규모 구분(경형 1000cc 미만, 소형 1600cc 미만, 중형 2000cc 미만, 대형 2000cc 이상)에 따라 분류.
MODEL_SPECS = {
    "모닝":     {"브랜드": "기아",   "차급": "경형", "배기량_cc": 998,  "연비_km_L": 14.7, "신차가_만원": 1421},
    "아반떼":   {"브랜드": "현대",   "차급": "소형", "배기량_cc": 1598, "연비_km_L": 14.8, "신차가_만원": 2034},
    "투싼":     {"브랜드": "현대",   "차급": "소형", "배기량_cc": 1598, "연비_km_L": 12.5, "신차가_만원": 2771},
    "스포티지": {"브랜드": "기아",   "차급": "소형", "배기량_cc": 1598, "연비_km_L": 11.4, "신차가_만원": 2907},
    "쏘나타":   {"브랜드": "현대",   "차급": "중형", "배기량_cc": 1999, "연비_km_L": 12.0, "신차가_만원": 2826},
    "K5":       {"브랜드": "기아",   "차급": "중형", "배기량_cc": 1999, "연비_km_L": 12.6, "신차가_만원": 2724},
    "그랜저":   {"브랜드": "현대",   "차급": "대형", "배기량_cc": 2497, "연비_km_L": 11.4, "신차가_만원": 3711},
}

# ── 감가상각: 신차 대비 중고차 잔존가치율 (공식 통계가 아닌 공개 참고자료 기반 가정) ──
# 낙관: calcmo.kr 평균 감가곡선(국산 승용, 1/3/5/7/10년 = 80/62/48/37/25%)
# 비관: telarum.com 연식별 감가율(1/3/5년 = 80/55/40%). 7·10년은 자료가 없어 낙관 곡선의 하락 비율을 적용한 가정
# 기본: 두 곡선의 평균. 두 자료 모두 조사기관·표본이 불명확하므로 시세 근거가 아니라 '시나리오'로만 사용한다.
RESIDUAL_ANCHORS = {
    "낙관": {0: 1.00, 1: 0.80, 3: 0.62, 5: 0.48, 7: 0.37, 10: 0.25},
    "비관": {0: 1.00, 1: 0.80, 3: 0.55, 5: 0.40, 7: 0.308, 10: 0.208},
}
RESIDUAL_ANCHORS["기본"] = {k: (RESIDUAL_ANCHORS["낙관"][k] + RESIDUAL_ANCHORS["비관"][k]) / 2
                          for k in RESIDUAL_ANCHORS["낙관"]}
RESIDUAL_SCENARIOS = ["낙관", "기본", "비관"]
RESIDUAL_FLOOR = 0.05        # 잔존가치 하한(폐차 수준)
RESIDUAL_DECAY_AFTER_10 = 0.90   # 10년 초과 시 매년 10%씩 추가 하락 (가정)

# ── 보험료(원/년): 개인용 자동차보험 1대당 평균 보험료 (보험개발원, 2025년 약 68만원) ──
# 차급·연령·경력별 공식 평균은 확인하지 못해 모든 차급에 같은 값을 쓰고, 앱에서 사용자가 조정하게 한다.
AVG_INSURANCE_PREMIUM_WON = 680_000

# ── 자동차세 (비영업용 승용차) ─────────────────────────────
EDU_TAX_RATE = 0.30          # 지방교육세: 자동차세액의 30%
MAX_AGE_DISCOUNT = 0.50      # 차령 경감 상한 50%
AGE_DISCOUNT_STEP = 0.05     # 3년차부터 매년 5%p씩 경감

CAR_CLASSES = list(REPRESENTATIVE_DISPLACEMENT_CC.keys())
FUELS = list(FUEL_PRICE_PER_LITER.keys())


def base_car_tax(cc: int) -> float:
    """경감 전 자동차세(본세). 배기량 구간에 따라 cc당 세율이 달라진다(구간 전체에 동일 세율 적용)."""
    if cc <= 1000:
        rate = 80
    elif cc <= 1600:
        rate = 140
    else:
        rate = 200
    return cc * rate


def age_discount_rate(vehicle_year: int) -> float:
    """차령(n년차)에 따른 자동차세 경감률. 1~2년차 0%, 3년차 5% … 12년차 이상 50%."""
    if vehicle_year < 3:
        return 0.0
    return min(AGE_DISCOUNT_STEP * (vehicle_year - 2), MAX_AGE_DISCOUNT)


def car_tax(cc: int, vehicle_year: int = 1) -> float:
    """n년차 연간 자동차세(지방교육세 포함, 원)."""
    return base_car_tax(cc) * (1 - age_discount_rate(vehicle_year)) * (1 + EDU_TAX_RATE)


def annual_fuel_cost(annual_km: float, efficiency_km_per_l: float, price_per_liter: float) -> float:
    """연간 유류비(원)."""
    return annual_km / efficiency_km_per_l * price_per_liter


def annual_km_by_class(df_lifespan: pd.DataFrame, df_mileage: pd.DataFrame) -> dict:
    """차급별 연간 주행거리(km) = 평균 누적주행거리 ÷ 평균 사용연수."""
    merged = df_lifespan.merge(df_mileage, on="차급")
    merged["연간_주행거리_km"] = merged["평균_누적주행거리_km"] / merged["평균_사용연수"]
    return dict(zip(merged["차급"], merged["연간_주행거리_km"]))


def yearly_cost_table(car_class: str, fuel: str, annual_km: float, years: int, start_age: int = 1,
                      insurance: float = AVG_INSURANCE_PREMIUM_WON,
                      cc: int | None = None, efficiency: float | None = None) -> pd.DataFrame:
    """보유 기간 동안의 연도별 비용표.

    cc, efficiency : 지정하면 차급 대표값 대신 이 값(특정 모델의 배기량·연비)을 쓴다.

    start_age : 구매 시점의 차령(년차). 새 차 = 1, 3년 탄 중고차 = 4.
    insurance : 연간 보험료(원). 반환 컬럼: 보유연차, 차령, 자동차세_원, 유류비_원, 보험료_원, 연간합계_원, 누적합계_원
    """
    cc = cc if cc is not None else REPRESENTATIVE_DISPLACEMENT_CC[car_class]
    eff = efficiency if efficiency is not None else FUEL_EFFICIENCY_KM_PER_L[car_class]
    fuel_cost = annual_fuel_cost(annual_km, eff, FUEL_PRICE_PER_LITER[fuel])

    rows, cumulative = [], 0.0
    for i in range(1, years + 1):
        vehicle_year = start_age + i - 1
        tax = car_tax(cc, vehicle_year)
        total = tax + fuel_cost + insurance
        cumulative += total
        rows.append({
            "보유연차": i, "차령": vehicle_year,
            "자동차세_원": tax, "유류비_원": fuel_cost, "보험료_원": insurance,
            "연간합계_원": total, "누적합계_원": cumulative,
        })
    return pd.DataFrame(rows)


def compare_classes(km_by_class: dict, fuel: str, years: int, start_age: int = 1,
                    insurance: float = AVG_INSURANCE_PREMIUM_WON) -> pd.DataFrame:
    """모든 차급을 같은 조건(연료·보유기간·구매 차령)으로 비교. 총비용 오름차순."""
    rows = []
    for cls in CAR_CLASSES:
        if cls not in km_by_class:
            continue
        t = yearly_cost_table(cls, fuel, km_by_class[cls], years, start_age, insurance)
        rows.append({
            "차급": cls,
            "총소유비용_만원": t["누적합계_원"].iloc[-1] / 10_000,
            "자동차세_합계_만원": t["자동차세_원"].sum() / 10_000,
            "유류비_합계_만원": t["유류비_원"].sum() / 10_000,
            "보험료_합계_만원": t["보험료_원"].sum() / 10_000,
        })
    return pd.DataFrame(rows).sort_values("총소유비용_만원").reset_index(drop=True)


def compare_models(model_names: list, km_by_class: dict, years: int, start_age: int = 1,
                   insurance: float = AVG_INSURANCE_PREMIUM_WON, fuel: str = "휘발유",
                   scenario: str = "기본") -> pd.DataFrame:
    """선택한 모델들을 같은 조건으로 비교 (감가상각 포함). 연간 주행거리는 모델이 속한 차급의 값을 쓴다(모델별 통계 없음).
    총소유비용_낙관/비관: 잔존가치 시나리오에 따른 TCO 범위."""
    buy_age = start_age - 1
    rows = []
    for name in model_names:
        spec = MODEL_SPECS[name]
        t = yearly_cost_table(spec["차급"], fuel, km_by_class[spec["차급"]], years, start_age,
                              insurance, cc=spec["배기량_cc"], efficiency=spec["연비_km_L"])
        running = t["누적합계_원"].iloc[-1]
        price = spec["신차가_만원"] * 10_000
        depr = {sc: depreciation_cost(price, buy_age, years, sc) for sc in RESIDUAL_SCENARIOS}
        rows.append({
            "모델": name, "브랜드": spec["브랜드"], "차급": spec["차급"],
            "배기량_cc": spec["배기량_cc"], "연비_km_L": spec["연비_km_L"], "신차가_만원": spec["신차가_만원"],
            "총소유비용_만원": (running + depr[scenario]) / 10_000,
            "감가상각_합계_만원": depr[scenario] / 10_000,
            "자동차세_합계_만원": t["자동차세_원"].sum() / 10_000,
            "유류비_합계_만원": t["유류비_원"].sum() / 10_000,
            "보험료_합계_만원": t["보험료_원"].sum() / 10_000,
            "총소유비용_낙관_만원": (running + depr["낙관"]) / 10_000,
            "총소유비용_비관_만원": (running + depr["비관"]) / 10_000,
        })
    return pd.DataFrame(rows).sort_values("총소유비용_만원").reset_index(drop=True)

def residual_rate(age_years: float, scenario: str = "기본") -> float:
    """차령(년)에 따른 신차 대비 잔존가치율. 앵커 사이는 직선 보간, 10년 초과는 매년 10% 감소, 하한 5%."""
    anchors = RESIDUAL_ANCHORS[scenario]
    xs = sorted(anchors)
    if age_years <= xs[0]:
        return anchors[xs[0]]
    if age_years >= xs[-1]:
        return max(anchors[xs[-1]] * RESIDUAL_DECAY_AFTER_10 ** (age_years - xs[-1]), RESIDUAL_FLOOR)
    for a, b in zip(xs, xs[1:]):
        if a <= age_years <= b:
            w = (age_years - a) / (b - a)
            return anchors[a] + w * (anchors[b] - anchors[a])


def depreciation_cost(new_price_won: float, buy_age: int, years: int, scenario: str = "기본") -> float:
    """보유 기간 동안의 감가상각액(원) = 신차가 × (구매 시점 잔존율 − 매각 시점 잔존율).
    buy_age=0이면 신차 구매, 3이면 3년 된 중고차 구매."""
    return new_price_won * (residual_rate(buy_age, scenario) - residual_rate(buy_age + years, scenario))
