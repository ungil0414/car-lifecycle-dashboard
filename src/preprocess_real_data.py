"""
preprocess_real_data.py

KOSIS에서 받은 원본 엑셀 2개를 읽어서:
1. 분석하기 쉬운 '긴 형태(long format)' 데이터로 변환 (data/processed/*_full.csv)
2. 대시보드에 바로 쓸 수 있는 '차급별 평균 사용연수 / 평균 주행거리' 요약 데이터로 가공
   (data/processed/lifespan.csv, data/processed/mileage.csv)

핵심 아이디어:
- KOSIS 원본은 '차령 구간(예: 5~6년)'별 검사대수만 제공하고, 정확한 평균값은 주지 않음
- 그래서 각 구간의 '중간값(대푯값)'을 가정해서 가중평균을 직접 계산함
  → 이 부분은 발표 때 "왜 이 가정을 썼는지" 설명이 필요한 지점이라 README/보고서에 반드시 명시할 것

실행: python src/preprocess_real_data.py
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# 차령 구간 → 대표 연수(중간값). '15년 이상'은 open-ended라 18년으로 가정.
AGE_MIDPOINT = {
    "4년 이하": 2.0,
    "5~6년": 5.5,
    "7~8년": 7.5,
    "9~10년": 9.5,
    "11~12년": 11.5,
    "13~14년": 13.5,
    "15년 이상": 18.0,
}

# 주행거리 구간 → 대표 주행거리(km, 중간값). '25만km 이상'은 30만으로 가정.
MILEAGE_MIDPOINT = {
    "5만km 미만": 25_000,
    "5만km~10만km 미만": 75_000,
    "10만km~15만km 미만": 125_000,
    "15만km~20만km 미만": 175_000,
    "20만km~25만km 미만": 225_000,
    "25만km이상": 300_000,
}


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
    labels = labels.ffill()  # 병합된 셀(NaN) 위 값으로 채우기
    data = raw.iloc[3:, 3:].reset_index(drop=True)
    labels = labels.reset_index(drop=True)

    records = []
    for col_idx in range(data.shape[1]):
        year, bin_name, metric = years[col_idx], bins_[col_idx], metrics[col_idx]
        if bin_name == "합계" or metric != "검사대수 (대)":
            continue  # 요약 열/부적합률 열은 스킵 (필요시 나중에 따로 처리)
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
    (원본은 성별/연령대가 병합 셀로 되어 있어 ffill 필요)
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
            continue  # 개인 소유 차량만 분석 대상으로 함
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


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    age_path = RAW_DIR / "kosis_차령별_검사현황.xlsx"
    mileage_path = RAW_DIR / "kosis_주행거리별_검사현황.xlsx"

    print("차령별 데이터 파싱 중...")
    df_age_full = _parse_kosis_wide_file(age_path)
    df_age_full.to_csv(PROCESSED_DIR / "age_distribution_full.csv", index=False, encoding="utf-8-sig")
    print(f"  -> {len(df_age_full)} rows 저장 (age_distribution_full.csv)")

    print("주행거리별 데이터 파싱 중...")
    df_mileage_full = _parse_kosis_wide_file(mileage_path)
    df_mileage_full.to_csv(PROCESSED_DIR / "mileage_distribution_full.csv", index=False, encoding="utf-8-sig")
    print(f"  -> {len(df_mileage_full)} rows 저장 (mileage_distribution_full.csv)")

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
    print(trend.tail(8))

    print("\n서울시 연령대별/성별 등록현황 파싱 중...")
    seoul_age_path = RAW_DIR / "seoul_연령별_성별_등록현황.xlsx"
    df_seoul_age = _parse_seoul_age_gender_file(seoul_age_path)
    df_seoul_age.to_csv(PROCESSED_DIR / "age_gender_distribution_full.csv", index=False, encoding="utf-8-sig")
    print(f"  -> {len(df_seoul_age)} rows 저장")

    age_summary = build_age_distribution_summary(df_seoul_age)
    age_summary.to_csv(PROCESSED_DIR / "age_distribution.csv", index=False, encoding="utf-8-sig")
    print(age_summary)

    print("\n✅ 전처리 완료")


if __name__ == "__main__":
    main()
