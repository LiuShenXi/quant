# M3 Paper Trading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build M3 in two explicit sub-phases: M3a implements deterministic Paper infrastructure with local bar replay; M3b uses that same infrastructure for the 10-trading-day Paper observation gate required before real-money trading.

**Architecture:** Add a `quant.live` package beside the existing backtest slice. Strategies continue to see only `quant.core.contract`; Paper mode routes strategy orders through `LiveContext -> RiskEngine -> OrderManager -> SimGateway`, while SQLite and JSONL keep a write-ahead audit trail. M3a uses deterministic local replay for implementation and regression tests; M3b runs the same engine on scheduled daily Paper operation and drills disconnect/reconciliation/CRIT alerts. QMT, real broker adapters, minute bars, web UI, and real-money OMS deployment remain M4+.

**Tech Stack:** Python 3.11+, pytest, pydantic v2, PyYAML, pandas, stdlib `sqlite3`, stdlib `queue`, stdlib `threading`, loguru, existing `Matcher`, `CostModel`, `Portfolio`, ruff, import-linter, uv.

## Global Constraints

- Market scope: A股 ETF only for M3; daily bars only.
- Runtime scope: Paper trading only; no QMT, no true broker gateway, no real-money order submission.
- Phase boundary: M3a completion means local deterministic Paper replay passes; M3 is not accepted as the real-money pre-gate until M3b completes 10 trading days of Paper observation with daily reconciliation, one disconnect drill, and verified CRIT alert delivery.
- Strategy boundary: strategies may import `quant.core.contract` plus standard library, numpy, and pandas only.
- Runtime mode: `runtime_mode` may be `backtest` or `paper`; `live` is still rejected until M4.
- Order path: every Paper order must pass `RiskEngine` before `OrderManager` sends it to `SimGateway`.
- Daily-bar execution: `set_target()` called from a 15:00 daily bar records a target intent; the Paper runtime converts it into broker orders at the next tradable bar open, and trading-session checks run at that broker-send time.
- Persistence: every local order is written to SQLite before any gateway send attempt.
- Audit trail: every order, trade, rejection, reconciliation, alert, and manual ops action is appended to JSONL.
- Recovery: Paper engine startup must reconcile local state and gateway state before accepting strategy orders.
- Failure semantics: risk exceptions, gateway disconnects, stale market data, and reconciliation failures freeze or halt safely; they never silently allow new opening orders.
- Verification requirement: every task ends with a fresh test command and an explicit commit.
- Deliberately excluded: QMT, true live mode, real broker order submission, minute/tick bars, web UI, multi-account production operations, and mobile-command trading.

---

## Target File Structure

Extend the existing project under `quant/`:

```text
quant/
├── config/
│   ├── paper.yaml
│   ├── risk/global.yaml
│   └── strategies/dual_ma_510300_paper.yaml
├── docs/runbooks/
│   ├── paper_daily_runbook.md
│   └── paper_observation_checklist.md
├── scripts/
│   ├── ops.py
│   └── run_paper.py
├── src/quant/
│   ├── live/
│   │   ├── __init__.py
│   │   ├── alerts.py
│   │   ├── config.py
│   │   ├── context.py
│   │   ├── engine.py
│   │   ├── execution.py
│   │   ├── events.py
│   │   ├── monitor.py
│   │   ├── oms.py
│   │   ├── reconcile.py
│   │   ├── store.py
│   │   ├── types.py
│   │   └── gateway/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       └── sim.py
│   └── risk/
│       ├── __init__.py
│       ├── checks.py
│       └── pipeline.py
└── tests/
    ├── golden_paper/
    ├── test_live_config.py
    ├── test_live_events.py
    ├── test_live_store.py
    ├── test_risk_pipeline.py
    ├── test_oms.py
    ├── test_sim_gateway.py
    ├── test_reconcile.py
    ├── test_paper_engine.py
    ├── test_alerts_monitor.py
    ├── test_ops_cli.py
    ├── test_paper_golden.py
    └── test_m3_paper_gate_docs.py
```

## Shared Interface Decisions

These names are used throughout the plan. Keep them stable while implementing M3.

```python
# src/quant/live/types.py
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from quant.core.contract import Account, Order, OrderSide, OrderStatus, OrderType, Position, Trade


class EngineState(StrEnum):
    NORMAL = "NORMAL"
    FREEZE_OPEN = "FREEZE_OPEN"
    HALT = "HALT"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    CRIT = "CRIT"


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    strategy_id: str
    account_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None
    created_at: datetime


@dataclass(frozen=True)
class BrokerOrderSnapshot:
    broker_order_id: str
    order_id: str
    symbol: str
    side: OrderSide
    type: OrderType
    qty: float
    price: float | None
    status: OrderStatus
    filled_qty: float
    remaining_qty: float
    avg_fill_price: float
    updated_at: datetime
    reject_reason: str | None = None


@dataclass(frozen=True)
class BrokerTradeSnapshot:
    broker_trade_id: str
    broker_order_id: str
    order_id: str
    strategy_id: str
    account_id: str
    symbol: str
    side: OrderSide
    qty: float
    price: float
    commission: float
    dt: datetime
```

```python
# src/quant/live/gateway/base.py
from abc import ABC, abstractmethod
from collections.abc import Callable

from quant.core.contract import Account, Bar, Order, Position, Trade
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot, OrderRequest


class GatewayBase(ABC):
    name: str

    def __init__(self) -> None:
        self._on_bar = lambda bar: None
        self._on_order = lambda order: None
        self._on_trade = lambda trade: None
        self._on_disconnect = lambda reason: None

    def set_callbacks(
        self,
        *,
        on_bar: Callable[[Bar], None],
        on_order: Callable[[BrokerOrderSnapshot], None],
        on_trade: Callable[[BrokerTradeSnapshot], None],
        on_disconnect: Callable[[str], None],
    ) -> None:
        self._on_bar = on_bar
        self._on_order = on_order
        self._on_trade = on_trade
        self._on_disconnect = on_disconnect

    @abstractmethod
    def connect(self, conf: dict[str, object]) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, symbols: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_order(self, req: OrderRequest) -> str:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def query_account(self) -> Account:
        raise NotImplementedError

    @abstractmethod
    def query_positions(self) -> dict[str, Position]:
        raise NotImplementedError

    @abstractmethod
    def query_orders(self, active_only: bool = True) -> list[BrokerOrderSnapshot]:
        raise NotImplementedError
```

---

### Task 1: Paper Configuration And Live Package Skeleton

**Files:**
- Modify: `src/quant/core/config.py`
- Create: `src/quant/live/__init__.py`
- Create: `src/quant/live/config.py`
- Create: `config/paper.yaml`
- Create: `config/risk/global.yaml`
- Create: `config/strategies/dual_ma_510300_paper.yaml`
- Test: `tests/test_live_config.py`

**Interfaces:**
- Consumes: existing `StrategyConfig`, `RiskConfig`, `load_yaml`
- Produces: `PaperConfig`, `load_paper_config(path: Path) -> PaperConfig`
- Produces: `StrategyConfig.runtime_mode: Literal["backtest", "paper"]`

- [ ] **Step 1: Write config tests**

Create `tests/test_live_config.py`:

```python
from pathlib import Path

import pytest
from pydantic import ValidationError

from quant.core.config import StrategyConfig, load_strategy_config
from quant.live.config import PaperConfig, load_paper_config


def test_strategy_config_accepts_paper_but_rejects_live() -> None:
    config = load_strategy_config(Path("config/strategies/dual_ma_510300_paper.yaml"))
    assert config.runtime_mode == "paper"
    assert config.risk.max_order_value == 100_000

    with pytest.raises(ValidationError):
        StrategyConfig.model_validate(
            {
                "id": "bad_live",
                "class": "strategies.dual_ma:DualMA",
                "version": "1.0.0",
                "universe": ["510300.SH"],
                "freq": "1d",
                "params": {"symbol": "510300.SH"},
                "runtime_mode": "live",
            }
        )


def test_paper_config_loads_paths_and_thresholds() -> None:
    config = load_paper_config(Path("config/paper.yaml"))
    assert config.account_id == "paper"
    assert config.store_path.as_posix() == "runtime/paper/meta.db"
    assert config.events_path.as_posix() == "runtime/paper/events.jsonl"
    assert config.reconciliation.cash_tolerance == 0.01
    assert config.monitor.market_data_staleness_sec == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_live_config.py -q
```

Expected: FAIL because `quant.live.config` does not exist and `runtime_mode="paper"` is not accepted yet.

- [ ] **Step 3: Extend existing strategy config**

Modify `src/quant/core/config.py`:

```python
class RiskConfig(BaseModel):
    max_order_value: float | None = None
    max_position_value: float | None = None
    max_gross_exposure_pct: float | None = None
    max_orders_per_minute: int | None = None


class StrategyConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    class_path: str = Field(alias="class")
    version: str
    universe: list[str]
    freq: Literal["1d"]
    params: dict[str, Any]
    risk: RiskConfig = Field(default_factory=RiskConfig)
    runtime_mode: Literal["backtest", "paper"]
```

Keep the existing validators. Do not add `live` until M4.

- [ ] **Step 4: Add Paper config models**

Create `src/quant/live/__init__.py`:

```python
"""Paper trading and live-runtime infrastructure."""
```

Create `src/quant/live/config.py`:

```python
from pathlib import Path

from pydantic import BaseModel

from quant.core.config import load_yaml


class ReconciliationConfig(BaseModel):
    cash_tolerance: float = 0.01
    position_qty_tolerance: float = 0
    auto_repair_cash_drift_below: float = 1.0


class MonitorConfig(BaseModel):
    market_data_staleness_sec: int = 60
    gateway_heartbeat_sec: int = 30
    alert_dedupe_sec: int = 300


class PaperConfig(BaseModel):
    account_id: str
    initial_cash: float
    timezone: str = "Asia/Shanghai"
    data_root: Path
    store_path: Path
    events_path: Path
    run_root: Path
    reconciliation: ReconciliationConfig = ReconciliationConfig()
    monitor: MonitorConfig = MonitorConfig()


def load_paper_config(path: Path) -> PaperConfig:
    return PaperConfig.model_validate(load_yaml(path))
```

