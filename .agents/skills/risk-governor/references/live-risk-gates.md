# Live Risk Gates

## Capital and Exposure

- Initial capital is explicit.
- Per-order notional cap is explicit.
- Per-symbol exposure cap is explicit.
- Strategy-level gross and net exposure caps are explicit.
- Account-level total exposure cap is explicit.

## Loss Controls

- Daily loss limit is explicit.
- Weekly or rolling drawdown limit is explicit when live money is involved.
- Max strategy drawdown threshold is explicit.
- Loss-limit breach freezes new orders.

## Operational Controls

- Risk checks are outside strategy code.
- Strategies cannot call broker gateways directly.
- Startup reconciliation must pass before trading.
- All order, fill, rejection, and state-change events are persisted.
- Kill switch can be triggered independently of strategy logic.

## Human Authority

- Human approval is required before first live-money use.
- Human approval is required after any CRIT incident.
- Human approval is required after changing risk limits.
- The official broker client is the source of truth during incidents.

