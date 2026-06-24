from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import OrderSide, Position
from quant.live.execution import ExecutionRouter


class FakeOms:
    def __init__(self) -> None:
        self.submissions: list[dict[str, object]] = []
        self.freeze_reasons: list[str] = []
        self.raise_on_submit: Exception | None = None

    def submit_order(self, **kwargs) -> str:
        self.submissions.append(kwargs)
        if self.raise_on_submit is not None:
            raise self.raise_on_submit
        return f"O-{len(self.submissions)}"

    def freeze_open(self, reason: str) -> None:
        self.freeze_reasons.append(reason)


def test_pending_target_missing_price_is_retained_and_freezes_open() -> None:
    oms = FakeOms()
    router = ExecutionRouter(oms, lambda: {})
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    router.set_target(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        target_qty=100,
        now=now,
    )

    submitted = router.flush_pending(now=now, latest_prices={})

    assert submitted == []
    assert [intent.symbol for intent in router.pending_targets] == ["510300.SH"]
    assert oms.submissions == []
    assert oms.freeze_reasons == ["target_price_missing: 510300.SH"]


def test_pending_target_submission_failure_is_retained_and_freezes_open() -> None:
    oms = FakeOms()
    oms.raise_on_submit = RuntimeError("store offline")
    router = ExecutionRouter(oms, lambda: {})
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    router.set_target(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        target_qty=100,
        now=now,
    )

    submitted = router.flush_pending(now=now, latest_prices={"510300.SH": 3.2})

    assert submitted == []
    assert [intent.symbol for intent in router.pending_targets] == ["510300.SH"]
    assert oms.submissions[0]["side"] == OrderSide.BUY
    assert oms.freeze_reasons == ["target_submit_error: store offline"]


def test_handled_pending_targets_are_removed_after_safe_resolution() -> None:
    oms = FakeOms()
    positions = {
        "510300.SH": Position(
            "510300.SH",
            "paper",
            qty=100,
            sellable=100,
            avg_price=3.0,
            market_value=320,
        )
    }
    router = ExecutionRouter(oms, lambda: positions)
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    router.set_target(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        target_qty=100,
        now=now,
    )
    router.set_target(
        strategy_id="dual_ma_510300",
        symbol="159915.SZ",
        target_qty=200,
        now=now,
    )

    submitted = router.flush_pending(now=now, latest_prices={})

    assert submitted == []
    assert [intent.symbol for intent in router.pending_targets] == ["159915.SZ"]
    assert oms.freeze_reasons == ["target_price_missing: 159915.SZ"]
