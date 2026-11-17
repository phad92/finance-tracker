import uuid
from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.models.investments import Portfolio
from app.models.markets import Instrument, InstrumentPrice
from app.models.options import OptionPosition, OptionTransaction
from app.schemas.options import (
    OptionAnalyticsResult,
    OptionAnalyzeRequest,
    OptionPositionCloseRequest,
    OptionPositionCreate,
    OptionPositionResponse,
    StrategyPayoffRequest,
    StrategyPayoffResponse,
)
from app.services.options_engine import calculate_option_analytics, compute_strategy_payoff

router = APIRouter(prefix="/options", tags=["Options Trading & Quantitative Engine"])


async def _resolve_spot_price(db: AsyncSession, symbol: str, fallback_strike: float):
    """Look up latest observed underlying stock price if available in DB."""
    stmt = (
        select(InstrumentPrice)
        .join(Instrument)
        .where(Instrument.symbol == symbol.upper().strip())
        .order_by(desc(InstrumentPrice.price_date))
        .limit(1)
    )
    price_row = (await db.execute(stmt)).scalar_one_or_none()
    if price_row:
        return float(price_row.close), price_row.price_date
    return fallback_strike, None


@router.get("/positions", response_model=List[OptionPositionResponse])
async def list_option_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[OptionPositionResponse]:
    """
    List user's options contract positions enriched with local theoretical Greeks
    and fair-value estimates (clearly marked MODEL_ESTIMATED per Section 16.3).
    """
    stmt = (
        select(OptionPosition)
        .where(OptionPosition.user_id == current_user.id)
        .order_by(OptionPosition.expiration_date)
    )
    positions = (await db.execute(stmt)).scalars().all()

    resp = []
    today = date.today()
    for pos in positions:
        spot_price, spot_date = await _resolve_spot_price(db, pos.underlying_symbol, float(pos.strike_price))
        dte = max(0, (pos.expiration_date - today).days)

        analytics = None
        est_pnl = None
        if pos.status == "OPEN":
            analytics = calculate_option_analytics(
                OptionAnalyzeRequest(
                    spot_price=spot_price,
                    strike_price=float(pos.strike_price),
                    days_to_expiry=dte,
                    volatility=float(pos.assumed_volatility),
                    option_type=pos.option_type,
                    side=pos.side,
                    exercise_style=pos.exercise_style,
                    contract_multiplier=pos.contract_multiplier,
                    contracts=pos.contracts,
                    entry_premium=float(pos.entry_premium),
                ),
                underlying_price_date=spot_date,
            )
            diff = analytics.theoretical_price - float(pos.entry_premium)
            sign = 1.0 if pos.side == "LONG" else -1.0
            est_pnl = round(diff * sign * pos.contracts * pos.contract_multiplier - float(pos.fees), 2)

        notional = round(float(pos.strike_price) * pos.contract_multiplier * pos.contracts, 2)
        resp.append(
            OptionPositionResponse(
                id=pos.id,
                underlying_symbol=pos.underlying_symbol,
                option_symbol=pos.option_symbol,
                option_type=pos.option_type,
                side=pos.side,
                strategy_tag=pos.strategy_tag,
                exercise_style=pos.exercise_style,
                strike_price=float(pos.strike_price),
                expiration_date=pos.expiration_date,
                contract_multiplier=pos.contract_multiplier,
                contracts=pos.contracts,
                notional_exposure=notional,
                entry_premium=float(pos.entry_premium),
                fees=float(pos.fees),
                currency=pos.currency,
                assumed_volatility=float(pos.assumed_volatility),
                status=pos.status,
                analytics=analytics,
                estimated_unrealized_pnl=est_pnl,
                created_at=pos.created_at,
            )
        )
    return resp


