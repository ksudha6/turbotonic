from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import require_role
from src.db import get_db
from src.domain.product import Product
from src.domain.user import User, UserRole
from src.product_dto import (
    ProductCreate,
    ProductListItem,
    ProductResponse,
    ProductUpdate,
    product_to_list_item,
    product_to_response,
)
from src.product_repository import ProductRepository
from src.qualification_type_dto import qualification_type_to_list_item
from src.qualification_type_repository import QualificationTypeRepository

router = APIRouter(prefix="/api/v1/products", tags=["products"])


async def get_product_repo() -> AsyncIterator[ProductRepository]:
    async with get_db() as conn:
        yield ProductRepository(conn)


ProductRepoDep = Annotated[ProductRepository, Depends(get_product_repo)]


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(body: ProductCreate, repo: ProductRepoDep, _user: User = require_role(UserRole.SM)) -> ProductResponse:
    existing = await repo.get_by_vendor_and_part_number(body.vendor_id, body.part_number)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Product with this vendor_id and part_number already exists",
        )
    product = Product.create(
        vendor_id=body.vendor_id,
        part_number=body.part_number,
        description=body.description,
        manufacturing_address=body.manufacturing_address,
    )
    try:
        await repo.save(product)
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(
                status_code=409,
                detail="Product with this vendor_id and part_number already exists",
            ) from exc
        raise
    # New product has no qualifications yet
    return product_to_response(product, [])


@router.get("/", response_model=list[ProductListItem])
async def list_products(
    repo: ProductRepoDep, vendor_id: str | None = None, _user: User = require_role(UserRole.SM, UserRole.QUALITY_LAB)
) -> list[ProductListItem]:
    products = await repo.list_products(vendor_id)
    if not products:
        return []
    async with get_db() as conn:
        qt_repo = QualificationTypeRepository(conn)
        product_ids = [p.id for p in products]
        quals_by_product = await qt_repo.list_by_products(product_ids)
    return [
        product_to_list_item(p, [qualification_type_to_list_item(qt) for qt in quals_by_product.get(p.id, [])])
        for p in products
    ]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, repo: ProductRepoDep, _user: User = require_role(UserRole.SM, UserRole.QUALITY_LAB)) -> ProductResponse:
    product = await repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    async with get_db() as conn:
        qt_repo = QualificationTypeRepository(conn)
        qts = await qt_repo.list_by_product(product_id)
    qualifications = [qualification_type_to_list_item(qt) for qt in qts]
    return product_to_response(product, qualifications)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str, body: ProductUpdate, repo: ProductRepoDep, _user: User = require_role(UserRole.SM)
) -> ProductResponse:
    product = await repo.get_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product.update(
        description=body.description,
        manufacturing_address=body.manufacturing_address,
    )
    await repo.save(product)
    async with get_db() as conn:
        qt_repo = QualificationTypeRepository(conn)
        qts = await qt_repo.list_by_product(product_id)
    qualifications = [qualification_type_to_list_item(qt) for qt in qts]
    return product_to_response(product, qualifications)