- [ ] **Step 5: Add example YAML files**

Create `config/paper.yaml`:

```yaml
account_id: paper
initial_cash: 100000
timezone: Asia/Shanghai
data_root: data_sample
store_path: runtime/paper/meta.db
events_path: runtime/paper/events.jsonl
run_root: runtime/paper/runs
reconciliation:
  cash_tolerance: 0.01
  position_qty_tolerance: 0
  auto_repair_cash_drift_below: 1.0
monitor:
  market_data_staleness_sec: 60
  gateway_heartbeat_sec: 30
  alert_dedupe_sec: 300
```

Create `config/risk/global.yaml`:

```yaml
whitelist_mode: true
price_collar_pct: 0.02
max_order_value: 200000
max_position_value_per_symbol: 500000
max_gross_exposure_pct: 0.95
max_orders_per_minute: 10
max_cancel_ratio_daily: 0.5
kill_switch:
  daily_loss_freeze_pct: 0.02
  daily_loss_halt_pct: 0.04
market_data_staleness_sec: 60
```

Create `config/strategies/dual_ma_510300_paper.yaml`:

```yaml
id: dual_ma_510300
class: strategies.dual_ma:DualMA
version: "1.0.0"
universe: ["510300.SH"]
freq: "1d"
params:
  symbol: "510300.SH"
  fast: 3
  slow: 5
  target_qty: 10000
risk:
  max_order_value: 100000
  max_position_value: 100000
runtime_mode: paper
```

- [ ] **Step 6: Verify config**

Run:

```bash
pytest tests/test_live_config.py -q
ruff check src/quant/core/config.py src/quant/live/config.py tests/test_live_config.py
```

Expected: config tests pass and ruff reports no issues.

- [ ] **Step 7: Commit**

```bash
git add src/quant/core/config.py src/quant/live/__init__.py src/quant/live/config.py config/paper.yaml config/risk/global.yaml config/strategies/dual_ma_510300_paper.yaml tests/test_live_config.py
git commit -m "feat: add paper runtime config"
```

### Task 2: Live DTOs, Gateway Base, And Event Journal

**Files:**
- Create: `src/quant/live/types.py`
- Create: `src/quant/live/gateway/__init__.py`
- Create: `src/quant/live/gateway/base.py`
- Create: `src/quant/live/events.py`
- Test: `tests/test_live_events.py`

**Interfaces:**
- Consumes: `quant.core.contract` types
- Produces: `EngineState`, `AlertSeverity`, `OrderRequest`, `BrokerOrderSnapshot`, `BrokerTradeSnapshot`
- Produces: `GatewayBase`
- Produces: `EventJournal.append(event_type: str, payload: dict[str, object]) -> int`

- [ ] **Step 1: Write event and gateway tests**

Create `tests/test_live_events.py`:

```python
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import OrderSide, OrderStatus, OrderType
from quant.live.events import EventJournal
from quant.live.types import BrokerOrderSnapshot, EngineState, OrderRequest


def test_order_request_and_snapshot_are_stable_contracts() -> None:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    req = OrderRequest(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.2,
        created_at=now,
    )
    snapshot = BrokerOrderSnapshot(
        broker_order_id="PAPER-O-1",
        order_id=req.order_id,
        symbol=req.symbol,
        side=req.side,
        type=req.type,
        qty=req.qty,
        price=req.price,
        status=OrderStatus.SUBMITTED,
        filled_qty=0,
        remaining_qty=req.qty,
        avg_fill_price=0,
        updated_at=now,
    )
    assert snapshot.broker_order_id == "PAPER-O-1"
    assert EngineState.FREEZE_OPEN.value == "FREEZE_OPEN"


def test_event_journal_appends_jsonl_with_sequence(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    written_at = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    journal = EventJournal(path, clock=lambda: written_at)
    seq1 = journal.append("engine_state", {"state": "NORMAL"})
    seq2 = journal.append("order", {"order_id": "O-1", "status": "SUBMITTED"})

    assert (seq1, seq2) == (1, 2)
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [line["seq"] for line in lines] == [1, 2]
    assert lines[0]["type"] == "engine_state"
    assert lines[0]["written_at"] == written_at.isoformat()
    assert journal.last_seq == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_live_events.py -q
```

Expected: FAIL because `quant.live.types` and `quant.live.events` do not exist.

- [ ] **Step 3: Implement DTOs and gateway base**

Implement `src/quant/live/types.py` using the shared interface block at the top of this plan. Add this extra DTO for alerts:

```python
@dataclass(frozen=True)
class Alert:
    severity: AlertSeverity
    key: str
    message: str
    created_at: datetime
    payload: dict[str, object]
```

Create `src/quant/live/gateway/__init__.py`:

```python
"""Gateway abstractions for paper and future live trading."""
```

Create `src/quant/live/gateway/base.py` using the shared `GatewayBase` interface at the top of this plan. `set_callbacks` stores the callbacks on `self`; initialize all callbacks to no-op lambdas in `GatewayBase.__init__`.

- [ ] **Step 4: Implement EventJournal**

Create `src/quant/live/events.py`:

```python
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class EventJournal:
    def __init__(
        self,
        path: Path,
        timezone: str = "Asia/Shanghai",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path
        self.timezone = ZoneInfo(timezone)
        self.clock = clock or (lambda: datetime.now(self.timezone))
        self._seq = self._load_last_seq()

    @property
    def last_seq(self) -> int:
        return self._seq

    def append(self, event_type: str, payload: dict[str, object]) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seq += 1
        written_at = self.clock()
        if written_at.tzinfo is None or written_at.utcoffset() is None:
            written_at = written_at.replace(tzinfo=self.timezone)
        event = {
            "seq": self._seq,
            "type": event_type,
            "written_at": written_at.isoformat(),
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return self._seq

    def _load_last_seq(self) -> int:
        if not self.path.exists():
            return 0
        last_seq = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                last_seq = int(json.loads(line)["seq"])
        return last_seq
```

- [ ] **Step 5: Verify DTOs and events**

Run:

```bash
pytest tests/test_live_events.py -q
ruff check src/quant/live/types.py src/quant/live/gateway src/quant/live/events.py tests/test_live_events.py
```

Expected: tests pass and ruff reports no issues.

- [ ] **Step 6: Commit**

```bash
git add src/quant/live/types.py src/quant/live/gateway src/quant/live/events.py tests/test_live_events.py
git commit -m "feat: add live gateway contracts and event journal"
```

### Task 3: SQLite OMS Store

**Files:**
- Create: `src/quant/live/store.py`
- Test: `tests/test_live_store.py`

**Interfaces:**
- Consumes: `Order`, `Trade`, `EngineState`, `EventJournal`
- Produces: `OmsStore(path: Path)`
- Produces: `init_schema()`, `save_order(order)`, `update_order(order)`, `get_order(order_id)`, `list_orders(active_only=False)`
- Produces: `save_trade_once(trade) -> bool`, `list_trades()`
- Produces: `save_account_snapshot(account, positions, updated_at)`, `load_account_snapshot()`
- Produces: `is_empty() -> bool`
- Produces: `map_broker_order_id(order_id, broker_order_id)`, `get_order_id_by_broker(broker_order_id)`
- Produces: `set_engine_state(state, reason)`, `get_engine_state()`
- Produces: `save_kv(key, value)`, `load_kv(key, default=None)`

- [ ] **Step 1: Write persistence tests**

Create `tests/test_live_store.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, Order, OrderSide, OrderStatus, OrderType, Position, Trade
from quant.live.store import OmsStore
from quant.live.types import EngineState


def make_order(status: OrderStatus = OrderStatus.SUBMITTED) -> Order:
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    return Order(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.2,
        status=status,
        filled_qty=0,
        remaining_qty=1000,
        avg_fill_price=0,
        created_at=now,
        updated_at=now,
    )


def test_store_persists_order_mapping_and_engine_state(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    assert store.is_empty() is True
    store.save_order(make_order())
    store.map_broker_order_id("O-1", "PAPER-O-1")
    store.set_engine_state(EngineState.FREEZE_OPEN, "disconnect")

    reopened = OmsStore(tmp_path / "meta.db")
    reopened.init_schema()
    assert reopened.get_order("O-1").broker_order_id == "PAPER-O-1"
    assert reopened.get_order_id_by_broker("PAPER-O-1") == "O-1"
    assert reopened.get_engine_state() == EngineState.FREEZE_OPEN
    assert reopened.is_empty() is False


def test_store_deduplicates_trades_by_broker_trade_id(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    now = datetime(2024, 1, 3, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    trade = Trade(
        trade_id="T-1",
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=500,
        price=3.2,
        commission=5,
        dt=now,
        broker_order_id="PAPER-O-1",
        broker_trade_id="PAPER-T-1",
    )

    assert store.save_trade_once(trade) is True
    assert store.save_trade_once(trade) is False
    assert len(store.list_trades()) == 1


def test_store_persists_account_and_position_snapshot(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    now = datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    account = Account("paper", "CNY", cash=98_395, frozen=0, market_value=1_500, total_value=99_895)
    positions = {
        "510300.SH": Position(
            "510300.SH",
            "paper",
            qty=500,
            sellable=0,
            avg_price=3.0,
            market_value=1_500,
        )
    }

    store.save_account_snapshot(account, positions, now)
    snapshot = store.load_account_snapshot()
    assert snapshot.account.cash == 98_395
    assert snapshot.positions["510300.SH"].qty == 500
    assert snapshot.updated_at == now
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_live_store.py -q
```

