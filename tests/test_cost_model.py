"""계산 로직 검증 테스트 — 실행: python -m pytest tests -q  (또는 python tests/test_cost_model.py)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import cost_model as cm, sensitivity as sens

KM = {"경형": 12000, "소형": 12000, "중형": 12000, "대형": 12000}


def test_car_tax_rate_and_age_discount():
    # 1,598cc: 140원 x 1598 x 1.3 (경감 없음)
    assert round(cm.car_tax(1598, 1)) == round(1598 * 140 * 1.3)
    # 3년차 5% 경감
    assert round(cm.car_tax(1598, 3)) == round(1598 * 140 * 0.95 * 1.3)
    # 12년차 이상 최대 50%
    assert round(cm.car_tax(1598, 15)) == round(1598 * 140 * 0.5 * 1.3)


def test_fuel_cost():
    # 12,000km / 12km/L * 1,800원 = 1,800,000원
    assert round(cm.annual_fuel_cost(12000, 12, 1800)) == 1_800_000


def test_residual_monotonic_decreasing():
    for scn in cm.RESIDUAL_SCENARIOS:
        vals = [cm.residual_rate(a, scn) for a in range(0, 16)]
        assert all(a >= b for a, b in zip(vals, vals[1:]))
        assert vals[-1] >= 0.05  # 하한


def test_depreciation_scenarios_ordered():
    price = 30_000_000
    낙관 = cm.depreciation_cost(price, 0, 5, "낙관")
    기본 = cm.depreciation_cost(price, 0, 5, "기본")
    비관 = cm.depreciation_cost(price, 0, 5, "비관")
    assert 낙관 <= 기본 <= 비관


def test_tco_grows_with_years():
    a = sens._tco_won("쏘나타", KM, 3, 0, 680_000, "기본", "휘발유", {})
    b = sens._tco_won("쏘나타", KM, 5, 0, 680_000, "기본", "휘발유", {})
    assert b > a


def test_tornado_and_rank_stability_shapes():
    t = sens.tornado("그랜저", KM, 5, 0, 680_000)
    assert len(t) == 5 and (t["변동폭_만원"] >= 0).all()
    r = sens.rank_stability(["모닝", "그랜저"], KM, 5, 0, 680_000, n_draws=200)
    assert r["base_order"][0] == "모닝"
    # 각 모델의 순위 비율 합은 100%
    assert all(abs(row.sum() - 100) < 0.5 for _, row in r["rank_share"].iterrows())


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("OK", name)
