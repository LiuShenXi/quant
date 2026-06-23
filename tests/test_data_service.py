from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from quant.data.service import DataService


def test_history_is_cut_off_by_end_time() -> None:
    service = DataService(Path("data_sample"))
    end = datetime(2024, 1, 5, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    history = service.history("510300.SH", end=end, n=10)
    assert history["dt"].max() <= end
    assert len(history) == 4


def test_history_qfq_uses_request_end_as_factor_base() -> None:
    service = DataService(Path("data_sample"))
    end = datetime(2024, 1, 8, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    history = service.history("510300.SH", end=end, n=10, fields=["close"], adjust="qfq")
    first_close = history.iloc[0]["close"]
    assert round(first_close, 4) == 2.7870


def test_missing_data_status_is_rejected() -> None:
    service = DataService(Path("data_sample"))
    end = datetime(2024, 1, 9, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    try:
        service.history("159999.SZ", end=end, n=2)
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("missing data must fail")
