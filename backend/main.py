"""
main.py
MedGuard AI — FastAPI entry point (Groq version)
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from groq import Groq

from app.ai.agent import MedGuardAgent
from app.routes.analyze import router as analyze_router
from app.services.risk_engine import RiskEngine

# ─── Environment & Logging ────────────────────────────────────────────────────

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError("GROQ_API_KEY not found in .env")

client = Groq(api_key=api_key)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("medguard")


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising MedGuard AI with Groq (llama3-70b)...")

    app.state.agent = MedGuardAgent(client=client)
    app.state.risk_engine = RiskEngine()

    logger.info("MedGuard AI is ready.")
    yield

    logger.info("MedGuard AI shut down cleanly.")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MedGuard AI",
    description="AI-powered healthcare risk detection system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://medguardlive.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
app.include_router(analyze_router, prefix="/api/v1", tags=["Analysis"])


# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "MedGuard AI"}


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Unexpected error occurred"},
    )