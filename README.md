# 🏥 MedGuard AI

> AI-powered clinical risk detection system for preventing medical errors in real time.

---

## 🚀 Live Concept

MedGuard AI analyzes patient cases and detects:

* ❗ Diagnosis mismatches
* 💊 Drug interaction risks
* 🧪 Critical lab abnormalities
* ⚠️ Overall clinical risk (LOW → CRITICAL)

---

## 🖥️ UI Preview

### 📊 Dashboard

![Dashboard](assets/dashboard.png)

### ⚠️ Risk Analysis

![Analysis](assets/analysis.png)

### 🧠 Explainability Panel

![Explainability](assets/explainability.png)

---

## 🧠 How It Works

```
User Input
   ↓
FastAPI Backend (Async)
   ↓
AI Agents (Diagnosis + Drug + Lab)
   ↓
Rule Engine (Deterministic validation)
   ↓
Risk Scoring Engine
   ↓
Frontend Dashboard (Next.js)
```

---

## ⚙️ Tech Stack

### Backend

* FastAPI
* Python
* AsyncIO

### Frontend

* Next.js
* React
* Tailwind CSS

### AI Layer

* Groq LLM API
* Prompt-based medical reasoning

### Core Design

* Hybrid AI + Rule Engine
* Explainable AI system

---

## 📊 Example Use Case

**Input:**

* Symptoms: Chest pain, shortness of breath
* Diagnosis: Gastric reflux

**Output:**

* 🚨 Diagnosis mismatch detected
* ⚠️ Critical lab abnormalities
* 🔴 Risk Level: HIGH / CRITICAL

---

## 🧩 Key Features

* Real-time clinical risk detection
* Explainable AI decisions
* Modular agent-based architecture
* Deterministic lab rule engine
* Clean medical dashboard UI

---

## ⚠️ Problem It Solves

Medical errors occur due to:

* Misdiagnosis
* Overlooked lab values
* Drug interaction risks

MedGuard AI acts as a **second layer of safety for clinicians**.

---

## 🛠️ Setup

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

Create:

```
backend/.env
```

```env
GROQ_API_KEY=your_api_key_here
```

---

## 🚀 Future Scope

* Full rule-based diagnosis engine
* Hospital EMR integration
* Real-time patient monitoring
* Medical knowledge graph
* Explainability scoring

---

## ⚠️ Disclaimer

Not intended for real clinical use. Educational & research purpose only.

---

## 👨‍💻 Author

Yogesh
BTech CSE