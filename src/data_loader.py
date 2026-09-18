"""
data_loader.py

data/processed/ 폴더에 전처리된 실제 데이터 CSV가 있으면 이를 우선 사용하고,
없으면 sample_data.py 의 가상 데이터로 자동 대체합니다.

실제 KOSIS 원본 데이터는 data/raw/ 에 있고,
src/preprocess_real_data.py 를 실행하면 data/processed/ 에 정리된 CSV가 생성됩니다.
"""

from pathlib import Path
import pandas as pd

from src import sample_data

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def _load_or_fallback(filename: str, fallback_func) -> tuple[pd.DataFrame, bool]:
    """processed 폴더에 실제 데이터가 있으면 읽고, 없으면 fallback 함수(가상데이터)를 사용.
    반환값: (데이터프레임, 실제데이터여부)
    """
    processed_path = PROCESSED_DIR / filename
    if processed_path.exists():
        return pd.read_csv(processed_path), True
    raw_path = RAW_DIR / filename
    if raw_path.exists():
        return pd.read_csv(raw_path), True
    return fallback_func(), False


def load_lifespan_data():
    return _load_or_fallback("lifespan.csv", sample_data.get_lifespan_data)


def load_mileage_data():
    return _load_or_fallback("mileage.csv", sample_data.get_mileage_data)


def load_lifespan_trend():
    """실제 데이터(연도별 추이)만 존재. 없으면 빈 데이터프레임 반환."""
    path = PROCESSED_DIR / "lifespan_trend.csv"
    if path.exists():
        return pd.read_csv(path), True
    return pd.DataFrame(columns=["연도", "차급", "평균_사용연수"]), False


def load_age_distribution_data():
    """연령대별 자동차 등록현황 (서울시, 실제 데이터)"""
    return _load_or_fallback("age_distribution.csv", sample_data.get_age_distribution_data)


def load_age_gender_trend():
    """연령대별/성별 등록대수 연도별(2023~2025) 추이 (실제 데이터 없으면 빈 DF)"""
    path = PROCESSED_DIR / "age_gender_distribution_full.csv"
    if path.exists():
        return pd.read_csv(path), True
    return pd.DataFrame(columns=["연도", "성별", "연령대", "등록대수"]), False


def load_maintenance_cost_data():
    return _load_or_fallback("maintenance_cost.csv", sample_data.get_maintenance_cost_data)
