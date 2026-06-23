# 08 · 项目骨架与工程规范

## 1. 目录结构(monorepo)

```
quant/
├── core/                    # 契约与引擎接口(系统的"接口主权"区)
│   ├── contract/            #   types.py / strategy.py / context.py ← 03号文档
│   ├── engine.py            #   引擎基类:事件循环骨架,回测/实盘共用
│   └── portfolio.py         #   持仓与现金核算(两个引擎共用同一套账)
├── data/                    # 02号文档
│   ├── providers/           #   akshare / tushare / xtdata 适配器
│   ├── storage.py           #   parquet + duckdb + sqlite 封装
│   ├── service.py           #   DataService(唯一对上入口)
│   └── pipeline.py          #   更新管道 + 质检
├── backtest/                # 04号文档:matcher.py / costs.py / analyzer.py / engine.py
├── live/                    # 05号文档
│   ├── oms.py
│   ├── execution.py         #   立即限价 / 再平衡器 / TWAP
│   ├── reconcile.py
│   └── gateway/             #   base.py / qmt.py / sim.py(paper)/ ctp.py / ccxt_gw.py
├── risk/                    # 06号文档:checks.py / kill_switch.py / monitor.py
├── ops/                     # 07号文档:alerts.py / report.py / jobs/
├── strategies/              # ★ 你的东西(插件目录)
├── research/                # notebooks、vectorbt 实验(不进生产路径)
├── config/
│   ├── base.yaml            # 全局:路径、市场、日志级别
│   ├── costs/  risk/  strategies/
│   └── .env                 # 密钥(gitignore)
├── scripts/                 # run_backtest.py / run_live.py / update_data.py / ops.py / lint_strategy.py
├── tests/
└── pyproject.toml
```

## 2. 配置体系

三层合并:`base.yaml`(全局)→ 市场/成本/风控配置 → 策略实例配置。启动时合并后交给 pydantic 模型整体校验;实盘进程把**合并后的最终配置快照**写入当日事件流水(可追溯当天到底是什么配置在跑)。

## 3. 模块边界规则(用 import-linter 或 CI 脚本强制)

1. `strategies/` 只允许 import `core.contract` 与标准库/numpy/pandas——这是契约的物理保障。
2. `core/` 不允许 import `data/ backtest/ live/ risk/`(依赖只能朝核心层流入)。
3. 任何模块禁止 import `research/`;`research/` 随便 import 谁。
4. 券商 SDK(xtquant 等)只允许出现在 `live/gateway/` 内。

## 4. 依赖管理

- 用 `uv`(或 pip-tools)锁定全部依赖版本,锁文件进 Git;升级依赖是显式动作并要求测试全绿。
- xtquant 随 QMT 客户端发布,在实盘机上按其版本固定,不进通用锁文件,在部署文档中单独记录版本号。

## 5. 测试策略

| 层级 | 对象 | 要点 |
|---|---|---|
| 单元 | 成本计算、撮合规则(每条规则一组用例:涨跌停/T+1/整手/量能上限)、风控每条检查、复权计算 | 数字正确性的主防线 |
| 回归 | 黄金回归测试(见 04 第 8 节) | 核心层任何改动后必跑 |
| 集成 | 小数据集端到端回测;SimGateway 全链路(下单→部分成交→撤单→对账) | — |
| 验收 | 03 号文档第 9 节策略接入清单 + 09 号实盘准入清单 | 人工执行,有 checklist |

习惯:每次实盘出一个 bug,先写一个能复现它的测试,再修。

## 6. Git 与发布

- 单仓库,但平台层与策略层分目录、分 tag:平台 `platform-v1.2.0`,策略各自 `s/dual_ma-v1.0.0`。
- 平台层遵守 03 号文档的兼容性承诺;CHANGELOG 注明每次对契约是否有影响。
- main 分支保持随时可部署;实盘机只部署打过 tag 的版本。
