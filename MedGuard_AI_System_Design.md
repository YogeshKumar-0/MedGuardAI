# MedGuard AI — Full System Design

> Production-level AI system for medical error detection.  
> Stack: FastAPI · Next.js · OpenAI GPT-4o · PostgreSQL · Redis

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                        │
│           Next.js 14 (App Router) + Tailwind            │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS / REST / JSON
┌─────────────────────▼───────────────────────────────────┐
│                  API GATEWAY LAYER                       │
│     FastAPI · JWT Auth · Rate Limiting · CORS           │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│Diagnosis │  Drug    │  Lab     │  Risk    │  AI Agent   │
│ Engine   │  Check   │ Analysis │ Scoring  │ Orchestrator│
└──────────┴──────────┴──────────┴──────────┴──────┬──────┘
      │                                             │
      │  SQL                              OpenAI API│
┌─────▼──────────┐   ┌─────────────┐   ┌──────────▼──────┐
│  PostgreSQL 16 │   │ Redis Cache │   │   GPT-4o (LLM)  │
│  Primary Store │   │ Sess + Drug │   │  Structured Out  │
└────────────────┘   └─────────────┘   └─────────────────┘
```

---

## 2. Backend Modules (FastAPI / Python)

### 2.1 Auth Module (`app/auth/`)

Handles doctor registration, login, JWT issuance, and RBAC.

```python
# app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import service, schemas
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register", response_model=schemas.DoctorOut, status_code=201)
async def register(payload: schemas.DoctorCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_doctor(db, payload)

@router.post("/login", response_model=schemas.TokenPair)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    doctor = await service.authenticate(db, form.username, form.password)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return service.issue_tokens(doctor)

@router.post("/refresh", response_model=schemas.TokenPair)
async def refresh(token: str, db: AsyncSession = Depends(get_db)):
    return await service.refresh_tokens(db, token)
```

```python
# app/auth/service.py
import bcrypt, jwt
from datetime import datetime, timedelta
from app.core.config import settings

ACCESS_TTL  = timedelta(minutes=30)
REFRESH_TTL = timedelta(days=7)

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())

def issue_tokens(doctor) -> dict:
    payload = {"sub": str(doctor.id), "role": doctor.role}
    access  = jwt.encode({**payload, "exp": datetime.utcnow() + ACCESS_TTL},  settings.SECRET_KEY, "HS256")
    refresh = jwt.encode({**payload, "exp": datetime.utcnow() + REFRESH_TTL}, settings.SECRET_KEY, "HS256")
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
```

---

### 2.2 Diagnosis Engine (`app/diagnosis/`)

Detects mismatches between reported symptoms and the given diagnosis, and suggests a differential diagnosis list.

```python
# app/diagnosis/service.py
from app.ai.agent import MedGuardAgent
from app.db.models import DiagnosisRecord
from sqlalchemy.ext.asyncio import AsyncSession

async def analyze_diagnosis(db: AsyncSession, payload: dict) -> dict:
    agent  = MedGuardAgent()
    result = await agent.run_diagnosis_check(
        symptoms   = payload["symptoms"],
        diagnosis  = payload["diagnosis"],
        patient_id = payload["patient_id"],
    )
    record = DiagnosisRecord(
        patient_id         = payload["patient_id"],
        reported_diagnosis = payload["diagnosis"],
        ai_verdict         = result["verdict"],
        ddx_list           = result["differential"],
        confidence_score   = result["confidence"],
        mismatch_detected  = result["mismatch"],
    )
    db.add(record)
    await db.commit()
    return result
```

---

### 2.3 Drug Interaction Module (`app/drugs/`)

Cross-checks prescribed medications against a known interaction database and uses AI to assess severity.

```python
# app/drugs/service.py
from app.ai.agent import MedGuardAgent
from app.db.models import DrugInteractionAlert
from app.cache.redis_client import redis_client
import json

CACHE_TTL = 3600  # 1 hour

