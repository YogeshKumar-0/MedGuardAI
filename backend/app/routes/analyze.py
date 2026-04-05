import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request

from app.schemas import CaseInput, CaseAnalysisResponse
from app.ai.agent import MedGuardAgent
from app.services.risk_engine import RiskEngine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/analyze-case",
    response_model=CaseAnalysisResponse,
)
async def analyze_case(case: CaseInput, request: Request) -> CaseAnalysisResponse:

    logger.info(
        "Received case: age=%d, gender=%s, diagnosis=%s",
        case.age, case.gender, case.diagnosis,
    )

    agent: MedGuardAgent = request.app.state.agent
    engine: RiskEngine = request.app.state.risk_engine

    # ─────────────────────────────────────────────
    # 1. RUN AI (PARALLEL)
    # ─────────────────────────────────────────────
    try:
        dx_result, drug_result, lab_result = await asyncio.gather(
            agent.run_diagnosis_check(case),
            agent.run_drug_interaction_check(case),
            agent.run_lab_analysis(case),
        )
    except Exception as exc:
        logger.exception("AI analysis failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI analysis service is temporarily unavailable.",
        )

    # ─────────────────────────────────────────────
    # 2. DEBUG LOGS (CRITICAL FOR DEBUGGING)
    # ─────────────────────────────────────────────
    logger.error("DX RESULT: %s", dx_result)
    logger.error("DRUG RESULT: %s", drug_result)
    logger.error("LAB RESULT: %s", lab_result)

    # ─────────────────────────────────────────────
    # 3. SAFETY NORMALIZATION (THIS FIXES YOUR BUG)
    # ─────────────────────────────────────────────

    # Ensure lab_result is valid
    if not isinstance(lab_result, dict):
        lab_result = {}

    # Ensure findings is always a list
    findings = lab_result.get("findings")
    if not isinstance(findings, list):
        lab_result["findings"] = []

    # Ensure abnormalities flag exists
    if "abnormalities_found" not in lab_result:
        lab_result["abnormalities_found"] = False

    # Optional: normalize dx_result & drug_result too
    if not isinstance(dx_result, dict):
        dx_result = {}

    if not isinstance(drug_result, dict):
        drug_result = {}

    # ─────────────────────────────────────────────
    # 4. RISK ENGINE (SAFE NOW)
    # ─────────────────────────────────────────────
    try:
        risk_level, alerts = engine.evaluate(dx_result, drug_result, lab_result)
    except Exception as exc:
        logger.exception("Risk engine failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=str(exc),   # 🔥 SHOW REAL ERROR
        )

    logger.info(
        "Risk assessment complete: level=%s, alerts=%d",
        risk_level,
        len(alerts),
    )

    return CaseAnalysisResponse(
        risk_level=risk_level,
        alerts=alerts
    )