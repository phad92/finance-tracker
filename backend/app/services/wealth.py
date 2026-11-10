import uuid
from datetime import date
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wealth import Asset, AssetCategory, Liability
from app.schemas.wealth import NetWorthSummary
from app.services.currency import convert_amount


async def calculate_net_worth(
    db: AsyncSession,
    user_id: uuid.UUID,
    reporting_currency: str = "GHS",
) -> NetWorthSummary:
    """
    Calculate consolidated net worth, category allocation, and currency exposure
    for a specific user in their reporting currency.
    """
    # 1. Fetch user's active assets with categories and valuations
    asset_stmt = (
        select(Asset)
        .where(Asset.user_id == user_id, Asset.is_active == True)
        .options(selectinload(Asset.category), selectinload(Asset.valuations))
    )
    asset_result = await db.execute(asset_stmt)
    assets = asset_result.scalars().all()

    total_assets = 0.0
    assets_by_category = defaultdict(float)
    currency_exposure = defaultdict(float)

    for asset in assets:
        if asset.valuations:
            # First valuation in desc order is the latest
            latest_val = asset.valuations[0]
            val_amount = float(latest_val.value_original_currency)
            val_currency = latest_val.currency
        else:
            val_amount = 0.0
            val_currency = asset.currency

        # Apply ownership percentage
        adjusted_val = val_amount * (float(asset.ownership_percentage) / 100.0)

        # Convert to reporting currency
        val_in_reporting, _ = await convert_amount(
            db=db,
            amount=adjusted_val,
            from_currency=val_currency,
            to_currency=reporting_currency,
        )

        total_assets += val_in_reporting
        cat_name = asset.category.name if asset.category else "Uncategorized"
        assets_by_category[cat_name] += val_in_reporting
        currency_exposure[val_currency] += val_in_reporting

    # 2. Fetch user's active liabilities
    liab_stmt = select(Liability).where(
        Liability.user_id == user_id,
        Liability.is_active == True,
    )
    liab_result = await db.execute(liab_stmt)
    liabilities = liab_result.scalars().all()

    total_liabilities = 0.0
    for liab in liabilities:
        bal = float(liab.current_balance)
        bal_in_reporting, _ = await convert_amount(
            db=db,
            amount=bal,
            from_currency=liab.currency,
            to_currency=reporting_currency,
        )
        total_liabilities += bal_in_reporting

    net_worth = total_assets - total_liabilities

    return NetWorthSummary(
        reporting_currency=reporting_currency,
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        net_worth=round(net_worth, 2),
        assets_by_category={k: round(v, 2) for k, v in assets_by_category.items()},
        currency_exposure={k: round(v, 2) for k, v in currency_exposure.items()},
        as_of_date=date.today(),
    )

