"""
preprocess_real_data.py

원본 공공데이터(KOSIS 엑셀 2개 + 서울 열린데이터광장 엑셀 1개)를 읽어서
대시보드에 바로 쓸 수 있는 CSV로 가공합니다.

실행: python src/preprocess_real_data.py
"""

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))  # 'python src/preprocess_real_data.py' 로 직접 실행해도 src 패키지를 찾도록

from src import cost_model  # noqa: E402

RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# 차령 구간 → 대표 연수(중간값). '15년 이상'은 열린 구간이라 18년으로 가정.
AGE_MIDPOINT = {
    "4년 이하": 2.0, "5~6년": 5.5, "7~8년": 7.5, "9~10년": 9.5,
    "11~12년": 11.5, "13~14년": 13.5, "15년 이상": 18.0,
}

# 주행거리 구간 → 대표 주행거리(km, 중간값). '25만km 이상'은 30만으로 가정.
MILEAGE_MIDPOINT = {
    "5만km 미만": 25_000, "5만km~10만km 미만": 75_000,
    "10만km~15만km 미만": 125_000, "15만km~20만km 미만": 175_000,
    "20만km~25만km 미만": 225_000, "25만km이상": 300_000,
}

CLASS_ORDER = ["경형", "소형", "중형", "대형"]


def _parse_kosis_wide_file(path: Path) -> pd.DataFrame:
    """KOSIS 3행 헤더(연도/구간/지표) + 병합 라벨 열(용도/차종/규모)을 긴 형태로 변환.
    반환 컬럼: 연도, 용도, 차종, 규모, 구간, 검사대수
    """
    raw = pd.read_excel(path, sheet_name="데이터", header=None)

    years = raw.iloc[0, 3:].tolist()
    bins_ = raw.iloc[1, 3:].tolist()
    metrics = raw.iloc[2, 3:].tolist()

    labels = raw.iloc[3:, 0:3].copy()
    labels.columns = ["용도", "차종", "규모"]
    labels = labels.ffill().reset_index(drop=True)
    data = raw.iloc[3:, 3:].reset_index(drop=True)

    records = []
    for col_idx in range(data.shape[1]):
        year, bin_name, metric = years[col_idx], bins_[col_idx], metrics[col_idx]
        if bin_name == "합계" or metric != "검사대수 (대)":
            continue
        col_values = pd.to_numeric(data.iloc[:, col_idx], errors="coerce")
        for row_idx, val in enumerate(col_values):
            if pd.isna(val):
                continue
            records.append({
                "연도": int(year),
                "용도": labels.loc[row_idx, "용도"],
                "차종": labels.loc[row_idx, "차종"],
                "규모": labels.loc[row_idx, "규모"],
                "구간": bin_name,
                "검사대수": int(val),
            })
    return pd.DataFrame(records)


