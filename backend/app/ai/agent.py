import json
import logging
from app.schemas import CaseInput

logger = logging.getLogger(__name__)

JSON_ONLY = "Respond ONLY with valid JSON. No preamble, no markdown, no explanation."


class MedGuardAgent:
    def __init__(self, client):
        self.client = client

    # ─── Helper ──────────────────────────────────────────────

    async def _call_groq(self, system_prompt: str, user_message: str) -> dict:
        try:
            print("\n🚀 CALLING GROQ...")

            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )

            raw = response.choices[0].message.content
            print("✅ RAW RESPONSE:", raw)

            return json.loads(raw)

        except Exception as exc:
            print("❌ GROQ ERROR:", exc)

            return {
                "abnormalities_found": False,
                "findings": [],
                "recommended_action": "AI unavailable — fallback used"
            }

    # ─── Diagnosis Check ─────────────────────────────────────

    async def run_diagnosis_check(self, case: CaseInput) -> dict:
        system_prompt = f"""You are a clinical decision-support AI.
Evaluate whether symptoms match the diagnosis.

Return JSON:
mismatch, confidence, reason, recommended_action

{JSON_ONLY}"""

        user_message = f"""
Age: {case.age}
Gender: {case.gender}
Symptoms: {', '.join(case.symptoms)}
Diagnosis: {case.diagnosis}
"""

        result = await self._call_groq(system_prompt, user_message)

        return {
            "mismatch": result.get("mismatch", False),
            "confidence": float(result.get("confidence", 0)),
            "reason": result.get("reason", ""),
            "recommended_action": result.get("recommended_action", ""),
        }

    # ─── Drug Check ──────────────────────────────────────────

    async def run_drug_interaction_check(self, case: CaseInput) -> dict:
        if not case.medications:
            return {
                "interactions_found": False,
                "severity": "none",
                "details": "No medications listed",
                "recommended_action": "None",
            }

        system_prompt = f"""Analyze drug interactions.

Return JSON:
interactions_found, severity, details, recommended_action

{JSON_ONLY}"""

        user_message = f"""
Medications: {', '.join(case.medications)}
"""

        result = await self._call_groq(system_prompt, user_message)

        return {
            "interactions_found": result.get("interactions_found", False),
            "severity": result.get("severity", "none"),
            "details": result.get("details", ""),
            "recommended_action": result.get("recommended_action", ""),
        }

    # ─── Lab Analysis (HYBRID AI + RULE ENGINE) ──────────────

    async def run_lab_analysis(self, case: CaseInput) -> dict:
        labs = case.lab_results

        ai_result = await self._call_groq(
            f"""You are a clinical lab expert.
            Provide a concise recommended_action based on abnormal lab values.

            Return JSON:
            recommended_action

            {JSON_ONLY}""",
            f"Labs: {labs}"
        )

        # STEP 2: RULE ENGINE (truth layer)
        findings = []

        def evaluate(marker, value, low, high):
            if value < low:
                return {
                    "marker": marker,
                    "status": "critical_low" if value < low * 0.75 else "low",
                    "note": f"{marker} is below normal range"
                }
            elif value > high:
                return {
                    "marker": marker,
                    "status": "critical_high" if value > high * 1.25 else "high",
                    "note": f"{marker} is above normal range"
                }
            else:
                return {
                    "marker": marker,
                    "status": "normal",
                    "note": f"{marker} is normal"
                }

        findings.append(evaluate("Hemoglobin", labs.hemoglobin, 12, 17.5))
        findings.append(evaluate("WBC", labs.WBC, 4500, 11000))
        findings.append(evaluate("Platelets", labs.platelets, 150000, 400000))
        findings.append(evaluate("Blood Sugar", labs.blood_sugar, 70, 99))
        findings.append(evaluate("Cholesterol", labs.cholesterol, 0, 200))

        # STEP 3: critical count
        critical_count = sum(1 for f in findings if "critical" in f["status"])

        # STEP 4: AI recommendation (safe usage)
        recommended_action = ai_result.get(
            "recommended_action",
            "Consult clinician for abnormal labs"
        )

        return {
            "abnormalities_found": any(f["status"] != "normal" for f in findings),
            "critical_count": critical_count,
            "findings": findings,
            "recommended_action": recommended_action,
        }