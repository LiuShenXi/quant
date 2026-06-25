from __future__ import annotations

from quant.live.config import PaperConfig
from quant.live.gateway.base import GatewayBase
from quant.live.gateway.sim import SimGateway
from quant.live.store import OmsStore


def build_sim_gateway(paper_config: PaperConfig, store: OmsStore) -> GatewayBase:
    snapshot = store.load_account_snapshot()
    if snapshot is None:
        return SimGateway(
            initial_cash=paper_config.initial_cash,
            account_id=paper_config.account_id,
        )
    return SimGateway.from_snapshot(
        account=snapshot.account,
        positions=snapshot.positions,
        active_orders=store.list_orders(active_only=True),
        trades=store.list_trades(),
        account_id=paper_config.account_id,
        initial_cash=paper_config.initial_cash,
    )
