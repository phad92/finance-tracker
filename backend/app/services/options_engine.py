from datetime import date
from typing import List, Optional
import numpy as np
from scipy.stats import norm

from app.schemas.options import (
    OptionAnalyticsResult,
    OptionAnalyzeRequest,
    OptionGreeks,
    PayoffPoint,
    StrategyPayoffRequest,
    StrategyPayoffResponse,
)


def _binomial_crr_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str,
    steps: int = 60,
) -> float:
    """
    Cox-Ross-Rubinstein Binomial Tree for American-style option valuation,
    incorporating early exercise checks at every lattice node.
    """
    if T <= 0:
        return max(0.0, S - K) if option_type == "CALL" else max(0.0, K - S)

    dt = T / steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1.0 / u
    disc = np.exp(-r * dt)
    p = (np.exp(r * dt) - d) / (u - d)
    p = max(0.0, min(1.0, p))

    # Terminal asset prices
    j = np.arange(steps + 1)
    ST = S * (u ** (steps - j)) * (d ** j)

    if option_type == "CALL":
        V = np.maximum(0.0, ST - K)
    else:
        V = np.maximum(0.0, K - ST)

    # Backward induction with early exercise check
    for i in range(steps - 1, -1, -1):
        V = disc * (p * V[:-1] + (1.0 - p) * V[1:])
        S_i = S * (u ** (i - np.arange(i + 1))) * (d ** np.arange(i + 1))
        if option_type == "CALL":
            intrinsic = np.maximum(0.0, S_i - K)
        else:
            intrinsic = np.maximum(0.0, K - S_i)
        V = np.maximum(V, intrinsic)

    return float(V[0])


def calculate_option_analytics(
    req: OptionAnalyzeRequest,
    underlying_price_date: Optional[date] = None,
) -> OptionAnalyticsResult:
    """
    Compute theoretical price, intrinsic/extrinsic breakdown, break-even, max risk,
    probability of ITM, and first/second-order Greeks (Delta, Gamma, Theta, Vega, Rho).
    """
    S = req.spot_price
    K = req.strike_price
    T = max(req.days_to_expiry / 365.0, 1e-6)
    r = req.risk_free_rate
    sigma = req.volatility
    opt_type = req.option_type.upper().strip()
    side = req.side.upper().strip()
    style = req.exercise_style.upper().strip()

    # Intrinsic value
    if opt_type == "CALL":
        intrinsic = max(0.0, S - K)
    else:
        intrinsic = max(0.0, K - S)

    # Black-Scholes terms (used for European pricing and analytical Greeks)
    sqrt_T = np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    if req.days_to_expiry == 0:
        bs_price = intrinsic
        delta = (1.0 if S > K else 0.0) if opt_type == "CALL" else (-1.0 if S < K else 0.0)
        gamma = 0.0
        theta_annual = 0.0
        vega_raw = 0.0
        rho_raw = 0.0
        prob_itm = 100.0 if intrinsic > 0 else 0.0
    else:
        pdf_d1 = float(norm.pdf(d1))
        cdf_d1 = float(norm.cdf(d1))
        cdf_d2 = float(norm.cdf(d2))

        if opt_type == "CALL":
            bs_price = S * cdf_d1 - K * np.exp(-r * T) * cdf_d2
            delta = cdf_d1
            theta_annual = -(S * pdf_d1 * sigma) / (2.0 * sqrt_T) - r * K * np.exp(-r * T) * cdf_d2
            rho_raw = K * T * np.exp(-r * T) * cdf_d2
            prob_itm = cdf_d2 * 100.0
        else:
            bs_price = K * np.exp(-r * T) * float(norm.cdf(-d2)) - S * float(norm.cdf(-d1))
            delta = cdf_d1 - 1.0
            theta_annual = -(S * pdf_d1 * sigma) / (2.0 * sqrt_T) + r * K * np.exp(-r * T) * float(norm.cdf(-d2))
            rho_raw = -K * T * np.exp(-r * T) * float(norm.cdf(-d2))
            prob_itm = float(norm.cdf(-d2)) * 100.0

        gamma = pdf_d1 / (S * sigma * sqrt_T)
        vega_raw = S * pdf_d1 * sqrt_T

    # Use Binomial Tree for American options valuation
    if style == "AMERICAN" and req.days_to_expiry > 0:
        theoretical_price = _binomial_crr_price(S, K, T, r, sigma, opt_type)
        pricing_model = "BINOMIAL_CRR"
    else:
        theoretical_price = float(bs_price)
        pricing_model = "BLACK_SCHOLES"

    extrinsic = max(0.0, theoretical_price - intrinsic)

    # Adjust sign for SHORT position on Greeks
    pos_sign = 1.0 if side == "LONG" else -1.0
    greeks = OptionGreeks(
        delta=round(delta * pos_sign, 4),
        gamma=round(gamma * pos_sign, 4),
        theta_daily=round((theta_annual / 365.0) * pos_sign, 4),
        vega_per_pct=round((vega_raw / 100.0) * pos_sign, 4),
        rho_per_pct=round((rho_raw / 100.0) * pos_sign, 4),
    )

    # Entry premium defaults to theoretical price if not provided
    ref_premium = req.entry_premium if req.entry_premium is not None else theoretical_price
    total_notional_multiplier = req.contract_multiplier * req.contracts
    premium_total = ref_premium * total_notional_multiplier

    if opt_type == "CALL":
        break_even = K + ref_premium
        if side == "LONG":
            max_profit = None  # Theoretically unlimited upside
            max_loss = round(premium_total, 2)
        else:
            max_profit = round(premium_total, 2)
            max_loss = None  # Uncovered short call risk is unlimited
    else:
        break_even = max(0.0, K - ref_premium)
        max_stock_drop_val = K * total_notional_multiplier
        if side == "LONG":
            max_profit = round(max(0.0, max_stock_drop_val - premium_total), 2)
            max_loss = round(premium_total, 2)
        else:
            max_profit = round(premium_total, 2)
            max_loss = round(max(0.0, max_stock_drop_val - premium_total), 2)

    return OptionAnalyticsResult(
        theoretical_price=round(theoretical_price, 4),
        intrinsic_value=round(intrinsic, 4),
        extrinsic_value=round(extrinsic, 4),
        break_even_price=round(break_even, 4),
        max_profit=max_profit,
        max_loss=max_loss,
        prob_itm_pct=round(prob_itm, 2),
        greeks=greeks,
        pricing_model=pricing_model,
        valuation_label="MODEL_ESTIMATED",
        underlying_spot_price=round(S, 4),
        underlying_price_date=underlying_price_date,
    )


