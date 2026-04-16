from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.middleware import SessionMiddleware
from src.db import close_pool, get_db, init_pool
from src.routers import activity, dashboard, document, invoice, milestone, product, purchase_order, qualification_type, reference_data, vendor
from src.routers.auth import router as auth_router, invite_router
from src.schema import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_pool()
    async with get_db() as conn:
        await init_db(conn)
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(SessionMiddleware)

app.include_router(auth_router)
app.include_router(invite_router)
app.include_router(purchase_order.router)
app.include_router(reference_data.router)
app.include_router(vendor.router)
app.include_router(product.router)
app.include_router(dashboard.router)
app.include_router(invoice.router)
app.include_router(milestone.router)
app.include_router(activity.router)
app.include_router(document.router)
app.include_router(qualification_type.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