async def check_interactions(db, patient_id: str, medications: list[str]) -> dict:
    cache_key = f"drug_check:{':'.join(sorted(medications))}"
    cached    = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    agent  = MedGuardAgent()
    result = await agent.run_drug_interaction_check(medications)

    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))

    for interaction in result.get("interactions", []):
        alert = DrugInteractionAlert(
            patient_id   = patient_id,
            drug_a       = interaction["drug_a"],
            drug_b       = interaction["drug_b"],
            severity     = interaction["severity"],      # LOW / MODERATE / HIGH / CRITICAL
            mechanism    = interaction["mechanism"],
            recommendation = interaction["recommendation"],
        )
        db.add(alert)

    await db.commit()
    return result
```

---

### 2.4 Lab Report Analysis (`app/labs/`)

Parses structured lab data, flags abnormal values, and recommends follow-up tests.

```python
# app/labs/service.py
from app.ai.agent import MedGuardAgent
from app.db.models import LabReport, LabFlag

async def analyze_lab_report(db, patient_id: str, lab_data: dict) -> dict:
    agent  = MedGuardAgent()
    result = await agent.run_lab_analysis(
        lab_results = lab_data["results"],   # list of {test, value, unit, ref_range}
        diagnosis   = lab_data.get("diagnosis"),
        patient_age = lab_data.get("age"),
        patient_sex = lab_data.get("sex"),
    )

    report = LabReport(
        patient_id        = patient_id,
        raw_results       = lab_data["results"],
        abnormal_count    = result["abnormal_count"],
        critical_count    = result["critical_count"],
        missing_tests     = result["missing_tests"],
        ai_interpretation = result["interpretation"],
    )
    db.add(report)

    for flag in result.get("flags", []):
        db.add(LabFlag(
            report_id  = report.id,
            test_name  = flag["test"],
            value      = flag["value"],
            ref_range  = flag["ref_range"],
            severity   = flag["severity"],
            note       = flag["note"],
        ))

    await db.commit()
    return result
```

---

### 2.5 Risk Scoring Engine (`app/risk/`)

Aggregates outputs from all analysis modules into a single patient risk index (0–100).

```python
# app/risk/service.py
from app.db.models import RiskAssessment

WEIGHTS = {
    "diagnosis_mismatch": 30,
    "drug_critical":      25,
    "drug_moderate":      15,
    "lab_critical":       20,
    "lab_abnormal":        5,
    "missing_tests":       5,
}

async def compute_risk_score(db, patient_id: str, analysis_results: dict) -> dict:
    r   = analysis_results
    raw = 0

    if r["diagnosis"]["mismatch"]:
        raw += WEIGHTS["diagnosis_mismatch"]

    for interaction in r["drugs"].get("interactions", []):
        if interaction["severity"] == "CRITICAL":
            raw += WEIGHTS["drug_critical"]
        elif interaction["severity"] in ("HIGH", "MODERATE"):
            raw += WEIGHTS["drug_moderate"]

    raw += min(r["labs"]["critical_count"] * WEIGHTS["lab_critical"], 40)
    raw += min(r["labs"]["abnormal_count"] * WEIGHTS["lab_abnormal"], 15)
    raw += min(len(r["labs"]["missing_tests"]) * WEIGHTS["missing_tests"], 10)

    score = min(raw, 100)
    level = "CRITICAL" if score >= 75 else "HIGH" if score >= 50 else "MODERATE" if score >= 25 else "LOW"

    record = RiskAssessment(
        patient_id   = patient_id,
        score        = score,
        level        = level,
        contributing_factors = analysis_results,
    )
    db.add(record)
    await db.commit()
    return {"score": score, "level": level}
```

---

### 2.6 AI Agent (`app/ai/`)

Central orchestrator that calls OpenAI with structured system prompts and parses JSON responses.

```python
# app/ai/agent.py
import json
from openai import AsyncOpenAI
from app.core.config import settings
from app.ai import prompts

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
MODEL  = "gpt-4o"