Expected: FAIL because `quant.live.store` does not exist.

- [ ] **Step 3: Implement schema**

Create `src/quant/live/store.py` with these tables:

```sql
CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  strategy_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  type TEXT NOT NULL,
  qty REAL NOT NULL,
  price REAL,
  status TEXT NOT NULL,
  filled_qty REAL NOT NULL,
  remaining_qty REAL NOT NULL,
  avg_fill_price REAL NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  broker_order_id TEXT,
  reject_reason TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_broker_order_id
ON orders(broker_order_id)
WHERE broker_order_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS trades (
  trade_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  strategy_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty REAL NOT NULL,
  price REAL NOT NULL,
  commission REAL NOT NULL,
  dt TEXT NOT NULL,
  broker_order_id TEXT,
  broker_trade_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS account_snapshots (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  account_id TEXT NOT NULL,
  currency TEXT NOT NULL,
  cash REAL NOT NULL,
  frozen REAL NOT NULL,
  market_value REAL NOT NULL,
  total_value REAL NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS position_snapshots (
  symbol TEXT PRIMARY KEY,
  account_id TEXT NOT NULL,
  qty REAL NOT NULL,
  sellable REAL NOT NULL,
  avg_price REAL NOT NULL,
  market_value REAL NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engine_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  state TEXT NOT NULL,
  reason TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

Use `dataclasses.asdict`, enum `.value`, and `datetime.isoformat()` for writes. Use `datetime.fromisoformat()` and enum constructors for reads.

- [ ] **Step 4: Implement methods**

Implement `OmsStore` with a fresh SQLite connection per method:

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from quant.core.contract import Account, Order, Position, Trade
from quant.live.types import EngineState


@dataclass(frozen=True)
class AccountSnapshot:
    account: Account
    positions: dict[str, Position]
    updated_at: datetime


class OmsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def init_schema(self) -> None:
        raise NotImplementedError

    def save_order(self, order: Order) -> None:
        raise NotImplementedError

    def update_order(self, order: Order) -> None:
        raise NotImplementedError

    def get_order(self, order_id: str) -> Order:
        raise NotImplementedError

    def list_orders(self, active_only: bool = False) -> list[Order]:
        raise NotImplementedError

    def save_trade_once(self, trade: Trade) -> bool:
        raise NotImplementedError

    def list_trades(self) -> list[Trade]:
        raise NotImplementedError

    def save_account_snapshot(
        self,
        account: Account,
        positions: dict[str, Position],
        updated_at: datetime,
    ) -> None:
        raise NotImplementedError

    def load_account_snapshot(self) -> AccountSnapshot | None:
        raise NotImplementedError

    def is_empty(self) -> bool:
        raise NotImplementedError

    def map_broker_order_id(self, order_id: str, broker_order_id: str) -> None:
        raise NotImplementedError

    def get_order_id_by_broker(self, broker_order_id: str) -> str | None:
        raise NotImplementedError

    def set_engine_state(self, state: EngineState, reason: str) -> None:
        raise NotImplementedError

    def get_engine_state(self) -> EngineState:
        raise NotImplementedError

    def save_kv(self, key: str, value: object) -> None:
        raise NotImplementedError

    def load_kv(self, key: str, default: object | None = None) -> object | None:
        raise NotImplementedError
```

`get_engine_state()` returns `EngineState.NORMAL` if the row does not exist.

- [ ] **Step 5: Verify store**

Run:

```bash
pytest tests/test_live_store.py -q
ruff check src/quant/live/store.py tests/test_live_store.py
```

Expected: store tests pass and ruff reports no issues.

- [ ] **Step 6: Commit**

```bash
git add src/quant/live/store.py tests/test_live_store.py
git commit -m "feat: add sqlite oms store"
```

### Task 4: Risk Pipeline And Kill Switch

**Files:**
- Modify: `src/quant/risk/checks.py`
- Create: `src/quant/risk/pipeline.py`
- Test: `tests/test_risk_pipeline.py`

**Interfaces:**
- Consumes: `OrderRequest`, `EngineState`, `Account`, `Position`, active `Order` list
- Produces: `RiskDecision(allowed: bool, reason: str | None, rule_id: str | None)`
- Produces: `RiskLimits`
- Produces: `RiskEngine.check_order(req, *, latest_price, account, positions, active_orders, now, state) -> RiskDecision`
- Produces: `RiskEngine.on_equity(total_value, now) -> EngineState | None`

- [ ] **Step 1: Write risk tests**

Create `tests/test_risk_pipeline.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, OrderSide, OrderType, Position
from quant.live.types import EngineState, OrderRequest
from quant.risk.pipeline import RiskEngine, RiskLimits


def make_req(side: OrderSide = OrderSide.BUY, price: float = 3.2, qty: float = 1000) -> OrderRequest:
    return OrderRequest(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=side,
        type=OrderType.LIMIT,
        qty=qty,
        price=price,
        created_at=datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def make_account(cash: float = 100_000, total_value: float = 100_000) -> Account:
    return Account("paper", "CNY", cash=cash, frozen=0, market_value=0, total_value=total_value)


def test_risk_rejects_symbol_outside_universe() -> None:
    engine = RiskEngine(
        RiskLimits(
            universe={"159915.SZ"},
            price_collar_pct=0.02,
            max_order_value=200_000,
            max_position_value_per_symbol=500_000,
            max_gross_exposure_pct=0.95,
            max_orders_per_minute=10,
        )
    )
    decision = engine.check_order(
        make_req(),
        latest_price=3.2,
        account=make_account(),
        positions={},
        active_orders=[],
        now=make_req().created_at,
        state=EngineState.NORMAL,
    )
    assert decision.allowed is False
    assert decision.rule_id == "symbol_whitelist"


def test_freeze_open_blocks_buy_but_allows_sell() -> None:
    engine = RiskEngine(RiskLimits(universe={"510300.SH"}))
    sellable = Position("510300.SH", "paper", qty=1000, sellable=1000, avg_price=3.0, market_value=3200)

    buy = engine.check_order(
        make_req(OrderSide.BUY),
        latest_price=3.2,
        account=make_account(),
        positions={"510300.SH": sellable},
        active_orders=[],
        now=make_req().created_at,
        state=EngineState.FREEZE_OPEN,
    )
    sell = engine.check_order(
        make_req(OrderSide.SELL),
        latest_price=3.2,
        account=make_account(),
        positions={"510300.SH": sellable},
        active_orders=[],
        now=make_req().created_at,
        state=EngineState.FREEZE_OPEN,
    )
    assert buy.rule_id == "engine_state"
    assert sell.allowed is True


def test_daily_loss_moves_to_halt() -> None:
    engine = RiskEngine(
        RiskLimits(
            universe={"510300.SH"},
            daily_loss_freeze_pct=0.02,
            daily_loss_halt_pct=0.04,
        )
    )
    now = make_req().created_at
    assert engine.on_equity(100_000, now) is None
    assert engine.on_equity(95_000, now) == EngineState.HALT
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_risk_pipeline.py -q
```

Expected: FAIL because `quant.risk.pipeline` does not exist.

- [ ] **Step 3: Keep quantity helper and add time helper**

Modify `src/quant/risk/checks.py`:

```python
from datetime import time


def round_down_qty(qty: float, lot_size: int, qty_step: int) -> float:
    if qty < lot_size:
        return 0
    return qty - (qty % qty_step)


def is_cn_continuous_auction(value: time) -> bool:
    return time(9, 30) <= value <= time(11, 30) or time(13, 0) <= value <= time(14, 57)
```

- [ ] **Step 4: Implement risk pipeline**

Create `src/quant/risk/pipeline.py`:

```python
from dataclasses import dataclass, field
from datetime import date, datetime

from quant.core.contract import Account, Order, OrderSide, Position
from quant.live.types import EngineState, OrderRequest
from quant.risk.checks import is_cn_continuous_auction


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str | None = None
    rule_id: str | None = None


@dataclass(frozen=True)
class RiskLimits:
    universe: set[str]
    price_collar_pct: float = 0.02
    max_order_value: float = 200_000
    max_position_value_per_symbol: float = 500_000
    max_gross_exposure_pct: float = 0.95
    max_orders_per_minute: int = 10
    daily_loss_freeze_pct: float = 0.02
    daily_loss_halt_pct: float = 0.04


@dataclass
class RiskEngine:
    limits: RiskLimits
    day_start_value: float | None = None
    day: date | None = None
    order_timestamps: list[datetime] = field(default_factory=list)

    def check_order(
        self,
        req: OrderRequest,
        *,
        latest_price: float,
        account: Account,
        positions: dict[str, Position],
        active_orders: list[Order],
        now: datetime,
        state: EngineState,
    ) -> RiskDecision:
        raise NotImplementedError

    def on_equity(self, total_value: float, now: datetime) -> EngineState | None:
        raise NotImplementedError
```

Implement checks in this exact order:

1. `engine_state`: `HALT` rejects all orders; `FREEZE_OPEN` rejects `BUY` only.
2. `symbol_whitelist`: symbol must be in `limits.universe`.
3. `trading_session`: `is_cn_continuous_auction(now.time())` must be true.
4. `price_collar`: if limit price exists, absolute deviation from `latest_price` must be `<= price_collar_pct`.
5. `max_order_value`: `qty * effective_price <= max_order_value`.
6. `cash`: BUY needs enough cash for notional; SELL needs enough `Position.sellable`.
7. `position_limit`: projected symbol market value must be within per-symbol limit.
8. `gross_exposure`: projected gross exposure divided by account total value must be within limit.
9. `order_frequency`: timestamps in the previous 60 seconds must not exceed max.
10. `self_cross`: reject if active order in same symbol has opposite side and crossing price.

