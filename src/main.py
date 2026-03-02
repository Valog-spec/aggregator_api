from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from src.api.v1.health import router as health_router

app = FastAPI(title="Aggregator API")

app.include_router(health_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
