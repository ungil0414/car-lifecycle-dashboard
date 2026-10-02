"""
preprocess_real_data.py

원본 공공데이터(KOSIS 엑셀 2개 + 서울 열린데이터광장 엑셀 1개)를 읽어서
대시보드에 바로 쓸 수 있는 형태로 가공합니다.

실행: python src/preprocess_real_data.py
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# ── 1. 차령별 데이터 (평균 사용연수) ──────────────────────
# 차령 구간 → 대표 연수(중간값). '15년 이상'은 open-ended라 18년으로 가정.
AGE_MIDPOINT = {
    "4년 이하": 2.0, "5~6년": 5.5, "7~8년": 7.5, "9~10년": 9.5,
    "11~12년": 11.5, "13~14년": 13.5, "15년 이상": 18.0,
}

# ── 2. 주행거리별 데이터 ──────────────────────────────────
# 주행거리 구간 → 대표 주행거리(km, 중간값). '25만km 이상'은 30만으로 가정.
MILEAGE_MIDPOINT = {
    "5만km 미만": 25_000, "5만km~10만km 미만": 75_000,
    "10만km~15만km 미만": 125_000, "15만km~20만km 미만": 175_000,
    "20만km~25만km 미만": 225_000, "25만km이상": 300_000,
}

# ── 3. 유지비 계산 상수 ───────────────────────────────────
# 차급별 대표 배기량(cc) — 자동차관리법 시행규칙상 규모 구분 기준(1000/1600/2000cc)에
# 해당하는 대표 모델의 실제 배기량 사용 (경형=모닝 998cc, 소형=아반떼 1598cc,
# 중형=쏘나타 1999cc, 대형=그랜저 2497cc)
REPRESENTATIVE_DISPLACEMENT_CC = {"경형": 998, "소형": 1598, "중형": 1999, "대형": 2497}

# 오피넷(한국석유공사) 2026년 9월 기준 전국 평균 판매가격(원/리터)
FUEL_PRICE_PER_LITER = {"휘발유": 1859, "경유": 1844}

# 차급별 대표 공인연비(km/L) — 국토부/에너지공단 공인연비 공개자료 기준 대표값 가정
FUEL_EFFICIENCY_KM_PER_L = {"경형": 15.0, "소형": 13.5, "중형": 11.5, "대형": 9.5}


def _car_tax_per_year(cc: int) -> float:
    """배기량 구간별 cc당 자동차세액(원) — 지방세법 시행령 제131조, 비영업용 승용차 기준.
    지방교육세(자동차세의 30%) 포함 금액을 반환한다."""
    if cc <= 1000:
        base = cc * 80
    elif cc <= 1600:
        base = cc * 140
    else:
        base = cc * 200
    return base * 1.3


def _parse_kosis_wide_file(path: Path) -> pd.DataFrame:
    """KOSIS 특유의 3행 헤더(연도/구간/지표) + 병합된 라벨 열(용도/차종/규모)을
    긴 형태(long format)로 변환한다.
    반환 컬럼: 연도, 용도, 차종, 규모, 구간, 검사대수, 부적합률
    """
    raw = pd.read_excel(path, sheet_name="데이터", header=None)

    years = raw.iloc[0, 3:].tolist()
    bins_ = raw.iloc[1, 3:].tolist()
    metrics = raw.iloc[2, 3:].tolist()

    labels = raw.iloc[3:, 0:3].copy()
    labels.columns = ["용도", "차종", "규모"]
    labels = labels.ffill()
    data = raw.iloc[3:, 3:].reset_index(drop=True)
    labels = labels.reset_index(drop=True)

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


def build_lifespan_summary(df_age_full: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """차급(규모)별 평균 사용연수 요약 (승용차, 전체 용도 기준, 최신연도)"""
    sub = df_age_full[
        (df_age_full["연도"] == year)
        & (df_age_full["용도"] == "전체")
        & (df_age_full["차종"] == "승용차")
        & (df_age_full["규모"] != "합계")
        & (df_age_full["구간"] != "기타")
    ].copy()
    sub["중간값"] = sub["구간"].map(AGE_MIDPOINT)

    rows = []
    for cls, g in sub.groupby("규모"):
        total = g["검사대수"].sum()
        weighted_avg = (g["중간값"] * g["검사대수"]).sum() / total
        rows.append({"차급": cls, "평균_사용연수": round(weighted_avg, 2), "표본수(대)": int(total)})

    order = ["경형", "소형", "중형", "대형"]
    result = pd.DataFrame(rows)
    result["차급"] = pd.Categorical(result["차급"], categories=order, ordered=True)
    return result.sort_values("차급").reset_index(drop=True)


def build_mileage_summary(df_mileage_full: pd.DataFrame, year: int = 2024) -> pd.DataFrame:
    """차급(규모)별 평균 누적주행거리 요약 (승용차, 전체 용도 기준, 최신연도)"""
    sub = df_mileage_full[
        (df_mileage_full["연도"] == year)
        & (df_mileage_full["용도"] == "전체")
        & (df_mileage_full["차종"] == "승용차")
        & (df_mileage_full["규모"] != "합계")
        & (df_mileage_full["구간"] != "기타")
    ].copy()
    sub["중간값"] = sub["구간"].map(MILEAGE_MIDPOINT)

    rows = []
    for cls, g in sub.groupby("규모"):
        total = g["검사대수"].sum()
        weighted_avg = (g["중간값"] * g["검사대수"]).sum() / total
        rows.append({"차급": cls, "평균_누적주행거리_km": int(round(weighted_avg, -2)), "표본수(대)": int(total)})

    order = ["경형", "소형", "중형", "대형"]
    result = pd.DataFrame(rows)
    result["차급"] = pd.Categorical(result["차급"], categories=order, ordered=True)
    return result.sort_values("차급").reset_index(drop=True)


def build_lifespan_trend(df_age_full: pd.DataFrame) -> pd.DataFrame:
    """연도별(2015~2024) 차급별 평균 사용연수 추이"""
    sub = df_age_full[
        (df_age_full["용도"] == "전체")
        & (df_age_full["차종"] == "승용차")
        & (df_age_full["규모"] != "합계")
        & (df_age_full["구간"] != "기타")
    ].copy()
    sub["중간값"] = sub["구간"].map(AGE_MIDPOINT)

    rows = []
    for (year, cls), g in sub.groupby(["연도", "규모"]):
        total = g["검사대수"].sum()
        weighted_avg = (g["중간값"] * g["검사대수"]).sum() / total
        rows.append({"연도": year, "차급": cls, "평균_사용연수": round(weighted_avg, 2)})
    return pd.DataFrame(rows).sort_values(["차급", "연도"]).reset_index(drop=True)


def _parse_seoul_age_gender_file(path: Path) -> pd.DataFrame:
    """서울 열린데이터광장 '자동차등록현황(성별/연령별)' 파일을 긴 형태로 변환.
    반환 컬럼: 연도, 성별, 연령대, 등록대수
    """
    raw = pd.read_excel(path, sheet_name="데이터", header=None)
    years = raw.iloc[0, 2:].tolist()

    labels = raw.iloc[1:, 0:2].copy()
    labels.columns = ["성별", "연령대"]
    labels["성별"] = labels["성별"].ffill()
    labels = labels.reset_index(drop=True)
    data = raw.iloc[1:, 2:].reset_index(drop=True)

    records = []
    for row_idx in range(len(labels)):
        gender = labels.loc[row_idx, "성별"]
        age = labels.loc[row_idx, "연령대"]
        if gender == "법인 및 사업자" or age == "소계":
            continue
        for col_idx, year in enumerate(years):
            val = pd.to_numeric(data.iloc[row_idx, col_idx], errors="coerce")
            if pd.isna(val):
                continue
            records.append({"연도": int(year), "성별": gender, "연령대": age, "등록대수": int(val)})
    return pd.DataFrame(records)


def build_age_distribution_summary(df_age_full: pd.DataFrame, year: int = 2025) -> pd.DataFrame:
    """연령대별 등록대수 요약(성별 합산, 최신연도) + 비중(%)"""
    sub = df_age_full[df_age_full["연도"] == year]
    grouped = sub.groupby("연령대", as_index=False)["등록대수"].sum()
    order = ["10대 이하", "20대", "30대", "40대", "50대", "60대", "70대", "80대", "90대 이상"]
    grouped["연령대"] = pd.Categorical(grouped["연령대"], categories=order, ordered=True)
    grouped = grouped.sort_values("연령대").reset_index(drop=True)
    grouped["비중(%)"] = round(grouped["등록대수"] / grouped["등록대수"].sum() * 100, 1)
    return grouped


def build_maintenance_cost_summary(df_lifespan: pd.DataFrame, df_mileage: pd.DataFrame) -> pd.DataFrame:
    """차급 x 연료별 연간 예상 유지비 = 자동차세 + 유류비 (보험료/정비비는 개인차가 커서 제외)"""
    merged = df_lifespan.merge(df_mileage, on="차급")
    merged["연간_주행거리_km"] = merged["평균_누적주행거리_km"] / merged["평균_사용연수"]

    rows = []
    for _, row in merged.iterrows():
        cls = row["차급"]
        annual_km = row["연간_주행거리_km"]
        cc = REPRESENTATIVE_DISPLACEMENT_CC[cls]
        tax = _car_tax_per_year(cc)
        efficiency = FUEL_EFFICIENCY_KM_PER_L[cls]
        for fuel, price in FUEL_PRICE_PER_LITER.items():
            fuel_cost = (annual_km / efficiency) * price
            total = tax + fuel_cost
            rows.append({
                "차급": cls, "연료": fuel,
                "자동차세_원": int(round(tax, -2)),
                "유류비_원": int(round(fuel_cost, -2)),
                "연간_예상유지비_만원": round(total / 10_000, 1),
            })
    order = ["경형", "소형", "중형", "대형"]
    result = pd.DataFrame(rows)
    result["차급"] = pd.Categorical(result["차급"], categories=order, ordered=True)
    return result.sort_values(["차급", "연료"]).reset_index(drop=True)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    age_path = RAW_DIR / "kosis_차령별_검사현황.xlsx"
    mileage_path = RAW_DIR / "kosis_주행거리별_검사현황.xlsx"

    print("차령별 데이터 파싱 중...")
    df_age_full = _parse_kosis_wide_file(age_path)
    df_age_full.to_csv(PROCESSED_DIR / "age_distribution_full.csv", index=False, encoding="utf-8-sig")

    print("주행거리별 데이터 파싱 중...")
    df_mileage_full = _parse_kosis_wide_file(mileage_path)
    df_mileage_full.to_csv(PROCESSED_DIR / "mileage_distribution_full.csv", index=False, encoding="utf-8-sig")

    print("차급별 평균 사용연수 요약 계산 중...")
    lifespan_summary = build_lifespan_summary(df_age_full)
    lifespan_summary.to_csv(PROCESSED_DIR / "lifespan.csv", index=False, encoding="utf-8-sig")
    print(lifespan_summary)

    print("\n차급별 평균 누적주행거리 요약 계산 중...")
    mileage_summary = build_mileage_summary(df_mileage_full)
    mileage_summary.to_csv(PROCESSED_DIR / "mileage.csv", index=False, encoding="utf-8-sig")
    print(mileage_summary)

    print("\n연도별 사용연수 추이 계산 중...")
    trend = build_lifespan_trend(df_age_full)
    trend.to_csv(PROCESSED_DIR / "lifespan_trend.csv", index=False, encoding="utf-8-sig")

    print("\n서울시 연령대별/성별 등록현황 파싱 중...")
    seoul_age_path = RAW_DIR / "seoul_연령별_성별_등록현황.xlsx"
    df_seoul_age = _parse_seoul_age_gender_file(seoul_age_path)
    df_seoul_age.to_csv(PROCESSED_DIR / "age_gender_distribution_full.csv", index=False, encoding="utf-8-sig")

    age_summary = build_age_distribution_summary(df_seoul_age)
    age_summary.to_csv(PROCESSED_DIR / "age_distribution.csv", index=False, encoding="utf-8-sig")
    print(age_summary)

    print("\n차급별 유지비(자동차세+유류비) 계산 중...")
    maintenance_summary = build_maintenance_cost_summary(lifespan_summary, mileage_summary)
    maintenance_summary.to_csv(PROCESSED_DIR / "maintenance_cost.csv", index=False, encoding="utf-8-sig")
    print(maintenance_summary)

    print("\n✅ 전처리 완료")


if __name__ == "__main__":
    main()
