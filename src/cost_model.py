"""
cost_model.py — 유지비 / 총소유비용(TCO) 계산 로직

발표 때 설명하기 쉽도록 '식 하나씩'만 쓰는 단순한 모델로 만들었습니다.

    연간 비용(n년차) = 자동차세(n년차) + 유류비
    TCO(N년 보유)    = 연간 비용의 N년 합계

  · 자동차세(n년차) = 배기량 × cc당 세율 × (1 − 차령 경감률) × (1 + 지방교육세 30%)
  · 차령 경감률     = 3년차 5%, 이후 매년 5%p 추가, 최대 50% (12년차 이상)
  · 유류비          = 연간 주행거리 ÷ 연비 × 유가
  · 연간 주행거리   = 평균 누적주행거리 ÷ 평균 사용연수  (KOSIS 실제 데이터로 역산)

⚠️ 아래 '가정' 항목은 공식 통계가 아니라 분석을 위해 둔 값입니다. 보고서/발표에서
   가정임을 밝히고, 수치를 바꿔도 결과가 크게 달라지지 않는지(민감도)를 함께 보여주면 좋습니다.
   보험료·정비비·감가상각은 개인 편차가 커서 포함하지 않았습니다.
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


def yearly_cost_table(car_class: str, fuel: str, annual_km: float, years: int, start_age: int = 1) -> pd.DataFrame:
    """보유 기간 동안의 연도별 비용표.

    start_age : 구매 시점의 차령(년차). 새 차 = 1, 3년 탄 중고차 = 4.
    반환 컬럼: 보유연차, 차령, 자동차세_원, 유류비_원, 연간합계_원, 누적합계_원
    """
    cc = REPRESENTATIVE_DISPLACEMENT_CC[car_class]
    fuel_cost = annual_fuel_cost(annual_km, FUEL_EFFICIENCY_KM_PER_L[car_class], FUEL_PRICE_PER_LITER[fuel])

    rows, cumulative = [], 0.0
    for i in range(1, years + 1):
        vehicle_year = start_age + i - 1
        tax = car_tax(cc, vehicle_year)
        total = tax + fuel_cost
        cumulative += total
        rows.append({
            "보유연차": i, "차령": vehicle_year,
            "자동차세_원": tax, "유류비_원": fuel_cost,
            "연간합계_원": total, "누적합계_원": cumulative,
        })
    return pd.DataFrame(rows)


def compare_classes(km_by_class: dict, fuel: str, years: int, start_age: int = 1) -> pd.DataFrame:
    """모든 차급을 같은 조건(연료·보유기간·구매 차령)으로 비교. 총비용 오름차순."""
    rows = []
    for cls in CAR_CLASSES:
        if cls not in km_by_class:
            continue
        t = yearly_cost_table(cls, fuel, km_by_class[cls], years, start_age)
        rows.append({
            "차급": cls,
            "총소유비용_만원": t["누적합계_원"].iloc[-1] / 10_000,
            "자동차세_합계_만원": t["자동차세_원"].sum() / 10_000,
            "유류비_합계_만원": t["유류비_원"].sum() / 10_000,
        })
    return pd.DataFrame(rows).sort_values("총소유비용_만원").reset_index(drop=True)
