# 02 · 数据层设计

数据层的目标:对上层提供一个**唯一、干净、可追溯**的数据入口 `DataService`,策略和回测永远不直接碰文件或第三方库。

## 0. 时间与口径约定(v1.1 补充)

数据层先定语义,再写代码:

1. A股默认时区为 `Asia/Shanghai`;所有 `datetime` 在进入平台边界前必须带时区,存储层可统一转为 UTC,对策略展示时再转回市场时区。
2. `Bar.dt` 表示**bar 结束时间**。日线为当日收盘时点,1 分钟线为该分钟结束时点。
3. `history(symbol, end=ctx.now, n=...)` 返回的最后一根 bar 必须满足 `bar.dt <= end`,物理上不能包含未来 bar。
4. 分钟线缺失要区分三类:正常无成交、停牌/临停、数据源缺失。第三类必须进入 `quality_log`,不能默默补 0。
5. 价格字段默认存交易所/数据源原始价;复权只在查询时动态计算,并在结果元数据中记录 `adjust` 与基准日期。

## 1. 数据源抽象(Provider)

```python
# data/providers/base.py
class DataProvider(ABC):
    @abstractmethod
    def fetch_instruments(self) -> pd.DataFrame: ...
    @abstractmethod
    def fetch_calendar(self, start: date, end: date) -> pd.DataFrame: ...
    @abstractmethod
    def fetch_bars(self, symbol: str, freq: str,
                   start: date, end: date) -> pd.DataFrame: ...
    @abstractmethod
    def fetch_adjust_factors(self, symbol: str) -> pd.DataFrame: ...
```

实现:`AkshareProvider`、`TushareProvider`、`XtdataProvider`(QMT 本地行情)。建议接入**两个源**,更新时对随机抽样的标的做交叉比对(收盘价误差超阈值即告警)——单数据源的静默错误是最难发现的坑。

## 2. 存储布局

```
data_root/
  parquet/
    bars_1d/year=2024/part-*.parquet      # 按年分区
    bars_1m/symbol=600519.SH/year=2024/   # 分钟线按标的+年分区
  meta.db                                  # SQLite:下方各元数据表
```

DuckDB 直接对 Parquet 建视图查询,无服务、零运维。日线全市场十几年数据也就几个 GB。

## 3. 核心表结构

**instruments(合约表,SQLite)**

| 字段 | 说明 |
|---|---|
| symbol | 统一格式 `600519.SH` / `rb2501.SHF` / `BTC-USDT.BINANCE` |
| name / type | 名称;stock / etf / future / crypto |
| list_date / delist_date | **退市标的必须保留**,否则回测有幸存者偏差 |
| lot_size / qty_step | 最小下单量与递增步长(如主板 100/100,科创板 200/1) |
| tick_size | 最小价格变动 |
| t_plus | 0 或 1,可卖出延迟(把交易规则做成数据,不硬编码) |
| status | active / suspended / delisted |

**trade_calendar**:`(exchange, date, is_open)`。所有"下一交易日"逻辑只查此表。

**bars_1d(Parquet)**

| 字段 | 说明 |
|---|---|
| symbol, dt | 主键 |
| open/high/low/close/volume/amount | 一律存**未复权原始价** |
| pre_close, limit_up, limit_down | 直接从数据源存涨跌停价,回测撮合要用(不同板块涨跌幅不同,存数据比写规则可靠) |
| suspended | 是否停牌 |
| data_status | ok / suspended / no_trade / missing。`missing` 不允许进入生产回测 |
| source / updated_at | 数据来源与写入时间,便于追溯 |

**adjust_factors**:`(symbol, ex_date, factor)` 累积复权因子。

**universe_membership**:`(index_code, symbol, in_date, out_date)`。指数成分股的**时点正确**记录——回测某天的沪深300策略,用的必须是当天的成分,不是今天的。

## 4. 复权处理(重要)

原则:**存原始价 + 因子,使用时动态复权**,不落盘复权价。

- 落盘前复权价的坑:每次分红除权,全历史价格都会变,你存的数据会"过期",回测结果随更新日期漂移。
- 动态前复权:`qfq_price = raw_price × factor / factor_as_of(end_date)`,以请求窗口的终点为基准,时点正确且可复现。`end_date` 必须来自调用方的 `end` 或回测当前时刻,不能用"最新交易日"。
- `DataService.history(..., adjust="qfq")` 内部完成,策略无感知。

财务/基本面数据(若使用):必须按**公告日**而非报告期对齐(point-in-time),否则就是用未来数据。

## 5. 统一数据入口

```python
# data/service.py —— 上层唯一入口
class DataService:
    def history(self, symbol: str, end: datetime, n: int,
                freq: str = "1d", adjust: str = "qfq",
                fields: list[str] | None = None) -> pd.DataFrame: ...
    def latest_bar_time(self, symbol: str, freq: str = "1d") -> datetime | None: ...
    def get_instrument(self, symbol: str) -> Instrument: ...
    def trading_days(self, start: date, end: date) -> list[date]: ...
    def next_trading_day(self, d: date) -> date: ...
    def universe(self, index_code: str, on: date) -> list[str]: ...
```

回测引擎和实盘 Context 的 `ctx.history()` 都委托给它——保证回测和实盘看到完全一致的历史数据。`DataService` 是读接口,不负责在策略回调内临时拉第三方网络数据;生产路径的数据必须先入库、质检、再查询。

## 6. 更新管道(每日收盘后)

```
for 每个待更新交易日:
    fetch(增量) → validate(质检) → upsert(幂等写入) → 记录 quality_log
全部完成 → 推送数据日报;任一环节失败 → 告警,且标记当日数据"不可用"
```

要求**幂等**:同一天重复跑结果一致(写入用 upsert 而非 append),这样失败重跑无心理负担。

## 7. 质量检查清单(validate 阶段)

| 检查 | 规则 |
|---|---|
| 日历完整性 | 交易日历上的开市日,每个 active 标的必须有 bar 或 suspended 标记 |
| OHLC 合法 | low ≤ open,close ≤ high;价格 > 0 |
| 跳变检测 | 相邻收盘价变动超阈值(如 ±21%)且当日无复权因子 → 告警人工确认 |
| 量额一致 | volume=0 但未标停牌 → 告警 |
| 主键唯一 | (symbol, dt) 无重复 |
| 因子链完整 | 复权因子日期连续、单调 |
| 双源比对 | 抽样 N 只,两数据源收盘价相对误差 < 0.1% |

质检结果写入 `quality_log` 表。**回测前置检查**:若回测区间内存在未通过质检的日期,引擎默认拒绝运行(可显式 override)。