Use `RiskDecision(False, "human readable reason", "rule_id")` for rejects and `RiskDecision(True)` for accepts. If `check_order()` itself catches an exception, return `RiskDecision(False, f"risk_engine_error: {error}", "risk_engine_error")`.

- [ ] **Step 5: Verify risk**

Run:

```bash
pytest tests/test_risk_pipeline.py tests/test_portfolio_costs.py -q
ruff check src/quant/risk tests/test_risk_pipeline.py
```

Expected: risk tests and existing portfolio tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/quant/risk/checks.py src/quant/risk/pipeline.py tests/test_risk_pipeline.py
git commit -m "feat: add paper risk pipeline"
```

### Task 5: Order Manager

**Files:**
- Create: `src/quant/live/oms.py`
- Test: `tests/test_oms.py`

**Interfaces:**
- Consumes: `GatewayBase`, `OmsStore`, `EventJournal`, `RiskEngine`, `OrderRequest`, broker snapshots
- Produces: `OrderManager.submit_order(strategy_id, symbol, side, qty, price, type, latest_price, now) -> str`
- Produces: `OrderManager.cancel_order(order_id: str) -> None`
- Produces: `OrderManager.on_broker_order(snapshot: BrokerOrderSnapshot) -> Order`
- Produces: `OrderManager.on_broker_trade(snapshot: BrokerTradeSnapshot) -> Trade | None`
- Produces: `OrderManager.freeze_open(reason: str)`, `OrderManager.halt(reason: str)`, `OrderManager.resume(reason: str)`

- [ ] **Step 1: Write OMS tests**

Create `tests/test_oms.py` with a fake gateway:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Account, OrderSide, OrderStatus, OrderType
from quant.live.events import EventJournal
from quant.live.oms import OrderManager
from quant.live.store import OmsStore
from quant.live.types import BrokerTradeSnapshot, EngineState
from quant.risk.pipeline import RiskEngine, RiskLimits


class FakeGateway:
    name = "fake"

    def __init__(self) -> None:
        self.sent = []
        self.cancelled = []

    def send_order(self, req):
        self.sent.append(req)
        return f"PAPER-{req.order_id}"

    def cancel_order(self, broker_order_id: str) -> None:
        self.cancelled.append(broker_order_id)

    def query_account(self):
        return Account("paper", "CNY", 100_000, 0, 0, 100_000)

    def query_positions(self):
        return {}

    def query_orders(self, active_only: bool = True):
        return []


def make_manager(tmp_path, universe={"510300.SH"}) -> OrderManager:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    return OrderManager(
        account_id="paper",
        gateway=FakeGateway(),
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        risk=RiskEngine(RiskLimits(universe=set(universe))),
    )


def test_submit_order_writes_before_gateway_send(tmp_path) -> None:
    manager = make_manager(tmp_path)
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    order_id = manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )
    order = manager.store.get_order(order_id)
    assert order.status == OrderStatus.SUBMITTED
    assert order.broker_order_id == "PAPER-O-1"
    assert manager.gateway.sent[0].order_id == order_id


def test_risk_reject_creates_rejected_order_without_gateway_send(tmp_path) -> None:
    manager = make_manager(tmp_path, universe={"159915.SZ"})
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    order_id = manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )
    order = manager.store.get_order(order_id)
    assert order.status == OrderStatus.REJECTED
    assert order.reject_reason.startswith("symbol_whitelist")
    assert manager.gateway.sent == []


def test_duplicate_broker_trade_is_idempotent(tmp_path) -> None:
    manager = make_manager(tmp_path)
    now = datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai"))
    order_id = manager.submit_order(
        strategy_id="dual_ma_510300",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=1000,
        price=3.2,
        type=OrderType.LIMIT,
        latest_price=3.2,
        now=now,
    )
    snap = BrokerTradeSnapshot(
        broker_trade_id="PAPER-T-1",
        broker_order_id="PAPER-O-1",
        order_id=order_id,
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        qty=500,
        price=3.2,
        commission=5,
        dt=now,
    )
    assert manager.on_broker_trade(snap) is not None
    assert manager.on_broker_trade(snap) is None
    assert len(manager.store.list_trades()) == 1
    assert manager.store.load_account_snapshot().account.cash == 100_000
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_oms.py -q
```

Expected: FAIL because `quant.live.oms` does not exist.

- [ ] **Step 3: Implement OrderManager**

Create `src/quant/live/oms.py`. `submit_order()` must:

1. Generate local ID `O-{n}` using a store-backed counter key `next_order_seq`.
2. Build an `Order` in `SUBMITTING`.
3. Run `RiskEngine.check_order()` with gateway account, gateway positions, active store orders, current engine state, and latest price.
4. If risk rejects, save `OrderStatus.REJECTED` order, append `risk_reject` and `order` events, and return local `order_id`.
5. If risk allows, save `SUBMITTING` order before gateway send.
6. Call `gateway.send_order()` with the `OrderRequest` built from the local order fields.
7. Map returned broker ID and update order to `SUBMITTED`.
8. Append `order` event.

`on_broker_trade()` must convert `BrokerTradeSnapshot` to `Trade`, call `store.save_trade_once()`, append `trade` only when newly inserted, update the account and position snapshot from `gateway.query_account()` and `gateway.query_positions()`, and return `None` for duplicates.

`freeze_open()`, `halt()`, and `resume()` must update store engine state and append `engine_state` events. `resume()` only moves to `NORMAL` when passed a non-empty reason string.

- [ ] **Step 4: Verify OMS**

Run:

```bash
pytest tests/test_oms.py tests/test_live_store.py tests/test_risk_pipeline.py -q
ruff check src/quant/live/oms.py tests/test_oms.py
```

Expected: OMS, store, and risk tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant/live/oms.py tests/test_oms.py
git commit -m "feat: add paper order manager"
```

### Task 6: SimGateway

**Files:**
- Create: `src/quant/live/gateway/sim.py`
- Test: `tests/test_sim_gateway.py`

**Interfaces:**
- Consumes: `GatewayBase`, `Matcher`, `CostModel`, `Portfolio`, `OrderRequest`, `Bar`
- Produces: `SimGateway(initial_cash: float, account_id: str, volume_limit_pct: float = 0.05)`
- Produces: `push_bar(bar: Bar) -> None`
- Produces: broker order IDs `PAPER-O-{n}` and broker trade IDs `PAPER-T-{n}`

- [ ] **Step 1: Write SimGateway tests**

Create `tests/test_sim_gateway.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from quant.core.contract import Bar, OrderSide, OrderStatus, OrderType
from quant.live.gateway.sim import SimGateway
from quant.live.types import OrderRequest


def make_bar() -> Bar:
    return Bar(
        symbol="510300.SH",
        freq="1d",
        dt=datetime(2024, 1, 3, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        open=3.0,
        high=3.1,
        low=2.95,
        close=3.05,
        volume=10_000,
        amount=30_500,
        limit_up=3.3,
        limit_down=2.7,
    )


def make_req() -> OrderRequest:
    return OrderRequest(
        order_id="O-1",
        strategy_id="dual_ma_510300",
        account_id="paper",
        symbol="510300.SH",
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        qty=1000,
        price=3.0,
        created_at=datetime(2024, 1, 2, 9, 31, tzinfo=ZoneInfo("Asia/Shanghai")),
    )


def test_sim_gateway_matches_partial_fill_and_updates_account() -> None:
    orders = []
    trades = []
    gateway = SimGateway(initial_cash=100_000, account_id="paper", volume_limit_pct=0.05)
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=orders.append,
        on_trade=trades.append,
        on_disconnect=lambda reason: None,
    )
    broker_order_id = gateway.send_order(make_req())
    gateway.push_bar(make_bar())

    assert broker_order_id == "PAPER-O-1"
    assert orders[-1].status == OrderStatus.PARTIAL
    assert trades[0].broker_trade_id == "PAPER-T-1"
    assert trades[0].qty == 500
    assert gateway.query_account().cash < 100_000


def test_cancel_order_marks_cancelled() -> None:
    orders = []
    gateway = SimGateway(initial_cash=100_000, account_id="paper")
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=orders.append,
        on_trade=lambda trade: None,
        on_disconnect=lambda reason: None,
    )
    broker_order_id = gateway.send_order(make_req())
    gateway.cancel_order(broker_order_id)
    assert orders[-1].status == OrderStatus.CANCELLED
    assert gateway.query_orders(active_only=True) == []


def test_disconnect_injection_blocks_send_and_emits_callback() -> None:
    disconnects = []
    gateway = SimGateway(initial_cash=100_000, account_id="paper")
    gateway.set_callbacks(
        on_bar=lambda bar: None,
        on_order=lambda order: None,
        on_trade=lambda trade: None,
        on_disconnect=disconnects.append,
    )
    gateway.inject_disconnect("network drill")
    try:
        gateway.send_order(make_req())
    except ConnectionError as exc:
        assert "network drill" in str(exc)
    else:
        raise AssertionError("disconnected gateway accepted an order")
    assert disconnects == ["network drill"]
    gateway.reconnect()
    assert gateway.send_order(make_req()) == "PAPER-O-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_sim_gateway.py -q
```

Expected: FAIL because `quant.live.gateway.sim` does not exist.

- [ ] **Step 3: Implement SimGateway**

Create `src/quant/live/gateway/sim.py`:

```python
from dataclasses import replace

