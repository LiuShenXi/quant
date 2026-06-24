from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from quant.live.events import EventJournal  # noqa: E402
from quant.live.monitor import resolve_engine_state_transition  # noqa: E402
from quant.live.store import OmsStore  # noqa: E402
from quant.live.types import EngineState  # noqa: E402


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
        return

    if args.command == "freeze-open":
        effective_state = _set_state_and_audit(
            store,
            journal,
            args.operator,
            "freeze-open",
            args.reason,
            EngineState.FREEZE_OPEN,
        )
        print(effective_state.value)
        return

    if args.command == "halt":
        effective_state = _set_state_and_audit(
            store,
            journal,
            args.operator,
            "halt",
            args.reason,
            EngineState.HALT,
        )
        print(effective_state.value)
        return

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
    print(EngineState.NORMAL.value)


def _set_state_and_audit(
    store: OmsStore,
    journal: EventJournal,
    operator: str,
    action: str,
    reason: str,
    state: EngineState,
) -> EngineState:
    current = store.get_engine_state()
    effective_state = resolve_engine_state_transition(current, state)
    if effective_state != current:
        store.set_engine_state(effective_state, reason)
    journal.append(
        "ops_action",
        {
            "operator": operator,
            "action": action if effective_state == state else "preserve_halt",
            "reason": reason,
            "state": effective_state.value,
            "requested_state": state.value,
        },
    )
    return effective_state


if __name__ == "__main__":
    main()
