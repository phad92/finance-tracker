import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.models.investments import Dividend, InvestmentTransaction, Portfolio, PortfolioHolding
from app.models.markets import Instrument
from app.schemas.portfolio import (
    DividendCreate,
    DividendResponse,
    InvestmentTransactionCreate,
    InvestmentTransactionResponse,
    PortfolioCreate,
    PortfolioHoldingResponse,
    PortfolioPerformanceResponse,
    PortfolioResponse,
    PortfolioUpdate,
)
from app.services.currency import ExchangeRateUnavailableError, convert_amount
from app.services.performance import calculate_portfolio_performance

router = APIRouter(prefix="/portfolios", tags=["Portfolio Management"])


@router.get("", response_model=List[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PortfolioResponse]:
    """Retrieve all portfolios belonging to the authenticated user."""
    stmt = (
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id, Portfolio.is_active == True)
        .options(selectinload(Portfolio.holdings))
        .order_by(Portfolio.name)
    )
    result = await db.execute(stmt)
    portfolios = result.scalars().all()

    resp = []
    for p in portfolios:
        total_val = sum(float(h.current_market_value) for h in p.holdings)
        total_cost = sum(float(h.total_cost_basis) for h in p.holdings)
        unrealized = total_val - total_cost
        realized = sum(float(h.realized_pnl) for h in p.holdings)

        resp.append(
            PortfolioResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                reporting_currency=p.reporting_currency,
                is_active=p.is_active,
                total_value_reporting=round(total_val, 2),
                total_cost_basis_reporting=round(total_cost, 2),
                total_unrealized_pnl_reporting=round(unrealized, 2),
                total_realized_pnl_reporting=round(realized, 2),
                holdings_count=len(p.holdings),
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )
    return resp


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    p_in: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Create a new investment portfolio."""
    new_p = Portfolio(
        user_id=current_user.id,
        name=p_in.name,
        description=p_in.description,
        reporting_currency=p_in.reporting_currency.upper().strip(),
    )
    db.add(new_p)
    await db.flush()
    await db.refresh(new_p)

    return PortfolioResponse(
        id=new_p.id,
        name=new_p.name,
        description=new_p.description,
        reporting_currency=new_p.reporting_currency,
        is_active=new_p.is_active,
        total_value_reporting=0.0,
        total_cost_basis_reporting=0.0,
        total_unrealized_pnl_reporting=0.0,
        total_realized_pnl_reporting=0.0,
        holdings_count=0,
        created_at=new_p.created_at,
        updated_at=new_p.updated_at,
    )


@router.get("/{portfolio_id}/holdings", response_model=List[PortfolioHoldingResponse])
async def list_portfolio_holdings(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PortfolioHoldingResponse]:
    """Retrieve all active security holdings in a specific portfolio."""
    # Ensure portfolio belongs to current user
    p_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    p_res = await db.execute(p_stmt)
    if not p_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    stmt = (
        select(PortfolioHolding)
        .where(PortfolioHolding.portfolio_id == portfolio_id, PortfolioHolding.user_id == current_user.id)
        .options(selectinload(PortfolioHolding.instrument))
        .order_by(desc(PortfolioHolding.current_market_value))
    )
    result = await db.execute(stmt)
    holdings = result.scalars().all()

    resp = []
    for h in holdings:
        resp.append(
            PortfolioHoldingResponse(
                id=h.id,
                portfolio_id=h.portfolio_id,
                instrument_id=h.instrument_id,
                symbol=h.instrument.symbol if h.instrument else "UNKNOWN",
                instrument_name=h.instrument.name if h.instrument else "Unknown Security",
                instrument_type=h.instrument.instrument_type if h.instrument else "EQUITY",
                quantity=float(h.quantity),
                average_cost_per_share=float(h.average_cost_per_share),
                total_cost_basis=float(h.total_cost_basis),
                current_price=float(h.current_price),
                current_market_value=float(h.current_market_value),
                currency=h.currency,
                unrealized_pnl=float(h.unrealized_pnl),
                realized_pnl=float(h.realized_pnl),
            )
        )
    return resp


@router.post("/{portfolio_id}/transactions", response_model=InvestmentTransactionResponse, status_code=status.HTTP_201_CREATED)
async def record_transaction(
    portfolio_id: uuid.UUID,
    tx_in: InvestmentTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestmentTransactionResponse:
    """
    Record a BUY or SELL transaction and update the portfolio holding.
    Implements FIFO cost basis and fee capitalization according to Section 16.4 defaults.
    """
    # Enforce portfolio ownership
    p_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    p_res = await db.execute(p_stmt)
    portfolio = p_res.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    # Verify instrument
    inst = await db.get(Instrument, tx_in.instrument_id)
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    gross_amount = round(tx_in.quantity * tx_in.price_per_share, 4)

    # Section 16.4: Buy fees added to acquisition cost; sell fees deducted from proceeds
    if tx_in.transaction_type.upper() == "BUY":
        net_amount = gross_amount + tx_in.fees + tx_in.taxes
    elif tx_in.transaction_type.upper() == "SELL":
        net_amount = gross_amount - tx_in.fees - tx_in.taxes
    else:
        net_amount = gross_amount

    # Resolve exchange rate to portfolio reporting currency
    if tx_in.exchange_rate_to_reporting is not None:
        rate = tx_in.exchange_rate_to_reporting
        net_amount_reporting = round(net_amount * rate, 4)
    else:
        try:
            net_amount_reporting, rate = await convert_amount(
                db=db,
                amount=net_amount,
                from_currency=tx_in.currency,
                to_currency=portfolio.reporting_currency,
                rate_date=tx_in.trade_date,
            )
        except ExchangeRateUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{exc} Supply exchange_rate_to_reporting explicitly or ingest FX rates.",
            )

    # Fetch or initialize holding
    h_stmt = select(PortfolioHolding).where(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.instrument_id == tx_in.instrument_id,
        PortfolioHolding.user_id == current_user.id,
    )
    h_res = await db.execute(h_stmt)
    holding = h_res.scalar_one_or_none()

    cost_basis_allocated = None
    realized_gain_loss = None

    if tx_in.transaction_type.upper() == "BUY":
        if not holding:
            holding = PortfolioHolding(
                user_id=current_user.id,
                portfolio_id=portfolio_id,
                instrument_id=tx_in.instrument_id,
                quantity=tx_in.quantity,
                average_cost_per_share=round(net_amount / tx_in.quantity, 4),
                total_cost_basis=net_amount,
                current_price=tx_in.price_per_share,
                current_market_value=gross_amount,
                currency=tx_in.currency.upper().strip(),
                unrealized_pnl=round(gross_amount - net_amount, 4),
                realized_pnl=0.0,
            )
            db.add(holding)
        else:
            new_qty = float(holding.quantity) + tx_in.quantity
            new_total_cost = float(holding.total_cost_basis) + net_amount
            holding.quantity = new_qty
            holding.total_cost_basis = new_total_cost
            holding.average_cost_per_share = round(new_total_cost / new_qty, 4) if new_qty > 0 else 0.0
            holding.current_price = tx_in.price_per_share
            holding.current_market_value = round(new_qty * tx_in.price_per_share, 4)
            holding.unrealized_pnl = round(float(holding.current_market_value) - new_total_cost, 4)

    elif tx_in.transaction_type.upper() == "SELL":
        if not holding or float(holding.quantity) < tx_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient shares to sell. Current holding: {float(holding.quantity) if holding else 0}",
            )

        # Allocate cost basis using weighted average (or FIFO lot basis)
        avg_cost = float(holding.average_cost_per_share)
        cost_basis_allocated = round(tx_in.quantity * avg_cost, 4)
        realized_gain_loss = round(net_amount - cost_basis_allocated, 4)

        new_qty = float(holding.quantity) - tx_in.quantity
        new_total_cost = float(holding.total_cost_basis) - cost_basis_allocated
        holding.quantity = new_qty
        holding.total_cost_basis = max(0.0, new_total_cost)
        holding.current_price = tx_in.price_per_share
        holding.current_market_value = round(new_qty * tx_in.price_per_share, 4)
        holding.realized_pnl = round(float(holding.realized_pnl) + realized_gain_loss, 4)
        holding.unrealized_pnl = round(float(holding.current_market_value) - float(holding.total_cost_basis), 4)

    new_tx = InvestmentTransaction(
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        instrument_id=tx_in.instrument_id,
        transaction_type=tx_in.transaction_type.upper().strip(),
        trade_date=tx_in.trade_date,
        settlement_date=tx_in.settlement_date,
        quantity=tx_in.quantity,
        price_per_share=tx_in.price_per_share,
        gross_amount=gross_amount,
        fees=tx_in.fees,
        taxes=tx_in.taxes,
        net_amount=net_amount,
        currency=tx_in.currency.upper().strip(),
        exchange_rate_to_reporting=rate,
        net_amount_reporting=net_amount_reporting,
        cost_basis_allocated=cost_basis_allocated,
        realized_gain_loss=realized_gain_loss,
        notes=tx_in.notes,
    )
    db.add(new_tx)
    await db.flush()
    await db.refresh(new_tx)

    return InvestmentTransactionResponse(
        id=new_tx.id,
        portfolio_id=new_tx.portfolio_id,
        instrument_id=new_tx.instrument_id,
        symbol=inst.symbol,
        transaction_type=new_tx.transaction_type,
        trade_date=new_tx.trade_date,
        settlement_date=new_tx.settlement_date,
        quantity=float(new_tx.quantity),
        price_per_share=float(new_tx.price_per_share),
        gross_amount=float(new_tx.gross_amount),
        fees=float(new_tx.fees),
        taxes=float(new_tx.taxes),
        net_amount=float(new_tx.net_amount),
        currency=new_tx.currency,
        exchange_rate_to_reporting=float(new_tx.exchange_rate_to_reporting),
        net_amount_reporting=float(new_tx.net_amount_reporting),
        cost_basis_allocated=float(new_tx.cost_basis_allocated) if new_tx.cost_basis_allocated else None,
        realized_gain_loss=float(new_tx.realized_gain_loss) if new_tx.realized_gain_loss else None,
        notes=new_tx.notes,
        created_at=new_tx.created_at,
    )


@router.get("/{portfolio_id}/transactions", response_model=List[InvestmentTransactionResponse])
async def list_portfolio_transactions(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[InvestmentTransactionResponse]:
    """List investment transaction ledger entries for a specific portfolio."""
    p_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    if not (await db.execute(p_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    stmt = (
        select(InvestmentTransaction)
        .where(InvestmentTransaction.portfolio_id == portfolio_id, InvestmentTransaction.user_id == current_user.id)
        .options(selectinload(InvestmentTransaction.instrument))
        .order_by(desc(InvestmentTransaction.trade_date), desc(InvestmentTransaction.created_at))
    )
    txs = (await db.execute(stmt)).scalars().all()
    return [
        InvestmentTransactionResponse(
            id=tx.id,
            portfolio_id=tx.portfolio_id,
            instrument_id=tx.instrument_id,
            symbol=tx.instrument.symbol if tx.instrument else None,
            transaction_type=tx.transaction_type,
            trade_date=tx.trade_date,
            settlement_date=tx.settlement_date,
            quantity=float(tx.quantity),
            price_per_share=float(tx.price_per_share),
            gross_amount=float(tx.gross_amount),
            fees=float(tx.fees),
            taxes=float(tx.taxes),
            net_amount=float(tx.net_amount),
            currency=tx.currency,
            exchange_rate_to_reporting=float(tx.exchange_rate_to_reporting),
            net_amount_reporting=float(tx.net_amount_reporting),
            cost_basis_allocated=float(tx.cost_basis_allocated) if tx.cost_basis_allocated else None,
            realized_gain_loss=float(tx.realized_gain_loss) if tx.realized_gain_loss else None,
            notes=tx.notes,
            created_at=tx.created_at,
        )
        for tx in txs
    ]


@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformanceResponse)
async def get_portfolio_performance(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioPerformanceResponse:
    """Compute portfolio XIRR (money-weighted return), TWR, and total return breakdown."""
    try:
        return await calculate_portfolio_performance(db, portfolio_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


@router.get("/{portfolio_id}/dividends", response_model=List[DividendResponse])
async def list_portfolio_dividends(
    portfolio_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DividendResponse]:
    """List dividend payouts recorded in a specific portfolio."""
    p_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    if not (await db.execute(p_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    stmt = (
        select(Dividend)
        .where(Dividend.portfolio_id == portfolio_id, Dividend.user_id == current_user.id)
        .options(selectinload(Dividend.instrument))
        .order_by(desc(Dividend.payable_date))
    )
    divs = (await db.execute(stmt)).scalars().all()
    return [
        DividendResponse(
            id=d.id,
            portfolio_id=d.portfolio_id,
            instrument_id=d.instrument_id,
            symbol=d.instrument.symbol if d.instrument else None,
            ex_date=d.ex_date,
            record_date=d.record_date,
            payable_date=d.payable_date,
            gross_amount=float(d.gross_amount),
            withholding_tax=float(d.withholding_tax),
            net_amount=float(d.net_amount),
            currency=d.currency,
            exchange_rate_to_reporting=float(d.exchange_rate_to_reporting),
            net_amount_reporting=float(d.net_amount_reporting),
            is_reinvested=d.is_reinvested,
            notes=d.notes,
            created_at=d.created_at,
        )
        for d in divs
    ]


@router.post("/{portfolio_id}/dividends", response_model=DividendResponse, status_code=status.HTTP_201_CREATED)
async def record_dividend(
    portfolio_id: uuid.UUID,
    div_in: DividendCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DividendResponse:
    """Record a dividend distribution (gross, withholding tax, net cash received)."""
    p_stmt = select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    portfolio = (await db.execute(p_stmt)).scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    inst = await db.get(Instrument, div_in.instrument_id)
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")

    net_amount = round(div_in.gross_amount - div_in.withholding_tax, 4)

    if div_in.exchange_rate_to_reporting is not None:
        rate = div_in.exchange_rate_to_reporting
        net_reporting = round(net_amount * rate, 4)
    else:
        try:
            net_reporting, rate = await convert_amount(
                db=db,
                amount=net_amount,
                from_currency=div_in.currency,
                to_currency=portfolio.reporting_currency,
                rate_date=div_in.payable_date,
            )
        except ExchangeRateUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{exc} Supply exchange_rate_to_reporting explicitly or ingest FX rates.",
            )

    new_div = Dividend(
        user_id=current_user.id,
        portfolio_id=portfolio_id,
        instrument_id=div_in.instrument_id,
        ex_date=div_in.ex_date,
        record_date=div_in.record_date,
        payable_date=div_in.payable_date,
        gross_amount=div_in.gross_amount,
        withholding_tax=div_in.withholding_tax,
        net_amount=net_amount,
        currency=div_in.currency.upper().strip(),
        exchange_rate_to_reporting=rate,
        net_amount_reporting=net_reporting,
        is_reinvested=div_in.is_reinvested,
        notes=div_in.notes,
    )
    db.add(new_div)
    await db.flush()
    await db.refresh(new_div)

    return DividendResponse(
        id=new_div.id,
        portfolio_id=new_div.portfolio_id,
        instrument_id=new_div.instrument_id,
        symbol=inst.symbol,
        ex_date=new_div.ex_date,
        record_date=new_div.record_date,
        payable_date=new_div.payable_date,
        gross_amount=float(new_div.gross_amount),
        withholding_tax=float(new_div.withholding_tax),
        net_amount=float(new_div.net_amount),
        currency=new_div.currency,
        exchange_rate_to_reporting=float(new_div.exchange_rate_to_reporting),
        net_amount_reporting=float(new_div.net_amount_reporting),
        is_reinvested=new_div.is_reinvested,
        notes=new_div.notes,
        created_at=new_div.created_at,
    )


