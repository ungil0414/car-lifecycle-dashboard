"""
sensitivity.py — 가정을 바꿔도 결론이 유지되는지 확인하는 민감도 분석

TCO에는 공식 통계가 아닌 '가정'이 여럿 들어갑니다 (연비, 유가, 보험료, 감가상각, 연간 주행거리).
이 모듈은 두 가지를 보여줍니다.

1) 토네이도: 가정 하나만 ±X% 흔들었을 때 TCO가 얼마나 변하는가 (어떤 가정이 중요한가)
2) 무작위 조합: 가정을 동시에 ±X% 범위에서 무작위로 흔들었을 때 모델 순위가 얼마나 유지되는가
   (유가는 모든 모델 공통, 연비·보험료·감가상각액·주행거리는 모델마다 독립적으로 흔든다 —
    '모든 모델이 같은 방향으로만 흔들리면 순위가 절대 안 바뀐다'는 착시를 피하기 위해서)

여기서 '배수(multiplier)'는 기준값에 곱하는 값입니다. 1.0 = 기준, 1.2 = +20%.
"""

import numpy as np
import pandas as pd

from src import cost_model

# 흔들어볼 가정과 화면에 보여줄 이름
FACTORS = {
    "연비": "eff",
    "유가": "fuel_price",
    "보험료": "insurance",
    "감가상각액": "depreciation",   # 신차 가격 오차와 중고 시세 오차를 함께 담은 값 (신차가 × 감가율이라 효과가 같음)
    "연간 주행거리": "km",
}

# 무작위 조합에서 모델마다 따로 흔드는 가정 (실제로 모델별로 달라지는 값들).
# 유가는 모든 모델에 똑같이 적용되므로 공통으로 흔든다.
PER_MODEL_FACTORS = ["eff", "insurance", "depreciation", "km"]
COMMON_FACTORS = ["fuel_price"]


def _tco_won(model_name: str, km_by_class: dict, years: int, buy_age: int, insurance_won: float,
             scenario: str, fuel: str, m: dict) -> float:
    """배수 m을 적용한 모델 1개의 TCO(원).
    m의 키: eff, fuel_price, insurance, depreciation, km (없으면 1.0)"""
    g = lambda k: m.get(k, 1.0)
    spec = cost_model.MODEL_SPECS[model_name]
    km = km_by_class[spec["차급"]] * g("km")
    eff = spec["연비_km_L"] * g("eff")
    fuel_price = cost_model.FUEL_PRICE_PER_LITER[fuel] * g("fuel_price")
    fuel_cost = cost_model.annual_fuel_cost(km, eff, fuel_price)

    running = 0.0
    for i in range(1, years + 1):
        running += cost_model.car_tax(spec["배기량_cc"], buy_age + i) + fuel_cost + insurance_won * g("insurance")

    price = spec["신차가_만원"] * 10_000
    depr = cost_model.depreciation_cost(price, buy_age, years, scenario) * g("depreciation")
    return running + depr


def tornado(model_name: str, km_by_class: dict, years: int, buy_age: int, insurance_won: float,
            scenario: str = "기본", fuel: str = "휘발유", swing: float = 0.2) -> pd.DataFrame:
    """가정 하나씩 ±swing 흔들었을 때 TCO 변화(만원). 영향이 큰 순으로 정렬."""
    base = _tco_won(model_name, km_by_class, years, buy_age, insurance_won, scenario, fuel, {})
    rows = []
    for label, key in FACTORS.items():
        low = _tco_won(model_name, km_by_class, years, buy_age, insurance_won, scenario, fuel, {key: 1 - swing})
        high = _tco_won(model_name, km_by_class, years, buy_age, insurance_won, scenario, fuel, {key: 1 + swing})
        rows.append({
            "가정": label,
            "−시나리오_변화_만원": (low - base) / 10_000,
            "+시나리오_변화_만원": (high - base) / 10_000,
            "변동폭_만원": abs(high - low) / 10_000,
        })
    out = pd.DataFrame(rows).sort_values("변동폭_만원", ascending=False).reset_index(drop=True)
    out.attrs["base_man"] = base / 10_000
    return out


def rank_stability(model_names: list, km_by_class: dict, years: int, buy_age: int, insurance_won: float,
                   scenario: str = "기본", fuel: str = "휘발유", swing: float = 0.2,
                   n_draws: int = 2000, seed: int = 42) -> dict:
    """가정을 동시에 ±swing 범위(균등분포)에서 무작위로 흔들어 모델 순위가 얼마나 유지되는지 계산.
    유가는 모델 공통, 나머지(연비·보험료·감가상각액·주행거리)는 모델마다 독립적으로 흔든다.

    반환:
      rank_share : 모델 × 순위(1=가장 저렴) 비율(%) 표
      pairwise   : A가 B보다 저렴할 확률(%) 행렬
      base_order : 가정을 흔들지 않았을 때의 순위(저렴한 순)
      same_order : 기준 순위와 완전히 같은 순서가 나온 비율(%)
    """
    rng = np.random.default_rng(seed)
    n_models = len(model_names)
    totals = np.zeros((n_draws, n_models))
    for d in range(n_draws):
        common = {k: rng.uniform(1 - swing, 1 + swing) for k in COMMON_FACTORS}
        for j, name in enumerate(model_names):
            m = dict(common)
            m.update({k: rng.uniform(1 - swing, 1 + swing) for k in PER_MODEL_FACTORS})
            totals[d, j] = _tco_won(name, km_by_class, years, buy_age, insurance_won, scenario, fuel, m)

    base = np.array([_tco_won(n, km_by_class, years, buy_age, insurance_won, scenario, fuel, {}) for n in model_names])
    base_rank = base.argsort().argsort()          # 0 = 가장 저렴
    ranks = totals.argsort(axis=1).argsort(axis=1)

    rank_share = pd.DataFrame(
        {f"{r + 1}위": [(ranks[:, j] == r).mean() * 100 for j in range(n_models)] for r in range(n_models)},
        index=model_names,
    ).round(1)

    pairwise = pd.DataFrame(
        [[(totals[:, a] < totals[:, b]).mean() * 100 if a != b else np.nan for b in range(n_models)]
         for a in range(n_models)],
        index=model_names, columns=model_names,
    ).round(1)

    base_order = [model_names[i] for i in base.argsort()]
    same_order = float((ranks == base_rank).all(axis=1).mean() * 100)
    return {"rank_share": rank_share, "pairwise": pairwise, "base_order": base_order,
            "same_order": same_order, "totals_man": totals / 10_000, "names": model_names}