from quant.backtest.matcher import Matcher
from quant.core.contract import Account, Bar, Order, OrderStatus, Position, Trade
from quant.core.portfolio import Portfolio
from quant.costs import CostModel
from quant.live.gateway.base import GatewayBase
from quant.live.types import BrokerOrderSnapshot, BrokerTradeSnapshot, OrderRequest
```

Implementation rules:

- `send_order()` stores an internal `Order` with status `SUBMITTED`, assigns `PAPER-O-{n}`, calls `on_order(snapshot)`, and returns the broker ID.
- `inject_disconnect(reason)` sets `connected=False`, stores the reason, and calls `on_disconnect(reason)`.
- `reconnect()` sets `connected=True` without automatically resuming the engine; the engine must reconcile before resuming.
- `send_order()` raises `ConnectionError(reason)` when disconnected and must not consume a broker order sequence number.
- `push_bar()` updates last prices, calls `on_bar(bar)`, matches active orders for the same symbol with existing `Matcher`, applies trades to the internal `Portfolio`, emits `on_trade()` then `on_order()` for status changes.
- Partial fills remain active with status `PARTIAL`; full fills become `FILLED`.
- `cancel_order()` moves active orders to `CANCELLED` and emits an order snapshot.
- `query_account()` and `query_positions()` return the simulated portfolio marked by latest prices.
- `query_orders(active_only=True)` returns `SUBMITTED` and `PARTIAL` snapshots only.

- [ ] **Step 4: Verify SimGateway**

Run:

```bash
pytest tests/test_sim_gateway.py tests/test_matcher.py tests/test_portfolio_costs.py -q
ruff check src/quant/live/gateway/sim.py tests/test_sim_gateway.py
```

Expected: SimGateway and reused accounting/matcher tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant/live/gateway/sim.py tests/test_sim_gateway.py
git commit -m "feat: add simulated paper gateway"
```

### Task 7: Reconciliation

**Files:**
- Create: `src/quant/live/reconcile.py`
- Test: `tests/test_reconcile.py`

**Interfaces:**
- Consumes: `OmsStore`, `GatewayBase`, `EventJournal`, `PaperConfig.reconciliation`
- Produces: `ReconciliationStatus`
- Produces: `ReconciliationResult(status, cash_diff, position_diffs, message)`
- Produces: `Reconciler.run(startup: bool) -> ReconciliationResult`

- [ ] **Step 1: Write reconciliation tests**

Create `tests/test_reconcile.py`:

```python
from quant.core.contract import Account, Position
from quant.live.events import EventJournal
from quant.live.reconcile import Reconciler, ReconciliationStatus
from quant.live.store import OmsStore
from quant.live.types import EngineState


class GatewayForReconcile:
    def __init__(self, cash: float, positions=None) -> None:
        self.cash = cash
        self.positions = positions or {}

    def query_account(self):
        return Account("paper", "CNY", self.cash, 0, 0, self.cash)

    def query_positions(self):
        return self.positions

    def query_orders(self, active_only: bool = True):
        return []


def make_store(tmp_path, local_cash: float) -> OmsStore:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    account = Account("paper", "CNY", local_cash, 0, 0, local_cash)
    store.save_account_snapshot(account, {}, account_updated_at())
    return store


def account_updated_at():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime(2024, 1, 2, 15, 0, tzinfo=ZoneInfo("Asia/Shanghai"))


def test_reconcile_ok_when_cash_matches(tmp_path) -> None:
    reconciler = Reconciler(
        store=make_store(tmp_path, 100_000),
        gateway=GatewayForReconcile(100_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )
    result = reconciler.run(startup=True)
    assert result.status == ReconciliationStatus.OK


def test_reconcile_failure_moves_engine_to_halt(tmp_path) -> None:
    store = make_store(tmp_path, 100_000)
    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(90_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )
    result = reconciler.run(startup=True)
    assert result.status == ReconciliationStatus.FAILED
    assert store.get_engine_state() == EngineState.HALT


def test_reconcile_repairs_small_cash_drift(tmp_path) -> None:
    store = make_store(tmp_path, 100_000)
    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(99_999.5),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )
    result = reconciler.run(startup=False)
    assert result.status == ReconciliationStatus.REPAIRED
    assert store.load_account_snapshot().account.cash == 99_999.5


def test_startup_reconcile_fails_when_local_snapshot_is_missing(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    reconciler = Reconciler(
        store=store,
        gateway=GatewayForReconcile(100_000),
        journal=EventJournal(tmp_path / "events.jsonl"),
        cash_tolerance=0.01,
        position_qty_tolerance=0,
        auto_repair_cash_drift_below=1.0,
    )
    result = reconciler.run(startup=True)
    assert result.status == ReconciliationStatus.FAILED
    assert store.get_engine_state() == EngineState.HALT
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_reconcile.py -q
```

Expected: FAIL because `quant.live.reconcile` does not exist.

- [ ] **Step 3: Implement reconciler**

Create `src/quant/live/reconcile.py`:

```python
from dataclasses import dataclass
from enum import StrEnum

from quant.live.events import EventJournal
from quant.live.gateway.base import GatewayBase
from quant.live.store import OmsStore
from quant.live.types import EngineState


class ReconciliationStatus(StrEnum):
    OK = "OK"
    REPAIRED = "REPAIRED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ReconciliationResult:
    status: ReconciliationStatus
    cash_diff: float
    position_diffs: dict[str, float]
    message: str
```

`Reconciler.run()` compares `store.load_account_snapshot()` with gateway account and positions. It must never create a default local snapshot from gateway data during startup, because that would make "no local fact exists" look like a clean reconciliation.

Rules:

- Missing local snapshot during startup: set engine state to `HALT`, append `reconciliation` event with `FAILED`, and return failed result.
- Diff within tolerances: append `reconciliation` event with `OK`.
- Cash diff above tolerance but `abs(diff) <= auto_repair_cash_drift_below`: overwrite account and position snapshots with gateway values and append `REPAIRED`.
- Any position diff above tolerance or cash diff above repair threshold: set engine state to `HALT`, append `reconciliation` event with `FAILED`, and return failed result.

- [ ] **Step 4: Verify reconciliation**

Run:

```bash
pytest tests/test_reconcile.py tests/test_live_store.py -q
ruff check src/quant/live/reconcile.py tests/test_reconcile.py
```

Expected: reconciliation and store tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/quant/live/reconcile.py tests/test_reconcile.py
git commit -m "feat: add paper reconciliation"
```

### Task 8: Paper Engine And Strategy Context

**Files:**
- Create: `src/quant/live/context.py`
- Create: `src/quant/live/engine.py`
- Create: `src/quant/live/execution.py`
- Create: `scripts/run_paper.py`
- Test: `tests/test_paper_engine.py`

**Interfaces:**
- Consumes: `StrategyConfig`, `PaperConfig`, `DataService`, `SimGateway`, `OrderManager`, `Reconciler`
- Produces: `ExecutionRouter.set_target(strategy_id, symbol, target_qty, now) -> None`
- Produces: `ExecutionRouter.flush_pending(now, latest_prices) -> list[str]`
- Produces: `PaperContext`
- Produces: `PaperEngine.run_replay() -> PaperRunResult`
- Produces command: `python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20`

- [ ] **Step 1: Write paper engine tests**

Create `tests/test_paper_engine.py`:

```python
from pathlib import Path

from quant.core.config import load_strategy_config
from quant.live.config import load_paper_config
from quant.live.engine import PaperEngine


def test_paper_engine_replay_writes_store_and_events(tmp_path) -> None:
    strategy_config = load_strategy_config(Path("config/strategies/dual_ma_510300_paper.yaml"))
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )

    result = PaperEngine(strategy_config, paper_config).run_replay(max_bars=20)

    assert result.orders
    assert (tmp_path / "meta.db").exists()
    assert (tmp_path / "events.jsonl").exists()
    assert "trading_session" not in (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert result.final_state in {"NORMAL", "FREEZE_OPEN", "HALT"}


def test_paper_engine_refuses_non_paper_strategy(tmp_path) -> None:
    strategy_config = load_strategy_config(Path("config/strategies/dual_ma_510300.yaml"))
    paper_config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={"store_path": tmp_path / "meta.db", "events_path": tmp_path / "events.jsonl"}
    )

    try:
        PaperEngine(strategy_config, paper_config)
    except ValueError as exc:
        assert "runtime_mode must be paper" in str(exc)
    else:
        raise AssertionError("PaperEngine accepted a backtest strategy config")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_paper_engine.py -q
```

Expected: FAIL because `quant.live.engine`, `quant.live.context`, and `quant.live.execution` do not exist.

- [ ] **Step 3: Implement ExecutionRouter**

Create `src/quant/live/execution.py`:

```python
from dataclasses import dataclass
from datetime import datetime

from quant.core.contract import OrderSide, OrderType, Position
from quant.live.oms import OrderManager


@dataclass(frozen=True)
class TargetIntent:
    strategy_id: str
    symbol: str
    target_qty: float
    created_at: datetime


class ExecutionRouter:
    def __init__(self, oms: OrderManager) -> None:
        self.oms = oms
        self.pending_targets: list[TargetIntent] = []

    def set_target(
        self,
        *,
        strategy_id: str,
        symbol: str,
        target_qty: float,
        now: datetime,
    ) -> None:
        self.pending_targets.append(TargetIntent(strategy_id, symbol, target_qty, now))

    def flush_pending(
        self,
        *,
        now: datetime,
        latest_prices: dict[str, float],
        positions: dict[str, Position],
    ) -> list[str]:
        submitted: list[str] = []
        pending = self.pending_targets
        self.pending_targets = []
        for intent in pending:
            current_qty = positions.get(intent.symbol).qty if intent.symbol in positions else 0
            diff = intent.target_qty - current_qty
            if diff > 0:
                submitted.append(
                    self.oms.submit_order(
                        strategy_id=intent.strategy_id,
                        symbol=intent.symbol,
                        side=OrderSide.BUY,
                        qty=diff,
                        price=latest_prices[intent.symbol],
                        type=OrderType.LIMIT,
                        latest_price=latest_prices[intent.symbol],
                        now=now,
                    )
                )
            elif diff < 0:
                submitted.append(
                    self.oms.submit_order(
                        strategy_id=intent.strategy_id,
                        symbol=intent.symbol,
                        side=OrderSide.SELL,
                        qty=abs(diff),
                        price=latest_prices[intent.symbol],
                        type=OrderType.LIMIT,
                        latest_price=latest_prices[intent.symbol],
                        now=now,
                    )
                )
        return submitted
