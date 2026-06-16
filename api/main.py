import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, ingest, nlp, risk
from api.routers import operations, alerts, reports, patients

_DEV_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
_EXTRA = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
ALLOWED_ORIGINS = _DEV_ORIGINS + _EXTRA


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="HealthIQ API",
    description="AI-powered healthcare analytics platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ingest.router)
app.include_router(risk.router)
app.include_router(nlp.router)
app.include_router(operations.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(patients.router)