class MedGuardAgent:

    async def _call(self, system_prompt: str, user_message: str) -> dict:
        response = await client.chat.completions.create(
            model       = MODEL,
            temperature = 0.1,
            response_format = {"type": "json_object"},
            messages    = [
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_message},
            ],
        )
        return json.loads(response.choices[0].message.content)

    async def run_diagnosis_check(self, symptoms: list, diagnosis: str, patient_id: str) -> dict:
        user_msg = f"Symptoms: {', '.join(symptoms)}\nReported diagnosis: {diagnosis}"
        return await self._call(prompts.DIAGNOSIS_SYSTEM, user_msg)

    async def run_drug_interaction_check(self, medications: list) -> dict:
        user_msg = f"Medications: {', '.join(medications)}"
        return await self._call(prompts.DRUG_SYSTEM, user_msg)

    async def run_lab_analysis(self, lab_results: list, diagnosis: str, patient_age: int, patient_sex: str) -> dict:
        user_msg = json.dumps({
            "lab_results": lab_results,
            "context": {"diagnosis": diagnosis, "age": patient_age, "sex": patient_sex}
        })
        return await self._call(prompts.LAB_SYSTEM, user_msg)
```

```python
# app/ai/prompts.py

DIAGNOSIS_SYSTEM = """
You are a senior clinical AI assistant specialised in medical error detection.
Given a list of patient symptoms and a reported diagnosis, you must:
1. Assess whether the diagnosis is consistent with the symptoms.
2. Provide a differential diagnosis list (DDx) ordered by likelihood.
3. Rate your confidence from 0.0 to 1.0.

Return ONLY valid JSON in this exact schema:
{
  "mismatch": true|false,
  "verdict": "string — one sentence explanation",
  "differential": [
    {"condition": "string", "likelihood": "HIGH|MODERATE|LOW", "reasoning": "string"}
  ],
  "confidence": 0.0–1.0,
  "urgency": "ROUTINE|URGENT|EMERGENCY"
}
"""

DRUG_SYSTEM = """
You are a clinical pharmacology AI. Given a list of medications, identify all
drug-drug interactions. For each pair report severity and actionable recommendation.

Return ONLY valid JSON:
{
  "interactions": [
    {
      "drug_a": "string",
      "drug_b": "string",
      "severity": "LOW|MODERATE|HIGH|CRITICAL",
      "mechanism": "string",
      "effect": "string",
      "recommendation": "string"
    }
  ],
  "safe_to_co_prescribe": true|false,
  "summary": "string"
}
"""

LAB_SYSTEM = """
You are a clinical laboratory AI. Given structured lab results with reference ranges,
patient age, sex, and current diagnosis:
1. Flag abnormal and critical values.
2. Recommend missing tests based on clinical context.
3. Provide a concise clinical interpretation.

Return ONLY valid JSON:
{
  "flags": [
    {
      "test": "string",
      "value": "string",
      "ref_range": "string",
      "severity": "NORMAL|MILDLY_ABNORMAL|ABNORMAL|CRITICAL",
      "note": "string"
    }
  ],
  "abnormal_count": 0,
  "critical_count": 0,
  "missing_tests": ["string"],
  "interpretation": "string"
}
"""
```

---

## 3. Frontend Modules (Next.js 14)

### 3.1 Dashboard Page (`/app/dashboard/page.tsx`)

```tsx
// app/dashboard/page.tsx
import { PatientSummaryCard } from "@/components/PatientSummaryCard";
import { ActiveAlertsBanner }  from "@/components/ActiveAlertsBanner";
import { RiskScoreGauge }      from "@/components/RiskScoreGauge";
import { AnalysisTimeline }    from "@/components/AnalysisTimeline";