```

The engine calls `flush_pending()` before each replay bar is pushed into `SimGateway`, using the next bar open price and a synthetic send timestamp inside the continuous auction session, for example `09:31 Asia/Shanghai`.

- [ ] **Step 4: Implement PaperContext**

Create `src/quant/live/context.py`. Mirror the existing `BacktestContext` API:

```python
class PaperContext:
    @property
    def now(self) -> datetime:
        raise NotImplementedError

    @property
    def params(self) -> dict[str, Any]:
        raise NotImplementedError

    def history(
        self,
        symbol: str,
        n: int,
        freq: str = "1d",
        fields: Sequence[str] | None = None,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        raise NotImplementedError

    def get_position(self, symbol: str) -> Position:
        raise NotImplementedError

    def get_positions(self) -> dict[str, Position]:
        raise NotImplementedError

    def get_account(self) -> Account:
        raise NotImplementedError

    def get_open_orders(self) -> list[Order]:
        raise NotImplementedError

    def order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        price: float | None = None,
        type: OrderType = OrderType.LIMIT,
    ) -> str:
        raise NotImplementedError

    def set_target(self, symbol: str, target_qty: float) -> None:
        raise NotImplementedError

    def cancel(self, order_id: str) -> None:
        raise NotImplementedError

    def get_bar(self, symbol: str, freq: str = "1d") -> Bar | None:
        raise NotImplementedError

    def get_instrument(self, symbol: str) -> Instrument:
        raise NotImplementedError

    def schedule(self, timer_id: str, at: str) -> None:
        raise NotImplementedError

    def log(self, msg: str, level: str = "INFO") -> None:
        raise NotImplementedError

    def save_state(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def load_state(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError
```

`order()` calls `OrderManager.submit_order()` immediately with `latest_price` from the current bar or last price. If the strategy calls `order()` outside the trading session, `RiskEngine` may reject it with `trading_session`; daily strategies should prefer `set_target()`. `set_target()` records a target intent through `ExecutionRouter` so the actual broker order is created on the next tradable replay bar.

- [ ] **Step 5: Implement PaperEngine**

Create `src/quant/live/engine.py`:

```python
from dataclasses import dataclass

from quant.core.contract import Order, Trade


@dataclass(frozen=True)
class PaperRunResult:
    orders: list[Order]
    trades: list[Trade]
    final_state: str
    events_path: str
    store_path: str
```

`PaperEngine.__init__()` must:

1. Reject configs where `strategy_config.runtime_mode != "paper"`.
2. Initialize `DataService`, `OmsStore`, `EventJournal`, `RiskEngine`, `SimGateway`, `OrderManager`, and `Reconciler`.
3. If `OmsStore.is_empty()` and `load_account_snapshot()` is `None`, bootstrap the local account snapshot from `PaperConfig.initial_cash` and an empty position map, then append an `account_bootstrap` event. Do not bootstrap from gateway query results.
4. Wire SimGateway callbacks so broker order/trade snapshots update OMS, then call strategy `on_order/on_trade`.
5. Run startup reconciliation before strategy `on_start`.

`run_replay(max_bars: int | None = None)` must:

1. Load bars from `DataService` for the strategy universe, sorted by `dt, symbol`.
2. Instantiate strategy from `class_path`.
3. Use a deterministic replay clock for `EventJournal`: event `written_at` should equal the current simulated market time, not wall-clock time.
4. Call `on_init`, startup reconciliation, `on_start`.
5. For each bar: build a synthetic send time at `09:31 Asia/Shanghai` on the bar date, update latest open price, flush pending target intents through `ExecutionRouter`, push the bar into `SimGateway`, then set `now` to the bar end time and call strategy `on_bar`.
6. Call `on_stop`.
7. Return `PaperRunResult` from store state.

Keep callbacks serial in one thread for M3. Queue/thread mechanics can be introduced in M4 when a true live gateway requires it.

- [ ] **Step 6: Add run_paper CLI**

Create `scripts/run_paper.py`:

```python
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))