def compute_strategy_payoff(req: StrategyPayoffRequest) -> StrategyPayoffResponse:
    """
    Generate an expiration payoff curve across underlying spot price scenarios
    for single-leg or multi-leg options strategies (Covered Call, Spreads, Iron Condor, Straddle).
    """
    low_price = max(0.01, req.underlying_spot * (1.0 - req.price_range_pct))
    high_price = req.underlying_spot * (1.0 + req.price_range_pct)
    price_grid = np.linspace(low_price, high_price, 45)

    # Calculate net initial cash flow (negative = debit paid, positive = credit received)
    net_entry_cash = 0.0
    for leg in req.legs:
        sign = -1.0 if leg.side.upper() == "LONG" else 1.0
        if leg.option_type.upper() == "STOCK":
            net_entry_cash += sign * leg.strike_price * leg.contracts  # Here contracts = shares
        else:
            net_entry_cash += sign * leg.premium * leg.contracts * leg.contract_multiplier

    curve: List[PayoffPoint] = []
    pnls: List[float] = []

    for spot in price_grid:
        total_pnl = 0.0
        for leg in req.legs:
            l_type = leg.option_type.upper()
            l_side = leg.side.upper()
            pos_sign = 1.0 if l_side == "LONG" else -1.0

            if l_type == "CALL":
                intrinsic = max(0.0, float(spot) - leg.strike_price)
                leg_pnl = (intrinsic - leg.premium) * pos_sign * leg.contracts * leg.contract_multiplier
            elif l_type == "PUT":
                intrinsic = max(0.0, leg.strike_price - float(spot))
                leg_pnl = (intrinsic - leg.premium) * pos_sign * leg.contracts * leg.contract_multiplier
            else:  # STOCK leg (e.g., Covered Call underlying shares)
                leg_pnl = (float(spot) - leg.strike_price) * pos_sign * leg.contracts

            total_pnl += leg_pnl

        rounded_pnl = round(total_pnl, 2)
        pnls.append(rounded_pnl)
        curve.append(PayoffPoint(underlying_price=round(float(spot), 2), pnl=rounded_pnl))

    # Find approximate break-even crossings
    break_evens: List[float] = []
    for i in range(1, len(curve)):
        y1, y2 = curve[i - 1].pnl, curve[i].pnl
        if (y1 < 0 <= y2) or (y1 > 0 >= y2):
            x1, x2 = curve[i - 1].underlying_price, curve[i].underlying_price
            if y2 != y1:
                be = x1 - y1 * (x2 - x1) / (y2 - y1)
                break_evens.append(round(be, 2))

    # Check if unbounded at extremes
    has_uncapped_long_call = sum(
        (1 if l.side.upper() == "LONG" else -1) * l.contracts * l.contract_multiplier
        for l in req.legs
        if l.option_type.upper() == "CALL"
    ) + sum(
        (1 if l.side.upper() == "LONG" else -1) * l.contracts
        for l in req.legs
        if l.option_type.upper() == "STOCK"
    )

    max_profit = None if has_uncapped_long_call > 0 else round(max(pnls), 2)
    max_loss = None if has_uncapped_long_call < 0 else round(min(pnls), 2)

    return StrategyPayoffResponse(
        underlying_spot=round(req.underlying_spot, 2),
        net_entry_cash_flow=round(net_entry_cash, 2),
        max_profit=max_profit,
        max_loss=max_loss,
        break_even_prices=break_evens,
        curve=curve,
    )

