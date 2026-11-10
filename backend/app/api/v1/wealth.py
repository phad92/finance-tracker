import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.identity import User
from app.models.wealth import Asset, AssetCategory, AssetValuation, Liability
from app.schemas.wealth import (
    AssetCategoryResponse,
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    AssetValuationCreate,
    AssetValuationResponse,
    LiabilityCreate,
    LiabilityResponse,
    LiabilityUpdate,
    NetWorthSummary,
)
from app.services.currency import convert_amount
from app.services.wealth import calculate_net_worth

router = APIRouter(prefix="/wealth", tags=["Wealth & Asset Management"])


@router.get("/summary", response_model=NetWorthSummary)
async def get_net_worth_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NetWorthSummary:
    """Calculate and return consolidated net worth, category allocation, and currency exposure."""
    return await calculate_net_worth(
        db=db,
        user_id=current_user.id,
        reporting_currency=current_user.default_currency,
    )


@router.get("/categories", response_model=List[AssetCategoryResponse])
async def list_asset_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AssetCategory]:
    """Retrieve all available asset categories."""
    stmt = select(AssetCategory).order_by(AssetCategory.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/assets", response_model=List[AssetResponse])
async def list_assets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[AssetResponse]:
    """Retrieve all active assets for the authenticated user, including latest valuations."""
    stmt = (
        select(Asset)
        .where(Asset.user_id == current_user.id, Asset.is_active == True)
        .options(selectinload(Asset.category), selectinload(Asset.valuations))
        .order_by(Asset.name)
    )
    result = await db.execute(stmt)
    assets = result.scalars().all()

    response_list = []
    for asset in assets:
        latest_val = None
        if asset.valuations:
            v = asset.valuations[0]
            latest_val = AssetValuationResponse.model_validate(v)

        item = AssetResponse(
            id=asset.id,
            category_id=asset.category_id,
            category_name=asset.category.name if asset.category else None,
            name=asset.name,
            institution=asset.institution,
            currency=asset.currency,
            ownership_percentage=float(asset.ownership_percentage),
            is_active=asset.is_active,
            latest_valuation=latest_val,
            notes=asset.notes,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )
        response_list.append(item)

    return response_list


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_in: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetResponse:
    """Create a new user asset, with optional initial valuation."""
    new_asset = Asset(
        user_id=current_user.id,
        category_id=asset_in.category_id,
        name=asset_in.name,
        institution=asset_in.institution,
        currency=asset_in.currency.upper().strip(),
        ownership_percentage=asset_in.ownership_percentage,
        notes=asset_in.notes,
    )
    db.add(new_asset)
    await db.flush()

    latest_val_resp = None
    if asset_in.initial_valuation:
        val_in = asset_in.initial_valuation
        val_reporting, applied_rate = await convert_amount(
            db=db,
            amount=val_in.value_original_currency,
            from_currency=val_in.currency,
            to_currency=current_user.default_currency,
            rate_date=val_in.valuation_date,
        )

        initial_val = AssetValuation(
            user_id=current_user.id,
            asset_id=new_asset.id,
            valuation_date=val_in.valuation_date,
            value_original_currency=val_in.value_original_currency,
            currency=val_in.currency.upper().strip(),
            exchange_rate_to_reporting=applied_rate,
            value_reporting_currency=val_reporting,
            valuation_method=val_in.valuation_method,
            notes=val_in.notes,
        )
        db.add(initial_val)
        await db.flush()
        latest_val_resp = AssetValuationResponse.model_validate(initial_val)

    await db.refresh(new_asset)

    # Fetch category name
    cat = await db.get(AssetCategory, new_asset.category_id)

    return AssetResponse(
        id=new_asset.id,
        category_id=new_asset.category_id,
        category_name=cat.name if cat else None,
        name=new_asset.name,
        institution=new_asset.institution,
        currency=new_asset.currency,
        ownership_percentage=float(new_asset.ownership_percentage),
        is_active=new_asset.is_active,
        latest_valuation=latest_val_resp,
        notes=new_asset.notes,
        created_at=new_asset.created_at,
        updated_at=new_asset.updated_at,
    )


@router.post("/assets/{asset_id}/valuations", response_model=AssetValuationResponse, status_code=status.HTTP_201_CREATED)
async def add_asset_valuation(
    asset_id: uuid.UUID,
    val_in: AssetValuationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetValuationResponse:
    """Record a new historical valuation for an asset."""
    # Enforce tenant isolation check
    asset_stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == current_user.id)
    result = await db.execute(asset_stmt)
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    val_reporting, applied_rate = await convert_amount(
        db=db,
        amount=val_in.value_original_currency,
        from_currency=val_in.currency,
        to_currency=current_user.default_currency,
        rate_date=val_in.valuation_date,
    )

    new_val = AssetValuation(
        user_id=current_user.id,
        asset_id=asset.id,
        valuation_date=val_in.valuation_date,
        value_original_currency=val_in.value_original_currency,
        currency=val_in.currency.upper().strip(),
        exchange_rate_to_reporting=applied_rate,
        value_reporting_currency=val_reporting,
        valuation_method=val_in.valuation_method,
        notes=val_in.notes,
    )
    db.add(new_val)
    await db.flush()
    await db.refresh(new_val)
    return AssetValuationResponse.model_validate(new_val)


@router.get("/liabilities", response_model=List[LiabilityResponse])
async def list_liabilities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[Liability]:
    """Retrieve all active liabilities for the authenticated user."""
    stmt = (
        select(Liability)
        .where(Liability.user_id == current_user.id, Liability.is_active == True)
        .order_by(Liability.name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/liabilities", response_model=LiabilityResponse, status_code=status.HTTP_201_CREATED)
async def create_liability(
    liab_in: LiabilityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Liability:
    """Record a new liability or debt obligation."""
    new_liab = Liability(
        user_id=current_user.id,
        name=liab_in.name,
        institution=liab_in.institution,
        category=liab_in.category.upper().strip(),
        currency=liab_in.currency.upper().strip(),
        original_balance=liab_in.original_balance,
        current_balance=liab_in.current_balance,
        interest_rate=liab_in.interest_rate,
        monthly_payment=liab_in.monthly_payment,
        start_date=liab_in.start_date,
        maturity_date=liab_in.maturity_date,
        notes=liab_in.notes,
    )
    db.add(new_liab)
    await db.flush()
    await db.refresh(new_liab)
    return new_liab