def main() -> None:
    from quant.core.config import load_strategy_config
    from quant.live.config import load_paper_config
    from quant.live.engine import PaperEngine

    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--max-bars", type=int, default=None)
    args = parser.parse_args()

    result = PaperEngine(
        load_strategy_config(Path(args.strategy)),
        load_paper_config(Path(args.paper)),
    ).run_replay(max_bars=args.max_bars)
    print(f"paper events: {result.events_path}")
    print(f"paper store: {result.store_path}")
    print(f"final state: {result.final_state}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Verify paper engine**

Run:

```bash
pytest tests/test_paper_engine.py tests/test_oms.py tests/test_sim_gateway.py -q
python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
ruff check src/quant/live/context.py src/quant/live/engine.py src/quant/live/execution.py scripts/run_paper.py tests/test_paper_engine.py
```

Expected: tests pass, CLI prints event/store paths, and ruff reports no issues.

- [ ] **Step 8: Commit**

```bash
git add src/quant/live/context.py src/quant/live/engine.py src/quant/live/execution.py scripts/run_paper.py tests/test_paper_engine.py
git commit -m "feat: add paper replay engine"
```

### Task 9: Alerts, Monitor, And Ops CLI

**Files:**
- Create: `src/quant/live/alerts.py`
- Create: `src/quant/live/monitor.py`
- Create: `scripts/ops.py`
- Test: `tests/test_alerts_monitor.py`
- Test: `tests/test_ops_cli.py`

**Interfaces:**
- Consumes: `EventJournal`, `OmsStore`, `OrderManager`, `EngineState`
- Produces: `AlertManager.emit(severity, key, message, payload) -> bool`
- Produces: `RuntimeMonitor.check_market_data(now, last_bar_at) -> EngineState | None`
- Produces command: `python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status`
- Produces command: `python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi halt --reason "manual drill"`
- Produces command: `python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi resume --reason "checked account and positions" --precheck account --precheck positions --precheck active_orders`

- [ ] **Step 1: Write alert and monitor tests**

Create `tests/test_alerts_monitor.py`:

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quant.live.alerts import AlertManager
from quant.live.events import EventJournal
from quant.live.monitor import RuntimeMonitor
from quant.live.store import OmsStore
from quant.live.types import AlertSeverity, EngineState


def test_alert_manager_deduplicates_by_key(tmp_path) -> None:
    manager = AlertManager(EventJournal(tmp_path / "events.jsonl"), dedupe_sec=300)
    payload = {
        "run_id": "paper-20240102",
        "strategy_id": "dual_ma_510300",
        "account_id": "paper",
        "last_event_seq": 7,
        "local_time": "2024-01-02T09:31:00+08:00",
        "market_time": "2024-01-02T09:31:00+08:00",
    }
    assert manager.emit(AlertSeverity.CRIT, "gateway_down", "gateway disconnected", payload) is True
    assert manager.emit(AlertSeverity.CRIT, "gateway_down", "gateway disconnected", payload) is False


def test_crit_alert_requires_location_fields(tmp_path) -> None:
    manager = AlertManager(EventJournal(tmp_path / "events.jsonl"), dedupe_sec=300)
    try:
        manager.emit(AlertSeverity.CRIT, "bad", "missing context", {"run_id": "paper-20240102"})
    except ValueError as exc:
        assert "CRIT alert missing fields" in str(exc)
    else:
        raise AssertionError("CRIT alert without required context was accepted")


def test_market_data_staleness_freezes_open(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    monitor = RuntimeMonitor(
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        alert_manager=AlertManager(EventJournal(tmp_path / "alerts.jsonl"), dedupe_sec=300),
        market_data_staleness_sec=60,
        run_id="paper-20240102",
        strategy_id="dual_ma_510300",
        account_id="paper",
    )
    now = datetime(2024, 1, 2, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    state = monitor.check_market_data(now=now, last_bar_at=now - timedelta(seconds=90))
    assert state == EngineState.FREEZE_OPEN
    assert store.get_engine_state() == EngineState.FREEZE_OPEN


def test_gateway_disconnect_freezes_and_gateway_reconnect_does_not_auto_resume(tmp_path) -> None:
    store = OmsStore(tmp_path / "meta.db")
    store.init_schema()
    monitor = RuntimeMonitor(
        store=store,
        journal=EventJournal(tmp_path / "events.jsonl"),
        alert_manager=AlertManager(EventJournal(tmp_path / "alerts.jsonl"), dedupe_sec=300),
        market_data_staleness_sec=60,
        run_id="paper-20240102",
        strategy_id="dual_ma_510300",
        account_id="paper",
    )

    state = monitor.on_gateway_disconnect("network drill")

    assert state == EngineState.FREEZE_OPEN
    assert store.get_engine_state() == EngineState.FREEZE_OPEN
    assert monitor.on_gateway_reconnect(reconciliation_ok=False) == EngineState.FREEZE_OPEN
    assert store.get_engine_state() == EngineState.FREEZE_OPEN
    assert monitor.on_gateway_reconnect(reconciliation_ok=True) == EngineState.NORMAL
    assert store.get_engine_state() == EngineState.NORMAL
```

- [ ] **Step 2: Write ops CLI tests**

Create `tests/test_ops_cli.py`:

```python
import subprocess
import sys

from quant.live.store import OmsStore
from quant.live.types import EngineState


def test_ops_cli_halt_resume_and_status(tmp_path) -> None:
    store_path = tmp_path / "meta.db"
    events_path = tmp_path / "events.jsonl"
    OmsStore(store_path).init_schema()

    halt = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "halt",
            "--reason",
            "manual drill",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert halt.returncode == 0, halt.stdout + halt.stderr
    assert OmsStore(store_path).get_engine_state() == EngineState.HALT

    status = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "status",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert status.returncode == 0, status.stdout + status.stderr
    assert "HALT" in status.stdout
    assert "ops_action" in events_path.read_text(encoding="utf-8")

    resume = subprocess.run(
        [
            sys.executable,
            "scripts/ops.py",
            "--store",
            str(store_path),
            "--events",
            str(events_path),
            "--operator",
            "shenxi",
            "resume",
            "--reason",
            "checked account and positions",
            "--precheck",
            "account",
            "--precheck",
            "positions",
            "--precheck",
            "active_orders",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert resume.returncode == 0, resume.stdout + resume.stderr
    assert OmsStore(store_path).get_engine_state() == EngineState.NORMAL
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
```

Expected: FAIL because alerts, monitor, and ops CLI do not exist.

- [ ] **Step 4: Implement AlertManager**

Create `src/quant/live/alerts.py`:

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from quant.live.events import EventJournal
from quant.live.types import AlertSeverity


class AlertManager:
    CRIT_REQUIRED_FIELDS = (
        "run_id",
        "strategy_id",
        "account_id",
        "last_event_seq",
        "local_time",
        "market_time",
    )

    def __init__(self, journal: EventJournal, dedupe_sec: int) -> None:
        self.journal = journal
        self.dedupe = timedelta(seconds=dedupe_sec)
        self.last_emit: dict[str, datetime] = {}
        self.timezone = ZoneInfo("Asia/Shanghai")

    def emit(
        self,
        severity: AlertSeverity,
        key: str,
        message: str,
        payload: dict[str, object],
    ) -> bool:
        if severity == AlertSeverity.CRIT:
            missing = [field for field in self.CRIT_REQUIRED_FIELDS if field not in payload]
            if missing:
                raise ValueError(f"CRIT alert missing fields: {', '.join(missing)}")
        now = datetime.now(self.timezone)
        if key in self.last_emit and now - self.last_emit[key] < self.dedupe:
            return False
        self.last_emit[key] = now
        envelope = {
            "severity": severity.value,
            "key": key,
            "message": message,
            "payload": payload,
        }
        for field in self.CRIT_REQUIRED_FIELDS:
            envelope[field] = payload.get(field)
        self.journal.append(
            "alert",
            envelope,
        )
        return True
```

- [ ] **Step 5: Implement RuntimeMonitor**

Create `src/quant/live/monitor.py`:

```python
from datetime import datetime

from quant.live.alerts import AlertManager
from quant.live.events import EventJournal
from quant.live.store import OmsStore
from quant.live.types import AlertSeverity, EngineState


class RuntimeMonitor:
    def __init__(
        self,
        *,
        store: OmsStore,
        journal: EventJournal,
        alert_manager: AlertManager,
        market_data_staleness_sec: int,
        run_id: str,
        strategy_id: str,
        account_id: str,
    ) -> None:
        self.store = store
        self.journal = journal
        self.alert_manager = alert_manager
        self.market_data_staleness_sec = market_data_staleness_sec
        self.run_id = run_id
        self.strategy_id = strategy_id
        self.account_id = account_id

    def check_market_data(
        self,
        *,
        now: datetime,
        last_bar_at: datetime | None,
    ) -> EngineState | None:
        if (
            last_bar_at is None
            or (now - last_bar_at).total_seconds() > self.market_data_staleness_sec
        ):
            self.store.set_engine_state(EngineState.FREEZE_OPEN, "market_data_stale")
            self.journal.append(
                "engine_state",
                {"state": EngineState.FREEZE_OPEN.value, "reason": "market_data_stale"},
            )
            self.alert_manager.emit(
                AlertSeverity.WARN,
                "market_data_stale",
                "market data is stale; opening orders are frozen",
                {"last_bar_at": last_bar_at.isoformat() if last_bar_at else None},
            )
            return EngineState.FREEZE_OPEN
        return None

    def on_gateway_disconnect(self, reason: str) -> EngineState:
        self.store.set_engine_state(EngineState.FREEZE_OPEN, reason)
        self.journal.append(
            "engine_state",
            {"state": EngineState.FREEZE_OPEN.value, "reason": reason},
        )
        self.alert_manager.emit(
            AlertSeverity.CRIT,
            "gateway_disconnect",
            "gateway disconnected; opening orders are frozen",
            {
                "run_id": self.run_id,
                "strategy_id": self.strategy_id,
                "account_id": self.account_id,
                "last_event_seq": self.journal.last_seq,
                "local_time": datetime.now().astimezone().isoformat(),
                "market_time": datetime.now().astimezone().isoformat(),
                "reason": reason,
            },
        )
        return EngineState.FREEZE_OPEN

    def on_gateway_reconnect(self, *, reconciliation_ok: bool) -> EngineState:
        if not reconciliation_ok:
            return self.store.get_engine_state()
        self.store.set_engine_state(EngineState.NORMAL, "gateway_reconnected_reconciliation_ok")
        self.journal.append(
            "engine_state",
            {"state": EngineState.NORMAL.value, "reason": "gateway_reconnected_reconciliation_ok"},
        )
        return EngineState.NORMAL
```

- [ ] **Step 6: Implement ops CLI**

Create `scripts/ops.py`:

```python
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from quant.live.store import OmsStore
from quant.live.events import EventJournal
from quant.live.types import EngineState


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--operator", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    for name in ("freeze-open", "halt"):
        command = sub.add_parser(name)
        command.add_argument("--reason", required=True)
    resume = sub.add_parser("resume")
    resume.add_argument("--reason", required=True)
    resume.add_argument("--precheck", action="append", required=True)
    args = parser.parse_args()

    store = OmsStore(Path(args.store))
    journal = EventJournal(Path(args.events))
    store.init_schema()
    if args.command == "status":
        print(store.get_engine_state().value)
    elif args.command == "freeze-open":
        store.set_engine_state(EngineState.FREEZE_OPEN, args.reason)
        journal.append(
            "ops_action",
            {
                "operator": args.operator,
                "action": "freeze-open",
                "reason": args.reason,
                "state": EngineState.FREEZE_OPEN.value,
            },
        )
        print("FREEZE_OPEN")
    elif args.command == "halt":
        store.set_engine_state(EngineState.HALT, args.reason)
        journal.append(
            "ops_action",
            {
                "operator": args.operator,
                "action": "halt",
                "reason": args.reason,
                "state": EngineState.HALT.value,
            },
        )
        print("HALT")
    elif args.command == "resume":
        required = {"account", "positions", "active_orders"}
        missing = sorted(required.difference(set(args.precheck)))
        if missing:
            raise SystemExit(f"resume missing precheck: {', '.join(missing)}")
        store.set_engine_state(EngineState.NORMAL, args.reason)
        journal.append(
            "ops_action",
            {
                "operator": args.operator,
                "action": "resume",
                "reason": args.reason,
                "precheck": args.precheck,
                "state": EngineState.NORMAL.value,
            },
        )
        print("NORMAL")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Verify alerts, monitor, and ops**

Run:

```bash
pytest tests/test_alerts_monitor.py tests/test_ops_cli.py -q
ruff check src/quant/live/alerts.py src/quant/live/monitor.py scripts/ops.py tests/test_alerts_monitor.py tests/test_ops_cli.py
```

Expected: tests pass and ruff reports no issues.

- [ ] **Step 8: Commit**

```bash
git add src/quant/live/alerts.py src/quant/live/monitor.py scripts/ops.py tests/test_alerts_monitor.py tests/test_ops_cli.py
git commit -m "feat: add paper alerts and ops controls"
```

### Task 10: Paper Golden Regression And Runbook

**Files:**
- Create: `tests/golden_paper/events.jsonl`
- Create: `tests/golden_paper/orders.csv`
- Create: `tests/golden_paper/trades.csv`
- Create: `tests/test_paper_golden.py`
- Create: `docs/runbooks/paper_daily_runbook.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `PaperEngine.run_replay(max_bars=20)`
- Produces: golden paper regression gate
- Produces: daily paper operation checklist

- [ ] **Step 1: Add golden generation command**

Run once after Task 8 and Task 9:

```bash
rm -rf /tmp/paper_golden runtime/paper
python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
mkdir -p tests/golden_paper
sqlite3 runtime/paper/meta.db ".headers on" ".mode csv" "select * from orders order by order_id;" > tests/golden_paper/orders.csv
sqlite3 runtime/paper/meta.db ".headers on" ".mode csv" "select * from trades order by trade_id;" > tests/golden_paper/trades.csv
cp runtime/paper/events.jsonl tests/golden_paper/events.jsonl
```

Expected: three golden files exist under `tests/golden_paper/`, and repeated generation produces byte-identical `events.jsonl` because replay uses the deterministic journal clock.

- [ ] **Step 2: Add golden comparison test**

Create `tests/test_paper_golden.py`:

```python
import filecmp
import sqlite3
from pathlib import Path

from quant.core.config import load_strategy_config
from quant.live.config import load_paper_config
from quant.live.engine import PaperEngine


def dump_table(db_path: Path, table: str, output: Path) -> None:
    with sqlite3.connect(db_path) as conn, output.open("w", encoding="utf-8") as file:
        cursor = conn.execute(f"select * from {table} order by 1")
        file.write(",".join([column[0] for column in cursor.description]) + "\n")
        for row in cursor.fetchall():
            file.write(",".join("" if value is None else str(value) for value in row) + "\n")


def test_paper_replay_matches_golden(tmp_path) -> None:
    config = load_paper_config(Path("config/paper.yaml")).model_copy(
        update={
            "store_path": tmp_path / "meta.db",
            "events_path": tmp_path / "events.jsonl",
            "run_root": tmp_path / "runs",
        }
    )
    PaperEngine(
        load_strategy_config(Path("config/strategies/dual_ma_510300_paper.yaml")),
        config,
    ).run_replay(max_bars=20)

    dump_table(tmp_path / "meta.db", "orders", tmp_path / "orders.csv")
    dump_table(tmp_path / "meta.db", "trades", tmp_path / "trades.csv")
    assert filecmp.cmp(
        tmp_path / "orders.csv",
        Path("tests/golden_paper/orders.csv"),
        shallow=False,
    )
    assert filecmp.cmp(
        tmp_path / "trades.csv",
        Path("tests/golden_paper/trades.csv"),
        shallow=False,
    )
    assert filecmp.cmp(
        tmp_path / "events.jsonl",
        Path("tests/golden_paper/events.jsonl"),
        shallow=False,
    )
```

If the `sqlite3` CLI is not installed locally, generate the initial CSV files using the same `dump_table()` helper from a temporary script, then commit the resulting golden files.

- [ ] **Step 3: Add paper runbook**

Create `docs/runbooks/paper_daily_runbook.md`:

```markdown
# Paper Daily Runbook

## 08:45 Pre-Open

- Pull latest code and confirm `pytest -q`, `ruff check .`, and `lint-imports` pass.
- Confirm `config/strategies/*_paper.yaml` uses `runtime_mode: paper`.
- Remove stale local runtime state only for deliberate dry runs; never delete state during a continuity test.
- Start Paper replay with `python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml`.
- Check `python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status`; expected `NORMAL`.

## During Session

- Any `CRIT` alert requires checking `runtime/paper/events.jsonl` and `runtime/paper/meta.db`.
- Do not resume from `HALT` until account, positions, active orders, and last event sequence have been inspected.
- Use `freeze-open` for manual caution and `halt` for unknown state.

## 15:05 Close

- Confirm no active orders remain unless they are intentionally carried by the simulator.
- Run reconciliation from the engine or next startup.
- Archive `runtime/paper/meta.db`, `runtime/paper/events.jsonl`, and the strategy config snapshot.

## Acceptance Log

- Paper must run for at least 10 trading days before M4 planning.
- Required daily notes: date, strategy id, final state, orders, trades, rejects, reconciliation result, alerts.
```

- [ ] **Step 4: Update project README**

Add to `README.md`:

````markdown
## Current Phase

M0-M2 implements a credible A股 ETF daily-bar backtest slice. M3 adds Paper trading infrastructure only; real broker gateways and real-money trading remain deliberately excluded.

## Paper Mode

After M3 is implemented:

```bash
python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status
```
````

- [ ] **Step 5: Verify full M3 gate**

Run:

```bash
pytest -q
ruff check .
lint-imports
python scripts/run_paper.py --strategy config/strategies/dual_ma_510300_paper.yaml --paper config/paper.yaml --max-bars 20
python scripts/ops.py --store runtime/paper/meta.db --events runtime/paper/events.jsonl --operator shenxi status
```

Expected:

```text
All tests pass.
All checks passed!
Contracts: 1 kept, 0 broken.
run_paper prints paper events/store paths and final state.
ops status prints NORMAL, FREEZE_OPEN, or HALT.
```

- [ ] **Step 6: Commit**

```bash
git add tests/golden_paper tests/test_paper_golden.py docs/runbooks/paper_daily_runbook.md README.md
git commit -m "test: add paper golden regression gate"
```

### Task 11: M3b Paper Observation Gate

**Files:**
- Create: `docs/runbooks/paper_observation_checklist.md`
- Create: `tests/test_m3_paper_gate_docs.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: M3a Paper runtime from Tasks 1-10
- Produces: explicit M3b acceptance checklist for 10 trading days, daily reconciliation, disconnect drill, and CRIT alert delivery

- [ ] **Step 1: Write acceptance-doc test**

Create `tests/test_m3_paper_gate_docs.py`:

```python
from pathlib import Path


def test_m3b_observation_checklist_captures_paper_gate_requirements() -> None:
    text = Path("docs/runbooks/paper_observation_checklist.md").read_text(encoding="utf-8")
    required = [
        "10 trading days",
        "daily reconciliation zero difference",
        "disconnect drill",
        "CRIT alert delivery",
        "no unresolved manual intervention",
        "M4 is blocked until this checklist is complete",
    ]
    for phrase in required:
        assert phrase in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_m3_paper_gate_docs.py -q
```

Expected: FAIL because `docs/runbooks/paper_observation_checklist.md` does not exist.

- [ ] **Step 3: Add M3b observation checklist**

Create `docs/runbooks/paper_observation_checklist.md`:

```markdown
# M3b Paper Observation Checklist

M3a means the local deterministic Paper replay infrastructure is implemented and tested. M3b is the真钱前 Paper gate from the roadmap. M4 is blocked until this checklist is complete.

## Required Window

- Run the same strategy config in `runtime_mode: paper` for at least 10 trading days.
- Record one row per trading day: date, strategy id, account id, final engine state, order count, trade count, reject count, reconciliation status, alerts, and operator notes.
- Any day with an unresolved engine crash, unresolved reconciliation difference, or missing event journal does not count toward the 10 trading days.

## Daily Acceptance

- Pre-open startup reconciliation completes before strategy orders are accepted.
- Close reconciliation reports daily reconciliation zero difference.
- No unresolved manual intervention remains at end of day.
- `runtime/paper/events.jsonl` and `runtime/paper/meta.db` are archived.

## Required Drill

- Perform at least one disconnect drill during the observation window.
- Expected behavior: gateway disconnect moves state to `FREEZE_OPEN`, emits a CRIT alert, blocks opening orders, reconnects, runs reconciliation, and resumes only after reconciliation passes.

## Alert Acceptance

- Perform one CRIT alert delivery drill.
- The delivered alert must include `run_id`, `strategy_id`, `account_id`, `last_event_seq`, `local_time`, and `market_time`.
- Confirm the alert is visible on the configured phone-side channel.

## Final M3b Sign-Off

- 10 trading days completed.
- daily reconciliation zero difference on every counted day.
- disconnect drill completed.
- CRIT alert delivery confirmed.
- no unresolved manual intervention remains.
- M4 is blocked until this checklist is complete.
```

- [ ] **Step 4: Update README with M3a/M3b status language**

Add to `README.md`:

```markdown
## Phase Language

M3a is the local deterministic Paper replay implementation. M3b is the真钱前 Paper observation gate: 10 trading days, daily reconciliation zero difference, one disconnect drill, and CRIT alert delivery confirmed. M4 remains blocked until M3b is signed off.
```

- [ ] **Step 5: Verify M3b checklist**

Run:

```bash
pytest tests/test_m3_paper_gate_docs.py -q
ruff check tests/test_m3_paper_gate_docs.py
```

Expected: checklist test passes and ruff reports no issues.

- [ ] **Step 6: Commit**

```bash
git add docs/runbooks/paper_observation_checklist.md tests/test_m3_paper_gate_docs.py README.md
git commit -m "docs: add m3b paper observation gate"
```

## Definition Of Done For M3a Local Replay

- [ ] `pytest -q` passes.
- [ ] `ruff check .` passes.
- [ ] `lint-imports` reports all contracts kept.
- [ ] `runtime_mode: paper` runs the same `DualMA` strategy without strategy-code changes.
- [ ] Strategy code still imports only `quant.core.contract`.
- [ ] Paper order path is `Context -> RiskEngine -> OrderManager -> SimGateway`; no direct gateway access from strategies.
- [ ] Daily-bar `set_target()` after bar close becomes a next-tradable-bar order intent, not an immediate after-hours broker order.
- [ ] Every order is written to SQLite before gateway send.
- [ ] Risk rejects create `OrderStatus.REJECTED` orders with structured `reject_reason`.
- [ ] Duplicate broker trade snapshots are idempotent.
- [ ] Startup reconciliation runs before strategy orders are accepted.
- [ ] Reconciliation failure sets engine state to `HALT` and appends a CRIT-ready event.
- [ ] Market data staleness can move the engine to `FREEZE_OPEN`.
- [ ] `scripts/ops.py` can show status, freeze opening orders, halt, and manually resume with operator, reason, precheck, and JSONL audit.
- [ ] Paper golden regression files protect orders, trades, and event sequence.
- [ ] Paper daily runbook exists and includes pre-open, during-session, close, and 10-trading-day acceptance notes.
- [ ] No QMT, real broker adapter, true live mode, minute/tick data, web UI, multi-account production path, or mobile-command trading appears in the implementation.

## Definition Of Done For M3b Paper Gate

- [ ] `docs/runbooks/paper_observation_checklist.md` exists and is followed.
- [ ] DualMA runs in `runtime_mode: paper` for at least 10 trading days.
- [ ] Every counted day has startup and close reconciliation with zero unresolved difference.
- [ ] At least one disconnect drill moves the engine to `FREEZE_OPEN`, emits CRIT, blocks opening orders, reconnects, reconciles, and resumes only after reconciliation passes.
- [ ] At least one CRIT alert delivery drill reaches the phone-side channel.
- [ ] Every CRIT alert includes `run_id`, `strategy_id`, `account_id`, `last_event_seq`, `local_time`, and `market_time`.
- [ ] No unresolved manual intervention, missing event journal, or missing SQLite state remains in the observation window.
- [ ] M4 remains blocked until every M3a and M3b item is checked.

## Explicit Next Phase

After M3a is implemented and M3b has run for at least 10 trading days with zero unresolved reconciliation differences, the next document should be `13_m4_qmt_live_开发计划.md`. It should cover QmtGateway, Windows deployment, NSSM process supervision, broker-side account reconciliation, real-money risk limits, backup/restore drills, and small-capital live acceptance. Do not start M4 until both M3a and M3b Definitions Of Done are met.
