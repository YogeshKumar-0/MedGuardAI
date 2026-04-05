# MedGuard AI — Backend

AI-powered healthcare risk detection system built with FastAPI + OpenAI.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then add your OPENAI_API_KEY
```

## Run

```bash
uvicorn main:app --reload
```

API docs: http://localhost:8000/docs

---

## Endpoint

### `POST /api/v1/analyze-case`

**Request body:**
```json
{
  "age": 58,
  "gender": "male",
  "symptoms": ["chest pain", "shortness of breath", "fatigue"],
  "diagnosis": "anxiety disorder",
  "medications": ["warfarin", "aspirin", "ibuprofen"],
  "lab_results": {
    "hemoglobin": 10.2,
    "WBC": 13.5,
    "platelets": 95,
    "blood_sugar": 145,
    "cholesterol": 260
  }
}
```

**Response:**
```json
{
  "risk_level": "CRITICAL",
  "alerts": [
    {
      "type": "diagnosis_mismatch",
      "message": "Symptoms of chest pain and shortness of breath are inconsistent with anxiety disorder and may indicate acute coronary syndrome.",
      "recommended_action": "Immediate cardiology consult and ECG."
    },
    {
      "type": "drug_interaction",
      "message": "Warfarin + Aspirin + Ibuprofen: triple anticoagulant/NSAID combination increases bleeding risk significantly.",
      "recommended_action": "Discontinue ibuprofen; review anticoagulation regimen with pharmacist."
    },
    {
      "type": "lab_abnormality",
      "message": "Hemoglobin (Low): May indicate anaemia. | Platelets (Critical Low): Thrombocytopenia risk. | Blood Sugar (High): Pre-diabetic range.",
      "recommended_action": "Urgent haematology review; monitor blood glucose."
    }
  ]
}
```

**cURL example:**
```bash
curl -X POST http://localhost:8000/api/v1/analyze-case \
  -H "Content-Type: application/json" \
  -d '{
    "age": 58,
    "gender": "male",
    "symptoms": ["chest pain", "shortness of breath", "fatigue"],
    "diagnosis": "anxiety disorder",
    "medications": ["warfarin", "aspirin", "ibuprofen"],
    "lab_results": {
      "hemoglobin": 10.2,
      "WBC": 13.5,
      "platelets": 95,
      "blood_sugar": 145,
      "cholesterol": 260
    }
  }'
```

---

## Architecture

```
backend/
├── main.py                        # FastAPI app, lifespan, middleware
├── requirements.txt
├── .env.example
└── app/
    ├── schemas.py                 # Pydantic request / response models
    ├── ai/
    │   └── agent.py               # MedGuardAgent — 3 AI check methods
    ├── services/
    │   └── risk_engine.py         # Weighted scoring → RiskLevel + Alerts
    └── routes/
        └── analyze.py             # POST /analyze-case handler
```

## Risk Scoring

| Domain              | Weight | Rationale                             |
|---------------------|--------|---------------------------------------|
| Diagnosis mismatch  | 40 pts | Wrong diagnosis cascades downstream   |
| Drug interaction    | 35 pts | Severe interactions are acutely fatal |
| Lab abnormalities   | 25 pts | Critical but less immediately decisive|

| Final Score | Risk Level |
|-------------|------------|
| 0–24        | LOW        |
| 25–49       | MODERATE   |
| 50–74       | HIGH       |
| 75–100      | CRITICAL   |