export default async function Dashboard() {
  return (
    <div className="grid grid-cols-12 gap-6 p-6">
      <div className="col-span-12">
        <ActiveAlertsBanner />
      </div>
      <div className="col-span-8 space-y-6">
        <PatientSummaryCard />
        <AnalysisTimeline />
      </div>
      <div className="col-span-4 space-y-6">
        <RiskScoreGauge />
      </div>
    </div>
  );
}
```

### 3.2 Case Submission Form (`/app/cases/new/page.tsx`)

```tsx
// components/CaseSubmissionForm.tsx
"use client";
import { useState } from "react";
import { useMutation }   from "@tanstack/react-query";
import { submitCase }    from "@/lib/api";
import { Button, Badge } from "@/components/ui";
import { AlertPanel }    from "@/components/AlertPanel";

export function CaseSubmissionForm() {
  const [form, setForm] = useState({
    patientId:   "",
    symptoms:    [] as string[],
    diagnosis:   "",
    medications: [] as string[],
    labResults:  [] as object[],
  });

  const mutation = useMutation({
    mutationFn: submitCase,
    onSuccess: (data) => {
      // Trigger real-time alert display
    },
  });

  return (
    <form className="space-y-6 max-w-3xl mx-auto p-6">
      <SymptomTagInput
        value={form.symptoms}
        onChange={(s) => setForm({ ...form, symptoms: s })}
      />
      <DiagnosisInput
        value={form.diagnosis}
        onChange={(d) => setForm({ ...form, diagnosis: d })}
      />
      <MedicationList
        value={form.medications}
        onChange={(m) => setForm({ ...form, medications: m })}
      />
      <LabResultsUploader
        onChange={(l) => setForm({ ...form, labResults: l })}
      />
      <Button
        onClick={() => mutation.mutate(form)}
        loading={mutation.isPending}
        className="w-full bg-blue-600 text-white"
      >
        Analyse Case
      </Button>
      {mutation.data && <AlertPanel results={mutation.data} />}
    </form>
  );
}
```

### 3.3 Risk Score Gauge Component

```tsx
// components/RiskScoreGauge.tsx
"use client";
type Level = "LOW" | "MODERATE" | "HIGH" | "CRITICAL";

const COLORS: Record<Level, string> = {
  LOW:      "text-green-600",
  MODERATE: "text-yellow-500",
  HIGH:     "text-orange-500",
  CRITICAL: "text-red-600",
};

export function RiskScoreGauge({ score, level }: { score: number; level: Level }) {
  const pct = score / 100;
  return (
    <div className="rounded-2xl border border-zinc-200 p-6 shadow-sm">
      <p className="text-sm font-medium text-zinc-500 mb-3">Patient Risk Index</p>
      <div className="relative h-4 rounded-full bg-zinc-100 overflow-hidden">
        <div
          className="absolute left-0 top-0 h-full rounded-full transition-all duration-700"
          style={{ width: `${score}%`, background: score >= 75 ? "#dc2626" : score >= 50 ? "#f97316" : score >= 25 ? "#eab308" : "#16a34a" }}
        />
      </div>
      <div className="flex justify-between mt-3">
        <span className={`text-3xl font-bold ${COLORS[level]}`}>{score}</span>
        <span className={`text-sm font-semibold uppercase tracking-wide self-end ${COLORS[level]}`}>
          {level}
        </span>
      </div>
    </div>
  );
}
```

### 3.4 Drug Interaction Alert Panel

```tsx
// components/DrugAlertPanel.tsx
"use client";
const SEVERITY_STYLE = {
  CRITICAL: "bg-red-50 border-red-300 text-red-800",
  HIGH:     "bg-orange-50 border-orange-300 text-orange-800",
  MODERATE: "bg-yellow-50 border-yellow-300 text-yellow-800",
  LOW:      "bg-blue-50 border-blue-300 text-blue-700",
};

