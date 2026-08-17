import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router

app = FastAPI(title="NotrieAI Explain API")

# Comma-separated list of allowed frontend origins, e.g.:
# ALLOWED_ORIGINS=https://notrieai-frontend.onrender.com,https://notrieai.com
# Falls back to the known Render frontend URL + localhost for local dev
# if the env var isn't set, so nothing breaks if you forget to set it.
_default_origins = [
    "https://notrieai-frontend.onrender.com",
    "http://localhost:5173",
]
_raw_origins = os.getenv("ALLOWED_ORIGINS")
allowed_origins = (
    [origin.strip() for origin in _raw_origins.split(",") if origin.strip()]
    if _raw_origins
    else _default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
