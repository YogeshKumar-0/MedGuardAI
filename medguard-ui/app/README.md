# 🏥 MedGuard AI

AI-powered clinical risk detection system for identifying diagnosis mismatches, drug interactions, and lab abnormalities.

---

## 🚀 Features

* Diagnosis validation (symptom mismatch detection)
* Drug interaction analysis
* Lab abnormality detection (rule-based)
* Risk scoring (LOW → CRITICAL)
* Explainable AI insights

---

## 🧠 Tech Stack

* Backend: FastAPI (Python)
* Frontend: Next.js + React + Tailwind
* AI: Groq / LLM APIs
* Architecture: Hybrid (AI + Rule Engine)

---

## 📊 Example Input

```json
{
  "age": 52,
  "gender": "male",
  "symptoms": ["chest pain", "shortness of breath"],
  "diagnosis": "gastric reflux",
  "medications": ["aspirin"],
  "lab_results": {
    "hemoglobin": 8,
    "WBC": 12000,
    "platelets": 90000,
    "blood_sugar": 180,
    "cholesterol": 250
  }
}
```

---

## 📈 Output

* Risk Level: HIGH / CRITICAL
* Alerts:

  * Diagnosis mismatch
  * Lab abnormalities

---

## ⚙️ Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd medguard-ui
npm install
npm run dev
```

---

## 🔐 Environment Variables

Create `.env` in backend:

```
OPENAI_API_KEY=your_api_key
```

---

## ⚠️ Disclaimer

For educational purposes only. Not for real medical use.

---

## 👨‍💻 Author

Yogesh
