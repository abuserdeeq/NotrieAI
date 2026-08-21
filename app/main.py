import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.admin_routes import router as admin_router
from app.auth_routes import router as auth_router
from app.rate_limit import limiter
from app.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Rotryai Explain API")

# Rate limiting - protects /auth/login and /auth/signup from brute-force
# and spam signups, and /api/explain from being hammered (each call costs
# real money via the OpenAI/Gemini API). See app/rate_limit.py.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Comma-separated list of allowed frontend origins, e.g.:
# ALLOWED_ORIGINS=https://notrieai-frontend.onrender.com,https://notrieai.com
# Falls back to the known Render frontend URL + localhost for local dev
# if the env var isn't set, so nothing breaks if you forget to set it.
_default_origins = [
    "https://notrieai-frontend.onrender.com",
    "https://notrieai.vercel.app",
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
app.include_router(auth_router, prefix="/api/auth")
app.include_router(admin_router, prefix="/api/admin")

