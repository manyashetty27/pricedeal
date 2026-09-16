"""
anomaly.py
-----------
Core "fake discount" detection logic.

The idea: Indian e-commerce listings often show a big struck-through
"original price" next to a "sale price" during festival events. That
original price is sometimes inflated days before the sale starts, making
the discount look bigger than it really is.

Because we record price snapshots over time, we can check a claimed sale
price against the product's own recent price history (not just the
seller's marketing) to see whether it's a genuine low.

This module is intentionally dependency-light (just stdlib) so it's easy
for judges to read end-to-end.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Optional, Sequence, Any


@dataclass
class PriceVerdict:
    current_price: float
    historical_min: Optional[float]
    historical_avg: Optional[float]
    historical_max: Optional[float]
    days_of_history: int
    verdict: str          # "genuine_low" | "inflated_discount" | "insufficient_data" | "no_change"
    explanation: str
    confidence: str        # "low" | "medium" | "high"
    pct_diff_avg: Optional[float] = None
    pct_diff_min: Optional[float] = None


def days_span(checked_at_list: Sequence[str]) -> int:
    """Calculate date span in days from a list of ISO timestamp strings."""
    if len(checked_at_list) < 2:
        return 0
    dates = sorted(datetime.fromisoformat(t.replace('Z', '+00:00')) for t in checked_at_list)
    span = (dates[-1] - dates[0]).days
    return max(span, 1) if len(dates) >= 2 else 0


def evaluate_price(current_price: float, history_rows: Sequence[Any]) -> PriceVerdict:
    """
    Evaluate a current price against historical price snapshot rows.

    history_rows: iterable of sqlite3.Row or dict objects with 'price' and 'checked_at',
    ordered oldest -> newest, NOT including the current price being evaluated.
    """
    prices = [float(r["price"]) for r in history_rows if r["price"] is not None]
    checked_ats = [str(r["checked_at"]) for r in history_rows if r["price"] is not None]
    days = days_span(checked_ats)

    if len(prices) < 3:
        return PriceVerdict(
            current_price=current_price,
            historical_min=min(prices) if prices else None,
            historical_avg=mean(prices) if prices else None,
            historical_max=max(prices) if prices else None,
            days_of_history=days,
            verdict="insufficient_data",
            explanation="Not enough price history yet to judge this discount. "
                        "Keep tracking for a few more days for a reliable verdict.",
            confidence="low",
            pct_diff_avg=None,
            pct_diff_min=None,
        )

    hist_min = min(prices)
    hist_max = max(prices)
    hist_avg = mean(prices)
    std = pstdev(prices) if len(prices) > 1 else 0

    confidence = "high" if days >= 14 else ("medium" if days >= 5 else "low")
    pct_avg = ((current_price - hist_avg) / hist_avg) * 100 if hist_avg else 0
    pct_min = ((current_price - hist_min) / hist_min) * 100 if hist_min else 0

    if current_price <= hist_min * 1.02:
        # At or below the lowest price we've ever seen (2% tolerance for rounding)
        return PriceVerdict(
            current_price=current_price,
            historical_min=hist_min,
            historical_avg=hist_avg,
            historical_max=hist_max,
            days_of_history=days,
            verdict="genuine_low",
            explanation=f"This is at or near the lowest price observed in the last "
                        f"{days} days (previous low: ₹{hist_min:,.0f}). Looks like a real deal.",
            confidence=confidence,
            pct_diff_avg=pct_avg,
            pct_diff_min=pct_min,
        )

    if current_price >= hist_avg + std and current_price < hist_avg * 1.5:
        # Priced meaningfully above its own recent average -> the "discount"
        # being advertised is likely measured against an inflated reference price
        return PriceVerdict(
            current_price=current_price,
            historical_min=hist_min,
            historical_avg=hist_avg,
            historical_max=hist_max,
            days_of_history=days,
            verdict="inflated_discount",
            explanation=f"This price is {pct_avg:.0f}% above its own {days}-day "
                        f"average (₹{hist_avg:,.0f}) and {pct_min:.0f}% "
                        f"above the lowest price seen (₹{hist_min:,.0f}). Any 'sale' badge "
                        f"on this listing may be measured against an inflated reference price.",
            confidence=confidence,
            pct_diff_avg=pct_avg,
            pct_diff_min=pct_min,
        )

    return PriceVerdict(
        current_price=current_price,
        historical_min=hist_min,
        historical_avg=hist_avg,
        historical_max=hist_max,
        days_of_history=days,
        verdict="no_change",
        explanation=f"Roughly in line with its usual price range (avg ₹{hist_avg:,.0f}, "
                    f"low ₹{hist_min:,.0f} over {days} days). Nothing unusual either way.",
        confidence=confidence,
        pct_diff_avg=pct_avg,
        pct_diff_min=pct_min,
    )
