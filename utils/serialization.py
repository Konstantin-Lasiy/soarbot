from typing import Any


def make_serializable(obj: Any) -> Any:
    """Recursively convert numpy/pandas types into JSON-serializable values.

    - pandas.Timestamp / numpy.datetime64 -> ISO-ish string via str(...)
    - pandas NaT / NaN -> None
    - numpy scalars -> .item()
    - numpy arrays -> .tolist()
    - dict/list -> recurse
    """
    try:
        import pandas as pd  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        pd = None  # type: ignore
        np = None  # type: ignore

    # pandas.Timestamp (including tz-aware). Avoid .isoformat() to keep type-checkers happy.
    if pd is not None and isinstance(obj, pd.Timestamp):
        if pd.isna(obj):
            return None
        return str(obj)

    # numpy.datetime64
    if np is not None and isinstance(obj, np.datetime64):
        if pd is not None and pd.isna(obj):
            return None
        if pd is not None:
            return str(pd.Timestamp(obj))
        return str(obj)

    # pandas NA/NaT/NaN and similar
    if pd is not None:
        try:
            if pd.isna(obj):
                return None
        except Exception:
            pass

    # numpy scalar
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass

    # numpy array / pandas Series
    if hasattr(obj, "tolist"):
        try:
            return obj.tolist()
        except Exception:
            pass

    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [make_serializable(v) for v in obj]

    return obj


