from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db import get_db
from src.routers import dashboard, invoice, milestone, purchase_order, reference_data, vendor
from src.schema import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with get_db() as conn:
        await init_db(conn)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(purchase_order.router)
app.include_router(reference_data.router)
app.include_router(vendor.router)
app.include_router(dashboard.router)
app.include_router(invoice.router)
app.include_router(milestone.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
