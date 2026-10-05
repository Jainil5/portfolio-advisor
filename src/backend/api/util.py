import math

import numpy as np
import pandas as pd


def clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        f = float(value)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def records(df: pd.DataFrame) -> list:
    if df.empty:
        return []
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]
