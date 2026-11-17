from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.models.markets import Exchange, Instrument, InstrumentPrice
from app.schemas.markets import (
    ExchangeResponse,
    InstrumentCreate,
    InstrumentPriceResponse,
    InstrumentResponse,
    MarketSyncResult,
)
from app.services.market_data import (
    fetch_us_stock_eod_price,
    parse_and_ingest_gse_csv,
    seed_market_master_data,
    sync_daily_fx_rates,
)

router = APIRouter(prefix="/markets", tags=["Market Data & Ingestion"])


@router.get("/exchanges", response_model=List[ExchangeResponse])
async def list_exchanges(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Exchange]:
    """List supported stock exchanges (GSE, NYSE, NASDAQ, JSE)."""
    stmt = select(Exchange).order_by(Exchange.code)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/instruments", response_model=List[InstrumentResponse])
async def list_instruments(
    exchange_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InstrumentResponse]:
    """List available market securities and their latest recorded prices."""
    stmt = select(Instrument).options(
        selectinload(Instrument.exchange),
        selectinload(Instrument.prices),
    ).order_by(Instrument.symbol)

    if exchange_code:
        stmt = stmt.join(Exchange).where(Exchange.code == exchange_code.upper().strip())

    result = await db.execute(stmt)
    instruments = result.scalars().all()

    resp = []
    for inst in instruments:
        latest_price = None
        latest_date = None
        source = None
        if inst.prices:
            # Sort descending by price_date in Python if not ordered
            sorted_prices = sorted(inst.prices, key=lambda p: p.price_date, reverse=True)
            latest_price = float(sorted_prices[0].close)
            latest_date = sorted_prices[0].price_date
            source = sorted_prices[0].source

        resp.append(
            InstrumentResponse(
                id=inst.id,
                symbol=inst.symbol,
                name=inst.name,
                exchange_id=inst.exchange_id,
                exchange_code=inst.exchange.code if inst.exchange else None,
                instrument_type=inst.instrument_type,
                currency_code=inst.currency_code,
                sector=inst.sector,
                latest_price=latest_price,
                latest_price_date=latest_date,
                data_source=source,
            )
        )
    return resp


@router.post("/instruments", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED)
async def create_instrument(
    inst_in: InstrumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InstrumentResponse:
    """Register a new security or instrument in the market master."""
    ex_stmt = select(Exchange).where(Exchange.code == inst_in.exchange_code.upper().strip())
    exchange = (await db.execute(ex_stmt)).scalar_one_or_none()
    if not exchange:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Exchange '{inst_in.exchange_code}' not found")

    new_inst = Instrument(
        symbol=inst_in.symbol.upper().strip(),
        name=inst_in.name,
        exchange_id=exchange.id,
        instrument_type=inst_in.instrument_type.upper().strip(),
        currency_code=inst_in.currency_code.upper().strip(),
        sector=inst_in.sector,
        isin=inst_in.isin,
    )
    db.add(new_inst)
    await db.flush()
    await db.refresh(new_inst)

    return InstrumentResponse(
        id=new_inst.id,
        symbol=new_inst.symbol,
        name=new_inst.name,
        exchange_id=new_inst.exchange_id,
        exchange_code=exchange.code,
        instrument_type=new_inst.instrument_type,
        currency_code=new_inst.currency_code,
        sector=new_inst.sector,
    )


@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_markets_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed baseline exchanges and securities (ETFs, GSE, US equities, commodities)."""
    await seed_market_master_data(db)
    return {"status": "seeded", "message": "Market master data seeded successfully."}


@router.post("/sync/fx", status_code=status.HTTP_200_OK)
async def sync_fx_rates_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger synchronization of daily currency exchange rates (USD/EUR/GBP to GHS)."""
    rates = await sync_daily_fx_rates(db)
    return {"status": "synced", "rates_updated": rates}


@router.post("/sync/us/{symbol}", response_model=MarketSyncResult)
async def sync_us_ticker(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketSyncResult:
    """Fetch the latest EOD closing price for a US stock or ETF via yfinance."""
    price = await fetch_us_stock_eod_price(db, symbol)
    if price is None:
        return MarketSyncResult(
            synced_count=0,
            failed_symbols=[symbol.upper()],
            source="YFINANCE_EOD",
            message=f"Could not fetch live quote for {symbol.upper()}. Ensure symbol is valid or network is accessible.",
        )
    return MarketSyncResult(
        synced_count=1,
        failed_symbols=[],
        source="YFINANCE_EOD",
        message=f"Updated {symbol.upper()} closing price to ${price}",
    )


@router.post("/gse/upload-csv", response_model=MarketSyncResult)
async def upload_gse_csv_prices(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketSyncResult:
    """
    Upload a CSV file containing Ghana Stock Exchange (GSE) daily closing prices.
    Columns: Symbol, ClosePrice, [Volume], [Date YYYY-MM-DD]
    """
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV upload exceeds maximum 5 MB limit.",
        )
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be UTF-8 encoded CSV text.",
        )
    count, errors = await parse_and_ingest_gse_csv(db, text)
    return MarketSyncResult(
        synced_count=count,
        failed_symbols=errors,
        source="GSE_CSV_INGESTION",
        message=f"Successfully ingested {count} GSE price updates. {len(errors)} warnings/errors.",
    )


@router.get("/instruments/{symbol}/prices", response_model=List[InstrumentPriceResponse])
async def get_instrument_price_history(
    symbol: str,
    limit: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InstrumentPrice]:
    """Retrieve historical EOD price observations for a specific ticker symbol."""
    stmt = (
        select(InstrumentPrice)
        .join(Instrument)
        .where(Instrument.symbol == symbol.upper().strip())
        .order_by(desc(InstrumentPrice.price_date))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