@router.post("/positions", response_model=OptionPositionResponse, status_code=status.HTTP_201_CREATED)
async def create_option_position(
    pos_in: OptionPositionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OptionPositionResponse:
    """Open a new options contract position and log the opening premium cash flow."""
    if pos_in.portfolio_id is not None:
        p_stmt = select(Portfolio).where(
            Portfolio.id == pos_in.portfolio_id,
            Portfolio.user_id == current_user.id,
        )
        if not (await db.execute(p_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    sym = pos_in.underlying_symbol.upper().strip()
    inst = (await db.execute(select(Instrument).where(Instrument.symbol == sym))).scalar_one_or_none()

    new_pos = OptionPosition(
        user_id=current_user.id,
        portfolio_id=pos_in.portfolio_id,
        underlying_instrument_id=inst.id if inst else None,
        underlying_symbol=sym,
        option_symbol=pos_in.option_symbol,
        option_type=pos_in.option_type.upper().strip(),
        side=pos_in.side.upper().strip(),
        strategy_tag=pos_in.strategy_tag.upper().strip(),
        exercise_style=pos_in.exercise_style.upper().strip(),
        strike_price=pos_in.strike_price,
        expiration_date=pos_in.expiration_date,
        contract_multiplier=pos_in.contract_multiplier,
        contracts=pos_in.contracts,
        entry_premium=pos_in.entry_premium,
        fees=pos_in.fees,
        currency=pos_in.currency.upper().strip(),
        assumed_volatility=pos_in.assumed_volatility,
        status="OPEN",
        notes=pos_in.notes,
    )
    db.add(new_pos)
    await db.flush()

    # Cash flow: LONG pays premium (-), SHORT receives premium (+)
    gross_cash = pos_in.entry_premium * pos_in.contracts * pos_in.contract_multiplier
    net_cash = -gross_cash - pos_in.fees if new_pos.side == "LONG" else gross_cash - pos_in.fees

    db.add(
        OptionTransaction(
            user_id=current_user.id,
            position_id=new_pos.id,
            action="OPEN",
            trade_date=date.today(),
            contracts=pos_in.contracts,
            premium_per_share=pos_in.entry_premium,
            fees=pos_in.fees,
            net_cash_flow=round(net_cash, 4),
            currency=new_pos.currency,
            notes=pos_in.notes,
        )
    )
    await db.flush()
    await db.refresh(new_pos)

    notional = round(float(new_pos.strike_price) * new_pos.contract_multiplier * new_pos.contracts, 2)
    return OptionPositionResponse(
        id=new_pos.id,
        underlying_symbol=new_pos.underlying_symbol,
        option_symbol=new_pos.option_symbol,
        option_type=new_pos.option_type,
        side=new_pos.side,
        strategy_tag=new_pos.strategy_tag,
        exercise_style=new_pos.exercise_style,
        strike_price=float(new_pos.strike_price),
        expiration_date=new_pos.expiration_date,
        contract_multiplier=new_pos.contract_multiplier,
        contracts=new_pos.contracts,
        notional_exposure=notional,
        entry_premium=float(new_pos.entry_premium),
        fees=float(new_pos.fees),
        currency=new_pos.currency,
        assumed_volatility=float(new_pos.assumed_volatility),
        status=new_pos.status,
        created_at=new_pos.created_at,
    )


@router.post("/positions/{position_id}/close", response_model=OptionPositionResponse)
async def close_option_position(
    position_id: uuid.UUID,
    close_in: OptionPositionCloseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OptionPositionResponse:
    """Close, expire, exercise, or assign an open options position."""
    stmt = select(OptionPosition).where(
        OptionPosition.id == position_id, OptionPosition.user_id == current_user.id
    )
    pos = (await db.execute(stmt)).scalar_one_or_none()
    if not pos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option position not found")

    action_map = {
        "CLOSE": "CLOSED",
        "EXPIRE": "EXPIRED",
        "EXERCISE": "EXERCISED",
        "ASSIGN": "ASSIGNED",
    }
    act = close_in.action.upper().strip()
    if act not in action_map:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid close action")

    pos.status = action_map[act]
    gross_cash = close_in.closing_premium * pos.contracts * pos.contract_multiplier
    # Closing a LONG receives cash (+), closing a SHORT pays cash (-)
    net_cash = gross_cash - close_in.fees if pos.side == "LONG" else -gross_cash - close_in.fees

    db.add(
        OptionTransaction(
            user_id=current_user.id,
            position_id=pos.id,
            action=act,
            trade_date=close_in.trade_date,
            contracts=pos.contracts,
            premium_per_share=close_in.closing_premium,
            fees=close_in.fees,
            net_cash_flow=round(net_cash, 4),
            currency=pos.currency,
            notes=close_in.notes,
        )
    )
    await db.flush()
    await db.refresh(pos)

    notional = round(float(pos.strike_price) * pos.contract_multiplier * pos.contracts, 2)
    return OptionPositionResponse(
        id=pos.id,
        underlying_symbol=pos.underlying_symbol,
        option_symbol=pos.option_symbol,
        option_type=pos.option_type,
        side=pos.side,
        strategy_tag=pos.strategy_tag,
        exercise_style=pos.exercise_style,
        strike_price=float(pos.strike_price),
        expiration_date=pos.expiration_date,
        contract_multiplier=pos.contract_multiplier,
        contracts=pos.contracts,
        notional_exposure=notional,
        entry_premium=float(pos.entry_premium),
        fees=float(pos.fees),
        currency=pos.currency,
        assumed_volatility=float(pos.assumed_volatility),
        status=pos.status,
        created_at=pos.created_at,
    )


@router.post("/analyze", response_model=OptionAnalyticsResult)
async def analyze_option_contract(
    req: OptionAnalyzeRequest,
    current_user: User = Depends(get_current_user),
) -> OptionAnalyticsResult:
    """
    Calculate theoretical fair value, Greeks, break-even, and probability of ITM
    using Black-Scholes (European) or Cox-Ross-Rubinstein Binomial Tree (American).
    """
    return calculate_option_analytics(req)


@router.post("/strategy-payoff", response_model=StrategyPayoffResponse)
async def generate_strategy_payoff(
    req: StrategyPayoffRequest,
    current_user: User = Depends(get_current_user),
) -> StrategyPayoffResponse:
    """Generate expiration P&L payoff curves for multi-leg options strategies."""
    return compute_strategy_payoff(req)

