"""
sample_data.py

⚠️ 이 파일은 실제 공공데이터가 준비되기 전까지 대시보드 구조를 테스트하기 위한
   '가상 데이터'를 생성합니다. 실제 데이터가 확보되면 data_loader.py 에서
   이 함수 대신 실제 CSV를 읽도록 교체합니다.

   숫자는 뉴스·통계 기사에서 확인한 대략적인 범위(예: 국산차 평균 폐차주기 15~16년,
   수입차 13~14년)를 참고해 현실적인 느낌으로 만들었을 뿐, 실제 통계값이 아닙니다.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

CAR_CLASSES = ["경형", "소형", "준중형", "중형", "대형", "수입차"]
AGE_GROUPS = ["20대", "30대", "40대", "50대", "60대 이상"]
FUEL_TYPES = ["휘발유", "경유", "하이브리드", "전기", "LPG"]


def get_lifespan_data() -> pd.DataFrame:
    """차급별 평균 사용 기간(폐차/교체까지 걸리는 평균 연수)"""
    base_years = {
        "경형": 13.3, "소형": 15.5, "준중형": 15.8,
        "중형": 16.2, "대형": 16.8, "수입차": 13.8,
    }
    rows = []
    for cls, yrs in base_years.items():
        rows.append({
            "차급": cls,
            "평균_사용연수": round(yrs + RNG.normal(0, 0.3), 1),
            "표본수(대)": int(RNG.integers(3000, 20000)),
        })
    return pd.DataFrame(rows)


def get_age_preference_data() -> pd.DataFrame:
    """연령대별 차급 선호 비율(%) - 가상 데이터"""
    rows = []
    weight_profile = {
        "20대": [0.30, 0.25, 0.20, 0.10, 0.05, 0.10],
        "30대": [0.15, 0.20, 0.25, 0.20, 0.05, 0.15],
        "40대": [0.05, 0.10, 0.20, 0.30, 0.15, 0.20],
        "50대": [0.05, 0.05, 0.15, 0.30, 0.25, 0.20],
        "60대 이상": [0.05, 0.10, 0.15, 0.25, 0.30, 0.15],
    }
    for age, weights in weight_profile.items():
        noisy = np.array(weights) + RNG.normal(0, 0.01, size=len(weights))
        noisy = np.clip(noisy, 0.01, None)
        noisy = noisy / noisy.sum()
        for cls, w in zip(CAR_CLASSES, noisy):
            rows.append({"연령대": age, "차급": cls, "선호비율": round(w * 100, 1)})
    return pd.DataFrame(rows)


def get_mileage_data() -> pd.DataFrame:
    """차급별 평균 누적주행거리(km) - 가상 데이터"""
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
    """연령대별 자동차 등록 비중(%) - 가상 데이터 (실제 데이터 스키마와 동일한 형태)"""
    order = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대 이상"]
    weights = np.array([0.1, 5.0, 15.0, 22.0, 27.0, 20.0, 8.0, 2.5, 0.4])
    weights = weights + RNG.normal(0, 0.3, size=len(weights))
    weights = np.clip(weights, 0.05, None)
    weights = weights / weights.sum() * 100
    counts = (weights * 30000).astype(int)  # 임의 스케일
    return pd.DataFrame({"연령대": order, "등록대수": counts, "비중(%)": weights.round(1)})


def get_maintenance_cost_data() -> pd.DataFrame:
    """차급 x 연료타입별 연간 예상 유지비(만원) - 가상 데이터
    (보험료 + 정비비 + 연료비 추정치 합산 컨셉)
    """
    base_cost = {
        "경형": 180, "소형": 220, "준중형": 260,
        "중형": 320, "대형": 420, "수입차": 550,
    }
    fuel_multiplier = {
        "휘발유": 1.0, "경유": 0.92, "하이브리드": 0.82,
        "전기": 0.70, "LPG": 0.88,
    }
    rows = []
    for cls, cost in base_cost.items():
        for fuel, mult in fuel_multiplier.items():
            est = cost * mult + RNG.normal(0, 8)
            rows.append({
                "차급": cls, "연료": fuel,
                "연간_예상유지비_만원": round(est, 1),
            })
    return pd.DataFrame(rows)
