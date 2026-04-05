"""
risk_engine.py
RiskEngine — converts AI check results into a final risk score and alert list.

Scoring philosophy
──────────────────
Each of the three check domains contributes a weighted sub-score (0–100).
The final score is a weighted average of all three.

  Domain               Max weight   Rationale
  ───────────────────  ──────────   ──────────────────────────────────────────
  Diagnosis mismatch   40 pts       Wrong diagnosis can cascade into every
                                    subsequent clinical decision.
  Drug interaction     35 pts       Severe drug-drug interactions are acutely
                                    life-threatening.
  Lab abnormality      25 pts       Abnormal labs are serious but less
                                    immediately decisive than the above two.

Final score → Risk level mapping
  0–24   → LOW
  25–49  → MODERATE
  50–74  → HIGH
  75–100 → CRITICAL
"""

import logging
from app.schemas import Alert, AlertType, RiskLevel

logger = logging.getLogger(__name__)

# ─── Weight constants ─────────────────────────────────────────────────────────
WEIGHT_DIAGNOSIS  = 40
WEIGHT_DRUG       = 35
WEIGHT_LAB        = 25

# ─── Severity → multiplier for drug interactions ──────────────────────────────
DRUG_SEVERITY_MULTIPLIER = {
    "none":     0.0,
    "mild":     0.3,
    "moderate": 0.65,
    "severe":   1.0,
}


class RiskEngine:
    """
    Stateless engine that converts raw AI check results into a risk score,
    risk level, and a list of actionable alerts.
    """

    # ─── Sub-scorers ──────────────────────────────────────────────────────────

    def _score_diagnosis(self, dx_result: dict) -> tuple[float, Alert | None]:
        """
        Score the diagnosis check.
        Uses both the mismatch flag and the model's confidence.

        Returns (sub_score_0_to_100, optional_alert)
        """
        if not dx_result.get("mismatch", False):
            return 0.0, None

        # Scale by confidence (e.g. 0.9 confidence mismatch → 90 pts)
        confidence = float(dx_result.get("confidence", 0.5))
        sub_score  = round(confidence * 100, 1)

        alert = Alert(
            type=AlertType.DIAGNOSIS_MISMATCH,
            message=dx_result.get("reason", "Symptom-diagnosis mismatch detected."),
            recommended_action=dx_result.get("recommended_action", "Consult a specialist."),
        )
        return sub_score, alert

    def _score_drug_interaction(self, drug_result: dict) -> tuple[float, Alert | None]:
        """
        Score the drug interaction check.
        Maps the severity string to a multiplier × 100.

        Returns (sub_score_0_to_100, optional_alert)
        """
        if not drug_result.get("interactions_found", False):
            return 0.0, None

        severity   = drug_result.get("severity", "none")
        multiplier = DRUG_SEVERITY_MULTIPLIER.get(severity, 0.0)
        sub_score  = round(multiplier * 100, 1)

        if sub_score == 0.0:
            return 0.0, None

        alert = Alert(
            type=AlertType.DRUG_INTERACTION,
            message=drug_result.get("details", "Drug interaction detected."),
            recommended_action=drug_result.get("recommended_action", "Consult a pharmacist."),
        )
        return sub_score, alert

    def _score_lab_analysis(self, lab_result: dict) -> tuple[float, Alert | None]:
        """
        Score the lab analysis check.
        Score increases with the number of critical findings.

        Scoring:
          - Each 'critical_*' finding adds 30 pts (capped at 100)
          - Each 'high' or 'low' finding adds 15 pts (capped at 100)
          - Base 20 pts if any abnormalities exist at all

        Returns (sub_score_0_to_100, optional_alert)
        """
        if not lab_result.get("abnormalities_found", False):
            return 0.0, None

        findings  = lab_result.get("findings", [])
        sub_score = 20.0  # base score for having any abnormality

        for finding in findings:
            status = finding.get("status", "normal")
            if status in ("critical_low", "critical_high"):
                sub_score += 30
            elif status in ("low", "high"):
                sub_score += 15

        sub_score = min(sub_score, 100.0)  # cap at 100

        try:
            alert = Alert(
                type=AlertType.LAB_ABNORMALITY,
                message=str(self._format_lab_message(findings)),
                recommended_action=str(
                    lab_result.get("recommended_action", "Review labs with clinician.")
                ),
            )
        except Exception as e:
            print("ALERT ERROR:", e)
            alert = None
        return sub_score, alert

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _format_lab_message(findings: list[dict]) -> str:
        """Build a concise message listing all abnormal findings."""
        abnormal = [f for f in findings if f.get("status", "normal") != "normal"]
        if not abnormal:
            return "Lab abnormalities detected."

        parts = []
        for f in abnormal:
            marker = f.get("marker", "Unknown")
            status = f.get("status", "").replace("_", " ").capitalize()
            note   = f.get("note", "")
            parts.append(f"{marker} ({status}): {note}")

        return " | ".join(parts)

    @staticmethod
    def _score_to_risk_level(score: float) -> RiskLevel:
        """Map a 0–100 weighted score to a RiskLevel enum."""
        if score < 25:
            return RiskLevel.LOW
        elif score < 50:
            return RiskLevel.MODERATE
        elif score < 75:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    # ─── Main entry point ─────────────────────────────────────────────────────

    def evaluate(
        self,
        dx_result:   dict,
        drug_result: dict,
        lab_result:  dict,
    ) -> tuple[RiskLevel, list[Alert]]:
        """
        Combine the three AI check results into a final risk assessment.

        Args:
            dx_result   : Output of MedGuardAgent.run_diagnosis_check()
            drug_result : Output of MedGuardAgent.run_drug_interaction_check()
            lab_result  : Output of MedGuardAgent.run_lab_analysis()

        Returns:
            (risk_level, alerts)
        """
        # Score each domain independently
        dx_score,   dx_alert   = self._score_diagnosis(dx_result)
        drug_score, drug_alert = self._score_drug_interaction(drug_result)
        lab_score,  lab_alert  = self._score_lab_analysis(lab_result)

        logger.debug(
            "Sub-scores — Diagnosis: %.1f | Drug: %.1f | Lab: %.1f",
            dx_score, drug_score, lab_score,
        )

        # Weighted final score
        final_score = (
            (dx_score   * WEIGHT_DIAGNOSIS)
            + (drug_score * WEIGHT_DRUG)
            + (lab_score  * WEIGHT_LAB)
        ) / 100.0

        logger.info("Final risk score: %.2f", final_score)

        risk_level = self._score_to_risk_level(final_score)
        alerts = []
        for a in [dx_alert, drug_alert, lab_alert]:
            if a is not None:
                alerts.append(a)

        return risk_level, alerts