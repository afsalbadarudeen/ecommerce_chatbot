import json
import pathlib

import pandas as pd

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_CSV_PATH = _DATA_DIR / "products.csv"
_JSON_PATH = _DATA_DIR / "company.json"

if not _CSV_PATH.exists():
    raise FileNotFoundError(
        f"Products CSV not found: {_CSV_PATH}\n"
        "Run: cp ecommerce_dummy_products.csv data/products.csv"
    )

_products_df: pd.DataFrame = pd.read_csv(_CSV_PATH)
_products_df.columns = _products_df.columns.str.lower().str.strip()

with _JSON_PATH.open(encoding="utf-8") as _f:
    _company_info: dict = json.load(_f)


def get_products_df() -> pd.DataFrame:
    return _products_df


def get_company_info() -> dict:
    return _company_info
