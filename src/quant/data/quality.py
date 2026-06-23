import pandas as pd


def reject_missing_rows(frame: pd.DataFrame) -> None:
    missing = frame[frame["data_status"] == "missing"]
    if not missing.empty:
        symbols = sorted(missing["symbol"].unique())
        raise ValueError(f"history contains missing data for {symbols}")