def _passenger_subset(df: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    """승용차 · 전체 용도 · 규모별 · '기타' 제외 (필요 시 특정 연도만)"""
    mask = (df["용도"] == "전체") & (df["차종"] == "승용차") & (df["규모"] != "합계") & (df["구간"] != "기타")
    if year is not None:
        mask &= df["연도"] == year
    return df[mask].copy()


def _ordered(df: pd.DataFrame, col: str = "차급") -> pd.DataFrame:
    df[col] = pd.Categorical(df[col], categories=CLASS_ORDER, ordered=True)
    return df.sort_values(col).reset_index(drop=True)


def build_lifespan_summary(df_age_full: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """차급별 평균 사용연수 (구간 중간값의 검사대수 가중평균)"""
    sub = _passenger_subset(df_age_full, year)
    sub["중간값"] = sub["구간"].map(AGE_MIDPOINT)
    rows = []
    for cls, g in sub.groupby("규모"):
        total = g["검사대수"].sum()
        rows.append({"차급": cls, "평균_사용연수": round((g["중간값"] * g["검사대수"]).sum() / total, 2),
                     "표본수(대)": int(total)})
    return _ordered(pd.DataFrame(rows))


def build_mileage_summary(df_mileage_full: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """차급별 평균 누적주행거리 (구간 중간값의 검사대수 가중평균)"""
    sub = _passenger_subset(df_mileage_full, year)
    sub["중간값"] = sub["구간"].map(MILEAGE_MIDPOINT)
    rows = []
    for cls, g in sub.groupby("규모"):
        total = g["검사대수"].sum()
        avg = (g["중간값"] * g["검사대수"]).sum() / total
        rows.append({"차급": cls, "평균_누적주행거리_km": int(round(avg, -2)), "표본수(대)": int(total)})
    return _ordered(pd.DataFrame(rows))


def build_lifespan_trend(df_age_full: pd.DataFrame) -> pd.DataFrame:
    """연도별(2015~2024) 차급별 평균 사용연수 추이"""
    sub = _passenger_subset(df_age_full)
    sub["중간값"] = sub["구간"].map(AGE_MIDPOINT)
    rows = []
    for (year, cls), g in sub.groupby(["연도", "규모"]):
        total = g["검사대수"].sum()
        rows.append({"연도": year, "차급": cls,
                     "평균_사용연수": round((g["중간값"] * g["검사대수"]).sum() / total, 2)})
    return pd.DataFrame(rows).sort_values(["차급", "연도"]).reset_index(drop=True)


def _parse_seoul_age_gender_file(path: Path) -> pd.DataFrame:
    """서울 열린데이터광장 '자동차등록현황(성별/연령별)' → 긴 형태 (연도, 성별, 연령대, 등록대수)"""
    raw = pd.read_excel(path, sheet_name="데이터", header=None)
    years = raw.iloc[0, 2:].tolist()

    labels = raw.iloc[1:, 0:2].copy()
    labels.columns = ["성별", "연령대"]
    labels["성별"] = labels["성별"].ffill()
    labels = labels.reset_index(drop=True)
    data = raw.iloc[1:, 2:].reset_index(drop=True)

    records = []
    for row_idx in range(len(labels)):
        gender, age = labels.loc[row_idx, "성별"], labels.loc[row_idx, "연령대"]
        if gender == "법인 및 사업자" or age == "소계":
            continue
        for col_idx, year in enumerate(years):
            val = pd.to_numeric(data.iloc[row_idx, col_idx], errors="coerce")
            if pd.isna(val):
                continue
            records.append({"연도": int(year), "성별": gender, "연령대": age, "등록대수": int(val)})
    return pd.DataFrame(records)


def build_age_distribution_summary(df_age_full: pd.DataFrame, year: int = 2025) -> pd.DataFrame:
    """연령대별 등록대수(성별 합산, 최신연도) + 비중(%)"""
    grouped = df_age_full[df_age_full["연도"] == year].groupby("연령대", as_index=False)["등록대수"].sum()
    order = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대 이상"]
    grouped["연령대"] = pd.Categorical(grouped["연령대"], categories=order, ordered=True)
    grouped = grouped.sort_values("연령대").reset_index(drop=True)
    grouped["비중(%)"] = round(grouped["등록대수"] / grouped["등록대수"].sum() * 100, 1)
    return grouped


def build_maintenance_cost_summary(df_lifespan: pd.DataFrame, df_mileage: pd.DataFrame) -> pd.DataFrame:
    """차급 × 연료별 '새 차 1~2년차' 기준 연간 유지비 = 자동차세(경감 전) + 유류비.
    차령에 따른 변화는 TCO 탭(cost_model.yearly_cost_table)에서 다룬다."""
    km_by_class = cost_model.annual_km_by_class(df_lifespan, df_mileage)
    rows = []
    for cls in CLASS_ORDER:
        cc = cost_model.REPRESENTATIVE_DISPLACEMENT_CC[cls]
        tax = cost_model.car_tax(cc, vehicle_year=1)
        for fuel, price in cost_model.FUEL_PRICE_PER_LITER.items():
            fuel_cost = cost_model.annual_fuel_cost(km_by_class[cls], cost_model.FUEL_EFFICIENCY_KM_PER_L[cls], price)
            rows.append({
                "차급": cls, "연료": fuel,
                "자동차세_원": int(round(tax, -2)),
                "유류비_원": int(round(fuel_cost, -2)),
                "연간_예상유지비_만원": round((tax + fuel_cost) / 10_000, 1),
            })
    return _ordered(pd.DataFrame(rows)).sort_values(["차급", "연료"]).reset_index(drop=True)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("차령별 데이터 파싱 중...")
    df_age_full = _parse_kosis_wide_file(RAW_DIR / "kosis_차령별_검사현황.xlsx")
    df_age_full.to_csv(PROCESSED_DIR / "age_distribution_full.csv", index=False, encoding="utf-8-sig")

    print("주행거리별 데이터 파싱 중...")
    df_mileage_full = _parse_kosis_wide_file(RAW_DIR / "kosis_주행거리별_검사현황.xlsx")
    df_mileage_full.to_csv(PROCESSED_DIR / "mileage_distribution_full.csv", index=False, encoding="utf-8-sig")

    lifespan = build_lifespan_summary(df_age_full)
    lifespan.to_csv(PROCESSED_DIR / "lifespan.csv", index=False, encoding="utf-8-sig")
    print("\n[차급별 평균 사용연수]\n", lifespan)

    mileage = build_mileage_summary(df_mileage_full)
    mileage.to_csv(PROCESSED_DIR / "mileage.csv", index=False, encoding="utf-8-sig")
    print("\n[차급별 평균 누적주행거리]\n", mileage)

    build_lifespan_trend(df_age_full).to_csv(PROCESSED_DIR / "lifespan_trend.csv", index=False, encoding="utf-8-sig")

    print("\n서울시 연령대별/성별 등록현황 파싱 중...")
    df_seoul = _parse_seoul_age_gender_file(RAW_DIR / "seoul_연령별_성별_등록현황.xlsx")
    df_seoul.to_csv(PROCESSED_DIR / "age_gender_distribution_full.csv", index=False, encoding="utf-8-sig")
    age_summary = build_age_distribution_summary(df_seoul)
    age_summary.to_csv(PROCESSED_DIR / "age_distribution.csv", index=False, encoding="utf-8-sig")
    print(age_summary)

    maintenance = build_maintenance_cost_summary(lifespan, mileage)
    maintenance.to_csv(PROCESSED_DIR / "maintenance_cost.csv", index=False, encoding="utf-8-sig")
    print("\n[차급·연료별 연간 유지비]\n", maintenance)

    print("\n✅ 전처리 완료")


if __name__ == "__main__":
    main()
