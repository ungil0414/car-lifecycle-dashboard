"""
sample_data.py

⚠️ 실제 공공데이터 CSV(data/processed/)가 없을 때만 쓰이는 '가상 데이터' 생성기입니다.
   현재는 모든 탭이 실제 데이터로 동작하므로, 이 파일은 안전장치(fallback) 역할만 합니다.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

CAR_CLASSES = ["경형", "소형", "준중형", "중형", "대형", "수입차"]
FUEL_TYPES = ["휘발유", "경유", "하이브리드", "전기", "LPG"]


def get_lifespan_data() -> pd.DataFrame:
    base_years = {"경형": 13.3, "소형": 15.5, "준중형": 15.8, "중형": 16.2, "대형": 16.8, "수입차": 13.8}
    rows = []
    for cls, yrs in base_years.items():
        rows.append({
            "차급": cls,
            "평균_사용연수": round(yrs + RNG.normal(0, 0.3), 1),
            "표본수(대)": int(RNG.integers(3000, 20000)),
        })
    return pd.DataFrame(rows)


def get_mileage_data() -> pd.DataFrame:
    base_km = {"경형": 90000, "소형": 110000, "준중형": 115000, "중형": 120000, "대형": 125000, "수입차": 100000}
    rows = []
    for cls, km in base_km.items():
        rows.append({
            "차급": cls,
            "평균_누적주행거리_km": int(km + RNG.normal(0, 3000)),
            "표본수(대)": int(RNG.integers(3000, 20000)),
        })
    return pd.DataFrame(rows)


def get_age_distribution_data() -> pd.DataFrame:
    order = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대 이상"]
    weights = np.array([0.1, 5.0, 15.0, 22.0, 27.0, 20.0, 8.0, 2.5, 0.4])
    weights = weights + RNG.normal(0, 0.3, size=len(weights))
    weights = np.clip(weights, 0.05, None)
    weights = weights / weights.sum() * 100
    counts = (weights * 30000).astype(int)
    return pd.DataFrame({"연령대": order, "등록대수": counts, "비중(%)": weights.round(1)})


def get_maintenance_cost_data() -> pd.DataFrame:
    base_cost = {"경형": 180, "소형": 220, "준중형": 260, "중형": 320, "대형": 420, "수입차": 550}
    fuel_multiplier = {"휘발유": 1.0, "경유": 0.92, "하이브리드": 0.82, "전기": 0.70, "LPG": 0.88}
    rows = []
    for cls, cost in base_cost.items():
        for fuel, mult in fuel_multiplier.items():
            est = cost * mult + RNG.normal(0, 8)
            rows.append({"차급": cls, "연료": fuel, "연간_예상유지비_만원": round(est, 1)})
    return pd.DataFrame(rows)