export function DrugAlertPanel({ interactions }: { interactions: any[] }) {
  if (!interactions.length) return (
    <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-green-700 text-sm">
      No drug interactions detected.
    </div>
  );
  return (
    <div className="space-y-3">
      {interactions.map((i, idx) => (
        <div key={idx} className={`rounded-xl border p-4 ${SEVERITY_STYLE[i.severity]}`}>
          <div className="flex justify-between items-start">
            <p className="font-semibold">{i.drug_a} + {i.drug_b}</p>
            <span className="text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded-full border">
              {i.severity}
            </span>
          </div>
          <p className="text-sm mt-1">{i.mechanism}</p>
          <p className="text-xs mt-2 opacity-80">Recommendation: {i.recommendation}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## 4. AI Agent Workflow

```
Doctor submits: symptoms + diagnosis + medications + lab results
        │
        ▼
FastAPI orchestrator receives POST /api/v1/cases/analyze
        │
        ├─► Diagnosis Engine
        │      ├─ Build prompt with symptoms + diagnosis
        │      ├─ Call GPT-4o (json_object mode)
        │      └─ Parse: mismatch, DDx, confidence, urgency
        │
        ├─► Drug Interaction Engine
        │      ├─ Check Redis cache (medication combo key)
        │      ├─ On miss: call GPT-4o with medication list
        │      └─ Parse: interactions[], severity, recommendation
        │
        ├─► Lab Analysis Engine
        │      ├─ Build prompt with lab values + reference ranges
        │      ├─ Call GPT-4o with patient context
        │      └─ Parse: flags[], missing_tests[], interpretation
        │
        └─► All results merged
               │
               ▼
        Risk Scoring Engine
               ├─ Weight each signal by clinical priority
               ├─ Sum capped at 100
               └─ Classify: LOW / MODERATE / HIGH / CRITICAL
                      │
                      ▼
               Save to PostgreSQL
               Emit WebSocket event to frontend
               Return structured JSON response
```

The four AI sub-chains run **concurrently** using `asyncio.gather()`:

```python
# app/cases/service.py
import asyncio
from app.diagnosis.service import analyze_diagnosis
from app.drugs.service     import check_interactions
from app.labs.service      import analyze_lab_report
from app.risk.service      import compute_risk_score

async def analyze_full_case(db, patient_id: str, payload: dict) -> dict:
    diag_task, drug_task, lab_task = await asyncio.gather(
        analyze_diagnosis(db, {**payload, "patient_id": patient_id}),
        check_interactions(db, patient_id, payload["medications"]),
        analyze_lab_report(db, patient_id, payload["lab_data"]),
    )

    risk = await compute_risk_score(db, patient_id, {
        "diagnosis": diag_task,
        "drugs":     drug_task,
        "labs":      lab_task,
    })

    return {
        "patient_id":   patient_id,
        "diagnosis":    diag_task,
        "drug_alerts":  drug_task,
        "lab_analysis": lab_task,
        "risk":         risk,
    }
```

---

## 5. Database Schema (PostgreSQL)

```sql
-- Doctors / users
CREATE TABLE doctors (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        VARCHAR(255) UNIQUE NOT NULL,
    name         VARCHAR(255) NOT NULL,
    specialty    VARCHAR(100),
    password_hash TEXT NOT NULL,
    role         VARCHAR(20) DEFAULT 'doctor',  -- doctor | admin
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Patients
CREATE TABLE patients (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id    UUID REFERENCES doctors(id) ON DELETE CASCADE,
    mrn          VARCHAR(100) UNIQUE,            -- Medical Record Number
    name         VARCHAR(255) NOT NULL,
    dob          DATE,
    sex          CHAR(1),                        -- M | F | O
    blood_type   VARCHAR(5),
    allergies    TEXT[],
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Full case analysis records
CREATE TABLE case_analyses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id   UUID REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id    UUID REFERENCES doctors(id),
    symptoms     TEXT[],
    diagnosis    TEXT,
    medications  TEXT[],
    status       VARCHAR(20) DEFAULT 'pending',  -- pending | completed | failed
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Diagnosis mismatch records
CREATE TABLE diagnosis_records (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id            UUID REFERENCES case_analyses(id) ON DELETE CASCADE,
    patient_id         UUID REFERENCES patients(id),
    reported_diagnosis TEXT NOT NULL,
    ai_verdict         TEXT,
    ddx_list           JSONB,                   -- [{condition, likelihood, reasoning}]
    mismatch_detected  BOOLEAN DEFAULT FALSE,
    confidence_score   DECIMAL(4,3),
    urgency            VARCHAR(20),             -- ROUTINE | URGENT | EMERGENCY
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- Drug interaction alerts
CREATE TABLE drug_interaction_alerts (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id        UUID REFERENCES case_analyses(id) ON DELETE CASCADE,
    patient_id     UUID REFERENCES patients(id),
    drug_a         VARCHAR(200) NOT NULL,
    drug_b         VARCHAR(200) NOT NULL,
    severity       VARCHAR(20) NOT NULL,        -- LOW | MODERATE | HIGH | CRITICAL
    mechanism      TEXT,
    effect         TEXT,
    recommendation TEXT,
    acknowledged   BOOLEAN DEFAULT FALSE,
    ack_by         UUID REFERENCES doctors(id),
    ack_at         TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Lab reports
CREATE TABLE lab_reports (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID REFERENCES case_analyses(id) ON DELETE CASCADE,
    patient_id        UUID REFERENCES patients(id),
    raw_results       JSONB NOT NULL,           -- [{test, value, unit, ref_range}]
    abnormal_count    INTEGER DEFAULT 0,
    critical_count    INTEGER DEFAULT 0,
    missing_tests     TEXT[],
    ai_interpretation TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Individual lab flags
CREATE TABLE lab_flags (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id   UUID REFERENCES lab_reports(id) ON DELETE CASCADE,
    test_name   VARCHAR(200) NOT NULL,
    value       VARCHAR(100),
    ref_range   VARCHAR(100),
    severity    VARCHAR(30),                    -- NORMAL | MILDLY_ABNORMAL | ABNORMAL | CRITICAL
    note        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Risk assessments
CREATE TABLE risk_assessments (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id               UUID REFERENCES case_analyses(id) ON DELETE CASCADE,
    patient_id            UUID REFERENCES patients(id),
    score                 INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    level                 VARCHAR(20) NOT NULL,  -- LOW | MODERATE | HIGH | CRITICAL
    contributing_factors  JSONB,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_cases_patient    ON case_analyses(patient_id);
CREATE INDEX idx_cases_doctor     ON case_analyses(doctor_id);
CREATE INDEX idx_alerts_severity  ON drug_interaction_alerts(severity);
CREATE INDEX idx_alerts_patient   ON drug_interaction_alerts(patient_id);
CREATE INDEX idx_risk_level       ON risk_assessments(level);
CREATE INDEX idx_risk_score       ON risk_assessments(score DESC);
CREATE INDEX idx_lab_critical     ON lab_flags(severity) WHERE severity = 'CRITICAL';
```

---

## 6. API Endpoints

### Auth
| Method | Path               | Description              | Auth |
|--------|--------------------|--------------------------|------|
| POST   | /auth/register     | Register new doctor      | —    |
| POST   | /auth/login        | Login, receive JWT pair  | —    |
| POST   | /auth/refresh      | Refresh access token     | —    |
| DELETE | /auth/logout       | Invalidate refresh token | ✓    |

### Patients
| Method | Path                        | Description                 | Auth |
|--------|-----------------------------|-----------------------------|------|
| POST   | /api/v1/patients            | Create patient record       | ✓    |
| GET    | /api/v1/patients            | List doctor's patients      | ✓    |
| GET    | /api/v1/patients/{id}       | Get patient detail          | ✓    |
| PATCH  | /api/v1/patients/{id}       | Update patient record       | ✓    |

### Case Analysis (Core)
| Method | Path                            | Description                  | Auth |
|--------|---------------------------------|------------------------------|------|
| POST   | /api/v1/cases/analyze           | Submit and run full analysis | ✓    |
| GET    | /api/v1/cases/{id}              | Get case analysis result     | ✓    |
| GET    | /api/v1/cases?patient_id={id}   | List cases for a patient     | ✓    |

### Diagnosis
| Method | Path                                 | Description              | Auth |
|--------|--------------------------------------|--------------------------|------|
| POST   | /api/v1/diagnosis/check              | Check single diagnosis   | ✓    |
| GET    | /api/v1/diagnosis/{id}               | Get diagnosis result     | ✓    |
| GET    | /api/v1/diagnosis/patient/{pid}      | List patient diagnoses   | ✓    |

### Medications & Drug Interactions
| Method | Path                                 | Description              | Auth |
|--------|--------------------------------------|--------------------------|------|
| POST   | /api/v1/drugs/interactions           | Check drug combo         | ✓    |
| GET    | /api/v1/drugs/alerts/{patient_id}    | Get all drug alerts      | ✓    |
| PATCH  | /api/v1/drugs/alerts/{id}/acknowledge| Acknowledge alert        | ✓    |

### Lab Reports
| Method | Path                                 | Description              | Auth |
|--------|--------------------------------------|--------------------------|------|
| POST   | /api/v1/labs/analyze                 | Analyse lab report       | ✓    |
| GET    | /api/v1/labs/{id}                    | Get lab report           | ✓    |
| GET    | /api/v1/labs/patient/{pid}           | List patient lab reports | ✓    |

### Risk
| Method | Path                                 | Description              | Auth |
|--------|--------------------------------------|--------------------------|------|
| GET    | /api/v1/risk/{patient_id}            | Get current risk score   | ✓    |
| GET    | /api/v1/risk/{patient_id}/history    | Risk score over time     | ✓    |

### WebSocket
| Path                      | Description                           |
|---------------------------|---------------------------------------|
| /ws/alerts/{patient_id}   | Live alert stream for a patient case  |

---

## 7. Folder Structure

### Backend (`/backend`)

```
backend/
├── app/
│   ├── ai/
│   │   ├── agent.py           # MedGuardAgent class (OpenAI orchestrator)
│   │   └── prompts.py         # All system prompt templates
│   ├── auth/
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── cases/
│   │   ├── router.py          # POST /cases/analyze
│   │   └── service.py         # asyncio.gather orchestrator
│   ├── diagnosis/
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── drugs/
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── labs/
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── risk/
│   │   ├── router.py
│   │   └── service.py
│   ├── patients/
│   │   ├── router.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── db/
│   │   ├── session.py         # Async SQLAlchemy engine
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── migrations/        # Alembic migrations
│   ├── cache/
│   │   └── redis_client.py    # Redis async client
│   ├── websocket/
│   │   └── manager.py         # WebSocket connection manager
│   └── core/
│       ├── config.py          # Pydantic Settings (env vars)
│       ├── security.py        # JWT helpers
│       └── exceptions.py      # Global error handlers
├── main.py                    # FastAPI app factory
├── requirements.txt
├── Dockerfile
└── alembic.ini
```

### Frontend (`/frontend`)

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── dashboard/
│   │   └── page.tsx
│   ├── patients/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx
│   ├── cases/
│   │   ├── new/page.tsx       # Case submission form
│   │   └── [id]/page.tsx      # Case analysis result
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                    # Base components (Button, Badge, Input…)
│   ├── ActiveAlertsBanner.tsx
│   ├── AlertPanel.tsx
│   ├── AnalysisTimeline.tsx
│   ├── CaseSubmissionForm.tsx
│   ├── DiagnosisResultCard.tsx
│   ├── DrugAlertPanel.tsx
│   ├── LabFlagTable.tsx
│   ├── MedicationList.tsx
│   ├── PatientSummaryCard.tsx
│   ├── RiskScoreGauge.tsx
│   └── SymptomTagInput.tsx
├── lib/
│   ├── api.ts                 # Axios instance + typed API calls
│   ├── hooks/
│   │   ├── useCase.ts
│   │   ├── useAlerts.ts
│   │   └── useWebSocket.ts    # Live alert streaming
│   └── types.ts               # Shared TypeScript types
├── public/
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── Dockerfile
```

### Infrastructure (`/infra`)

```
infra/
├── docker-compose.yml         # Local dev: FastAPI + Next.js + PG + Redis
├── nginx/
│   └── nginx.conf             # Reverse proxy + SSL termination
└── k8s/                       # Kubernetes manifests (prod)
    ├── backend-deployment.yaml
    ├── frontend-deployment.yaml
    ├── postgres-statefulset.yaml
    ├── redis-deployment.yaml
    └── ingress.yaml
```

---

## 8. Data Flow

### Full Case Analysis Request

```
1.  Doctor fills form → CaseSubmissionForm.tsx
2.  POST /api/v1/cases/analyze  { patient_id, symptoms, diagnosis, medications, lab_data }
3.  FastAPI auth middleware validates JWT → extracts doctor_id
4.  cases/router.py → cases/service.analyze_full_case()
5.  asyncio.gather() fires 3 tasks concurrently:
      ├─ diagnosis/service.analyze_diagnosis()
      │     └─ ai/agent.run_diagnosis_check() → OpenAI GPT-4o → parse JSON
      ├─ drugs/service.check_interactions()
      │     ├─ redis_client.get(cache_key) → HIT? return cached
      │     └─ MISS → ai/agent.run_drug_interaction_check() → OpenAI → cache + return
      └─ labs/service.analyze_lab_report()
            └─ ai/agent.run_lab_analysis() → OpenAI GPT-4o → parse JSON
6.  All results → risk/service.compute_risk_score() → weighted sum → 0–100 index
7.  All records written to PostgreSQL in one transaction
8.  WebSocket manager pushes {event: "analysis_complete", payload} to /ws/alerts/{patient_id}
9.  HTTP 200 response with full analysis JSON returned to frontend
10. React state updated → AlertPanel, RiskScoreGauge, DrugAlertPanel re-render
```

### Real-time Alert Flow (WebSocket)

```
Doctor opens patient page
      │
      ▼
useWebSocket("ws://api/ws/alerts/{patient_id}") hook connects
      │
FastAPI WebSocket endpoint accepts connection
WebSocketManager.connect(patient_id, socket)
      │
      │ (another doctor submits case for same patient)
      │
cases/service completes analysis
      │
WebSocketManager.broadcast(patient_id, alert_payload)
      │
      ▼
Frontend receives message → toast notification + badge count update
```

---

## 9. Environment Variables

### Backend `.env`

```env
DATABASE_URL=postgresql+asyncpg://medguard:secret@localhost:5432/medguard_db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
SECRET_KEY=your-256-bit-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALLOWED_ORIGINS=http://localhost:3000,https://medguard.yourcompany.com
```

### Frontend `.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 10. Docker Compose (Local Dev)

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+asyncpg://medguard:secret@db:5432/medguard_db
      REDIS_URL: redis://redis:6379/0
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SECRET_KEY: ${SECRET_KEY}
    depends_on: [db, redis]
    volumes: ["./backend:/app"]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on: [backend]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: medguard_db
      POSTGRES_USER: medguard
      POSTGRES_PASSWORD: secret
    volumes: ["pg_data:/var/lib/postgresql/data"]
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pg_data:
```

---

## 11. Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Async Python | `asyncio` + `asyncpg` | Concurrent AI calls — 3× faster than sequential |
| AI output format | `json_object` response mode | Eliminates markdown parsing, guarantees schema |
| Drug caching | Redis with compound key | Identical drug combos share one AI call |
| Risk scoring | Rule-weighted sum, not AI | Deterministic, auditable, regulatorily defensible |
| Auth | JWT (access + refresh) | Stateless, fits microservice scaling |
| Real-time | WebSocket per patient_id | Targeted push, no polling overhead |
| DB | PostgreSQL + JSONB | Structured queries + flexible AI output storage |

---

*MedGuard AI — Designed for patient safety, built for clinical trust.*
