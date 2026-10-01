# opencode-finance-trading

This repository now contains a modular Python-based trading foundation designed for:
- real market data ingestion
- candlestick analysis
- market structure detection
- entry validation
- dynamic stop-loss management
- paper trading simulation
- backtesting with the same logic used in paper/live flows
- Binance integration as a controlled, opt-in wrapper
- live trading safety gates that remain disabled by default

## Architecture

The package is organized as follows:

- `src/trading/analysis/` – candlestick analysis and structure detection
- `src/trading/execution/` – risk checks, order management, dynamic stops, emergency stop
- `src/trading/exchange/` – Binance client wrapper
- `src/trading/strategy/` – strategy evaluation layer
- `src/trading/portfolio/` – portfolio state and snapshots
- `src/trading/paper_trading.py` – simulator for virtual trades
- `src/trading/backtesting.py` – backtest runner using the same strategy logic
- `src/trading/dashboard.py` – dashboard snapshot API
- `src/trading/trading_agent.py` – orchestrator that enforces safety controls
- `src/trading/position_monitor.py` – position state, stop protection, and invalidation decisions
- `src/trading/browser/` – Playwright browser bridge exposed to OpenCode through MCP

## Operating modes

- `ANALYSIS`: read-only analysis only
- `PAPER`: real market data, virtual money
- `TESTNET`: exchange simulation with test environment only
- `LIVE`: real orders, disabled unless manual activation is enabled

The default mode is `PAPER`.

## Security rules

- No API secrets are hard-coded.
- Secrets live in `.env` and are documented in `.env.example`.
- The repository is set to ignore `.env` files.
- Live mode must be enabled explicitly using `LIVE_ENABLED=true`.
- Withdrawals are never requested or granted by the trading client.

## Binance integration

This project follows the official Binance public REST API contract for endpoints such as:
- `/api/v3/klines`
- `/api/v3/ticker/price`
- `/api/v3/account`
- `/api/v3/order`
- `/api/v3/openOrders`

The environment variables used are:
- `BINANCE_API_KEY`
- `BINANCE_API_SECRET`
- `BINANCE_TESTNET=true`

The wrapper is intentionally conservative and does not enable real trading unless the user explicitly opts in.

## OpenCode browser integration

OpenCode is configured in [opencode.json](opencode.json) with a local MCP server named `binance-browser`. It uses a persistent Playwright Chromium profile at `.browser-profile/`, which is ignored by git.

Start OpenCode from the repository root:

```bash
opencode
```

The browser tools can start Chromium, navigate only to Binance domains, inspect the current page, click reviewed selectors, and fill reviewed fields. The user must log in manually in the browser session. Passwords, API secrets, and cookies are not sent to the agent or stored in source files.

In a container without `DISPLAY`, the bridge falls back to headless mode and reports `display_fallback=true`. Headless mode is suitable for public market analysis, but authenticated account actions require a graphical browser environment or an explicitly attached browser session.

To attach a visible Chromium session, start Chromium with remote debugging enabled and set `BROWSER_CDP_URL=http://127.0.0.1:9222` in the MCP environment. Log in to Binance in that browser yourself, then ask OpenCode to run `browser_start`; the MCP will attach to the existing session instead of creating a new one. Never expose the debugging port beyond the local machine.

Order submission has a separate confirmation barrier. The agent must first request an order confirmation containing the symbol, side, quantity, entry, stop, and target. Only an exact explicit confirmation can unlock the following browser action. This protects against accidental clicks; it does not guarantee profitability or eliminate exchange/UI risks.

The browser MCP currently exposes:

- `browser_start`
- `browser_navigate`
- `browser_snapshot`
- `browser_wait`
- `browser_screenshot`
- `browser_click`
- `browser_fill`
- `request_order_confirmation`
- `confirm_order_action`

This integration controls the web interface and is separate from the REST client. It does not use a WebSocket.

## Quick start

1. Create a local environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your preferred settings.
3. Run the tests:
   ```bash
   pytest -q
   ```
4. Build the project:
   ```bash
   python -m compileall src
   ```

## Real-time analysis flow

The agent can consume Binance klines and produce an analysis-only trade plan:

```python
from trading.exchange.binance import BinanceClient
from trading.trading_agent import TradingAgent

agent = TradingAgent()
client = BinanceClient(testnet=True)
plan = agent.analyze_binance_snapshot(client, symbol="BTCUSDT", timeframe="15m")
print(plan)
```

This method reads market data and calculates structure, entry, stop, target, and risk. It does not submit an order. Execution remains a separate explicit call and is subject to the configured mode and safety gates.

Paper trading supports stop updates, break-even, partial exits, commissions, slippage, realized PnL, and drawdown tracking.

## Financial analysis context

The strategy now enriches each analysis cycle with:

- ATR and true range for volatility-aware stops
- RSI and volume ratio helpers
- market regime: bullish, bearish, range, or high-volatility variants
- optional higher-timeframe candles
- rejection when primary and higher-timeframe trends disagree
- quality score based on volume, regime, and timeframe alignment
- risk/benefit targets derived from the stop distance

These values are evidence for a decision, not a promise of profit. A weak or contradictory context should produce no trade plan.

## Manual live activation

Live trading is blocked until the operator sets all of the following:
- `MODE=LIVE`
- `LIVE_ENABLED=true`
- `LIVE_MANUAL_APPROVAL=true`

This is not automatic and must be done explicitly by the operator.

## Notes on MCP and OpenCode

The workspace did not have the OpenCode CLI installed during inspection (`opencode: command not found`). Because of that, there was no valid MCP server configuration to inspect or preserve. The project is therefore implemented as a standalone Python trading foundation, and any OpenCode MCP integration can be added later when the CLI is installed.

## Known limitations

- This project is not a guarantee of profits.
- It contains no martingale logic.
- It separates analysis and execution by design.
- The simulated paper engine is intentionally simple and safe for local testing.
- Binance live operations require valid credentials and proper permissions in the exchange account, and remain disabled unless explicitly enabled.
