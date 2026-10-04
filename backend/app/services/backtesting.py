"""Long-only test-set backtest using rules mined from an earlier train period."""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException

from app.schemas.analytics import BacktestRequest
from app.services.analytics import chronological_split, market_frame
from app.services.patterns import mine_rules


def run_backtest(params: BacktestRequest) -> dict[str, Any]:
    """Trade one selected mined rule on the held-out period with next-open entries."""
    mined = mine_rules(params.min_support, params.min_confidence, params.train_ratio, params.algorithm)
    up_rules = [rule for rule in mined["rules"] if rule["consequent"] == "NEXT_DAY_UP"]
    if params.rule_id:
        selected = next((rule for rule in up_rules if rule["rule_id"] == params.rule_id), None)
        if selected is None:
            raise HTTPException(status_code=422, detail="Selected rule is not an available NEXT_DAY_UP rule from the training set.")
    else:
        actionable = [rule for rule in up_rules if rule["actionable"]]
        choices = actionable or up_rules
        if not choices:
            raise HTTPException(status_code=422, detail="No qualifying NEXT_DAY_UP rule was mined. Lower min_support or min_confidence.")
        selected = choices[0]

    frame = market_frame()
    _, valid = chronological_split(frame, params.train_ratio)
    split = int(len(valid) * params.train_ratio)
    test = valid.iloc[split:]
    if test.empty:
        raise HTTPException(status_code=422, detail="The requested split leaves no test observations.")
    test_start = int(test.index[0])
    last_signal_index = int(test.index[-1])
    last_index = len(frame) - 1
    columns = selected["antecedent"]

    capital = float(params.initial_capital)
    equity = capital
    friction = (params.transaction_cost_pct + params.slippage_pct) / 100
    position_fraction = params.position_size_pct / 100
    stop_fraction = params.stop_loss_pct / 100 if params.stop_loss_pct else None
    target_fraction = params.take_profit_pct / 100 if params.take_profit_pct else None
    start_price = float(frame.iloc[test_start]["Close"])
    if start_price <= 0:
        raise HTTPException(status_code=422, detail="Invalid test-set starting close price.")

    position: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []
    daily: list[dict[str, Any]] = []
    # Buy & Hold pays the same one-way cost/slippage on entry and liquidation.
    baseline_start = capital * (1 - friction)

    def finish_position(exit_index: int, exit_price: float, reason: str) -> None:
        nonlocal equity, position
        assert position is not None
        mark_to_market = position["invested_equity"] * exit_price / position["entry_price"]
        equity = position["cash_reserve"] + mark_to_market * (1 - friction)
        pnl = equity - position["equity_before"]
        trades.append({
            "signal_date": position["signal_date"],
            "entry_date": position["entry_date"],
            "exit_date": frame.iloc[exit_index]["Date"].date().isoformat(),
            "entry_price": position["entry_price"],
            "exit_price": float(exit_price),
            "net_return_pct": pnl / position["equity_before"] * 100 if position["equity_before"] else 0.0,
            "net_pnl": pnl,
            "exit_reason": reason,
        })
        position = None

    for index in range(test_start, last_index + 1):
        row = frame.iloc[index]
        # A signal is known at the previous close; the order enters at today's open.
        if position is None and index > test_start and index - 1 <= last_signal_index:
            signal_row = frame.iloc[index - 1]
            signal_is_test = index - 1 >= test_start
            if signal_is_test and all(bool(signal_row[column]) for column in columns):
                entry_price = float(row["Open"])
                if entry_price > 0:
                    position = {
                        "signal_date": signal_row["Date"].date().isoformat(),
                        "entry_date": row["Date"].date().isoformat(),
                        "entry_index": index,
                        "entry_price": entry_price,
                        "equity_before": equity,
                        "cash_reserve": equity * (1 - position_fraction),
                        "invested_equity": equity * position_fraction * (1 - friction),
                        "stop_price": entry_price * (1 - stop_fraction) if stop_fraction is not None else None,
                        "target_price": entry_price * (1 + target_fraction) if target_fraction is not None else None,
                    }

        if position is not None:
            open_price, low, high, close = (float(row[key]) for key in ("Open", "Low", "High", "Close"))
            stop, target = position["stop_price"], position["target_price"]
            held_days = index - position["entry_index"] + 1
            reason = None
            exit_price = close
            if stop is not None and (open_price <= stop or low <= stop):
                # When stop and target are both touched inside one daily candle,
                # use the stop first as the conservative assumption.
                exit_price = open_price if open_price <= stop else stop
                reason = "stop-loss"
            elif target is not None and (open_price >= target or high >= target):
                exit_price = open_price if open_price >= target else target
                reason = "take-profit"
            elif held_days >= params.holding_days:
                reason = "holding-period"
            elif index == last_index:
                reason = "test-period-end"
            if reason:
                finish_position(index, exit_price, reason)
            else:
                equity = position["cash_reserve"] + position["invested_equity"] * close / position["entry_price"]

        close = float(row["Close"])
        buy_hold = baseline_start * close / start_price
        if index == last_index:
            buy_hold *= 1 - friction
        daily.append({"date": row["Date"].date().isoformat(), "equity": equity, "buy_hold": buy_hold})

    if position is not None:
        finish_position(last_index, float(frame.iloc[last_index]["Close"]), "test-period-end")
        daily[-1]["equity"] = equity

    equity_values = np.asarray([point["equity"] for point in daily], dtype=float)
    buy_hold_values = np.asarray([point["buy_hold"] for point in daily], dtype=float)
    strategy_returns = np.diff(equity_values) / equity_values[:-1] if len(equity_values) > 1 else np.asarray([])
    downside_deviation = float(np.sqrt(np.mean(np.minimum(strategy_returns, 0) ** 2))) if len(strategy_returns) else 0.0

    def sharpe(values: np.ndarray) -> float:
        return float(values.mean() / values.std(ddof=1) * np.sqrt(252)) if len(values) > 1 and values.std(ddof=1) > 0 else 0.0

    def max_drawdown(values: np.ndarray) -> np.ndarray:
        peaks = np.maximum.accumulate(values)
        return values / peaks - 1

    drawdowns = max_drawdown(equity_values)
    buy_hold_drawdowns = max_drawdown(buy_hold_values)
    period_days = max((date.fromisoformat(daily[-1]["date"]) - date.fromisoformat(daily[0]["date"])).days, 1)

    # Reduce the chart payload to roughly weekly observations while retaining both ends.
    sampled_indices = sorted(set(range(0, len(daily), 5)) | {len(daily) - 1})
    equity_curve = [{
        "date": daily[i]["date"], "strategy": round(daily[i]["equity"], 2), "buy_hold": round(daily[i]["buy_hold"], 2),
    } for i in sampled_indices]
    drawdown_series = [{
        "date": daily[i]["date"], "strategy": float(drawdowns[i] * 100), "buy_hold": float(buy_hold_drawdowns[i] * 100),
    } for i in sampled_indices]

    month_ends: dict[str, dict[str, Any]] = {}
    for point in daily:
        month_ends[point["date"][:7]] = point
    monthly_returns = []
    previous_strategy = capital
    previous_buy_hold = capital
    for month, point in month_ends.items():
        monthly_returns.append({
            "month": month,
            "strategy_pct": (point["equity"] / previous_strategy - 1) * 100 if previous_strategy else 0.0,
            "buy_hold_pct": (point["buy_hold"] / previous_buy_hold - 1) * 100 if previous_buy_hold else 0.0,
        })
        previous_strategy, previous_buy_hold = point["equity"], point["buy_hold"]

    winners = [trade["net_pnl"] for trade in trades if trade["net_pnl"] > 0]
    losers = [trade["net_pnl"] for trade in trades if trade["net_pnl"] < 0]
    gross_loss = abs(sum(losers))
    profit_factor = sum(winners) / gross_loss if gross_loss > 0 else (None if not winners else None)
    strategy_return = equity_values[-1] / capital - 1
    buy_hold_return = buy_hold_values[-1] / capital - 1
    return {
        "selected_rule": selected,
        "split": {
            "train_ratio": params.train_ratio,
            "train_rows": mined["train_rows"], "test_rows": mined["test_rows"],
            "train_end_date": mined["train_end_date"],
            "test_start_date": daily[0]["date"], "test_end_date": daily[-1]["date"],
            "explanation": "Rules are mined only on the first chronological training segment. Test signals at day t enter at the next day's open; stop/target checks use that day's OHLC range.",
        },
        "metrics": {
            "strategy_total_return_pct": strategy_return * 100,
            "buy_hold_total_return_pct": buy_hold_return * 100,
            "strategy_cagr_pct": ((equity_values[-1] / capital) ** (365.25 / period_days) - 1) * 100 if equity_values[-1] > 0 else -100.0,
            "buy_hold_cagr_pct": ((buy_hold_values[-1] / capital) ** (365.25 / period_days) - 1) * 100 if buy_hold_values[-1] > 0 else -100.0,
            "strategy_sharpe": sharpe(strategy_returns), "buy_hold_sharpe": sharpe(np.diff(buy_hold_values) / buy_hold_values[:-1]) if len(buy_hold_values) > 1 else 0.0,
            "strategy_sortino": float(strategy_returns.mean() / downside_deviation * np.sqrt(252)) if downside_deviation > 0 else 0.0,
            "strategy_max_drawdown_pct": float(drawdowns.min() * 100),
            "buy_hold_max_drawdown_pct": float(buy_hold_drawdowns.min() * 100),
            "win_rate_pct": len(winners) / len(trades) * 100 if trades else 0.0,
            "profit_factor": profit_factor,
            "number_of_trades": len(trades),
            "initial_capital": capital, "ending_equity": float(equity_values[-1]),
            "position_size_pct": params.position_size_pct,
        },
        "equity_curve": equity_curve,
        "drawdown_series": drawdown_series,
        "monthly_returns": monthly_returns,
        "trades": list(reversed(trades[-100:])),
        "trade_log_note": "Showing the most recent 100 trades; metrics use all test-period trades.",
    }
