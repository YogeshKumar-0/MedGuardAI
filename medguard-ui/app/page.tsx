"use client";

import React, { useState } from "react";

// Types for our API response
interface Alert {
  type: string;
  message: string;
  recommended_action: string;
}

interface ApiResponse {
  risk_level: "LOW" | "MODERATE" | "HIGH" | "CRITICAL";
  alerts: Alert[];
}

export default function MedGuardDashboard() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    age: "",
    gender: "male",
    symptoms: "",
    diagnosis: "",
    medications: "",
    labs: {
      hemoglobin: "",
      wbc: "",
      platelets: "",
      blood_sugar: "",
      cholesterol: "",
    },
  });

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleLabChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      labs: { ...prev.labs, [name]: value },
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    setLoading(true);
    setError(null);
    setResult(null);

    const payload = {
      age: Number(formData.age),
      gender: formData.gender,
      symptoms: formData.symptoms
        ? formData.symptoms.split(",").map((s) => s.trim())
        : [],
      diagnosis: formData.diagnosis,
      medications: formData.medications
        ? formData.medications.split(",").map((m) => m.trim())
        : [],
      lab_results: {
        hemoglobin: Number(formData.labs.hemoglobin) || 0,
        WBC: Number(formData.labs.wbc) || 0,
        platelets: Number(formData.labs.platelets) || 0,
        blood_sugar: Number(formData.labs.blood_sugar) || 0,
        cholesterol: Number(formData.labs.cholesterol) || 0,
      },
    };

    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/analyze-case", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "API Error");
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  // Helper to get sophisticated color classes based on risk level
  const getRiskColors = (level: string) => {
    switch (level) {
      case "LOW":
        return "bg-emerald-50 text-emerald-800 border-emerald-200 ring-emerald-500/20";
      case "MODERATE":
        return "bg-amber-50 text-amber-800 border-amber-200 ring-amber-500/20";
      case "HIGH":
        return "bg-orange-50 text-orange-800 border-orange-200 ring-orange-500/20";
      case "CRITICAL":
        return "bg-rose-50 text-rose-800 border-rose-200 ring-rose-500/20 shadow-lg shadow-rose-500/20";
      default:
        return "bg-slate-50 text-slate-800 border-slate-200 ring-slate-500/20";
    }
  };

  // Common input styling for a clean, cohesive look
  const inputStyles =
    "w-full rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-3 text-slate-900 transition-all duration-200 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-4 focus:ring-indigo-500/10 sm:text-sm font-medium";

  const labelStyles =
    "mb-1.5 block text-xs font-bold uppercase tracking-wider text-slate-500";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 py-12 px-4 sm:px-6 lg:px-8 font-sans text-slate-900 selection:bg-indigo-100 selection:text-indigo-900">
      <div className="mx-auto max-w-4xl space-y-10">

        {/* Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center rounded-2xl bg-indigo-50 p-3 mb-2 shadow-inner">
            <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
            MedGuard{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">
              AI
            </span>
          </h1>
          <p className="text-base sm:text-lg text-slate-500 font-medium max-w-xl mx-auto">
            Advanced clinical risk detection powered by predictive analytics.
          </p>
        </div>

        {/* Main Form Card */}
        <div className="relative rounded-3xl bg-white/80 backdrop-blur-xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 overflow-hidden">
          {/* Subtle top gradient bar */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500"></div>

          <div className="p-8 sm:p-12">
            <form onSubmit={handleSubmit} className="space-y-10">

              {/* Demographics & Clinical Info */}
              <div>
                <h3 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs text-indigo-600">1</span>
                  Patient Profile
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className={labelStyles}>Age</label>
                    <input
                      type="number"
                      name="age"
                      required
                      value={formData.age}
                      onChange={handleInputChange}
                      className={inputStyles}
                      placeholder="e.g. 45"
                    />
                  </div>
                  <div>
                    <label className={labelStyles}>Gender</label>
                    <div className="relative">
                      <select
                        name="gender"
                        value={formData.gender}
                        onChange={handleInputChange}
                        className={`${inputStyles} appearance-none pr-10`}
                      >
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-4 text-slate-400">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                  </div>

                  <div className="md:col-span-2">
                    <label className={labelStyles}>Primary Diagnosis</label>
                    <input
                      type="text"
                      name="diagnosis"
                      required
                      value={formData.diagnosis}
                      onChange={handleInputChange}
                      className={inputStyles}
                      placeholder="e.g. Type 2 Diabetes Mellitus"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className={labelStyles}>Symptoms <span className="text-slate-400 font-normal normal-case tracking-normal">(comma separated)</span></label>
                    <textarea
                      name="symptoms"
                      rows={2}
                      value={formData.symptoms}
                      onChange={handleInputChange}
                      className={`${inputStyles} resize-none`}
                      placeholder="Fever, chronic cough, shortness of breath..."
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className={labelStyles}>Medications <span className="text-slate-400 font-normal normal-case tracking-normal">(comma separated)</span></label>
                    <textarea
                      name="medications"
                      rows={2}
                      value={formData.medications}
                      onChange={handleInputChange}
                      className={`${inputStyles} resize-none`}
                      placeholder="Lisinopril 10mg, Metformin 500mg..."
                    />
                  </div>
                </div>
              </div>

              <hr className="border-slate-100" />

              {/* Lab Results */}
              <div>
                <h3 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs text-indigo-600">2</span>
                  Biomarkers & Vitals
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                  {[
                    { label: "Hemoglobin", unit: "g/dL", name: "hemoglobin" },
                    { label: "WBC", unit: "x10³/µL", name: "wbc" },
                    { label: "Platelets", unit: "x10³/µL", name: "platelets" },
                    { label: "Blood Sugar", unit: "mg/dL", name: "blood_sugar" },
                    { label: "Cholesterol", unit: "mg/dL", name: "cholesterol" },
                  ].map((lab) => (
                    <div key={lab.name} className="relative group">
                      <label className={labelStyles}>
                        {lab.label} <span className="text-slate-400 normal-case tracking-normal">({lab.unit})</span>
                      </label>
                      <input
                        type="number"
                        step="any"
                        name={lab.name}
                        value={formData.labs[lab.name as keyof typeof formData.labs]}
                        onChange={handleLabChange}
                        className={inputStyles}
                        placeholder="0.0"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-6">
                <button
                  type="submit"
                  disabled={loading}
                  className="group relative w-full flex justify-center py-4 px-4 border border-transparent rounded-2xl text-lg font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/30 disabled:opacity-70 transition-all duration-300 shadow-[0_0_20px_rgba(79,70,229,0.3)] hover:shadow-[0_0_25px_rgba(79,70,229,0.5)] transform hover:-translate-y-0.5"
                >
                  {loading ? (
                    <span className="flex items-center gap-3">
                      <svg
                        className="animate-spin h-5 w-5 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Analyzing Patient Data...
                    </span>
                  ) : (
                    "Generate AI Analysis"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="rounded-2xl bg-rose-50 p-5 border border-rose-200 shadow-sm animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center gap-3">
              <svg className="h-6 w-6 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h3 className="text-sm font-bold text-rose-800">Connection Error</h3>
                <p className="mt-1 text-sm text-rose-600">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Results UI */}
        {result && !loading && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out">

            {/* Risk Badge */}
            <div
              className={`relative overflow-hidden rounded-3xl p-8 text-center border-2 ring-4 ring-offset-2 ring-offset-slate-50 transition-all ${getRiskColors(
                result.risk_level
              )}`}
            >
              <h2 className="text-sm font-bold uppercase tracking-widest opacity-80 mb-2">
                Overall Risk Assessment
              </h2>
              <div className="text-5xl md:text-6xl font-black tracking-tight drop-shadow-sm">
                {result.risk_level}
              </div>
            </div>

            {/* 🧠 Explainability Panel */}
            {result && (
              <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
                <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                  🧠 Explainability
                </h3>

                <div className="grid md:grid-cols-3 gap-4">

                  {/* Diagnosis */}
                  <div className="p-4 rounded-xl bg-blue-50 border border-blue-100">
                    <h4 className="font-semibold text-blue-700">Diagnosis</h4>
                    <p className="text-sm text-blue-600 mt-1">
                      {result.alerts.find(a => a.type === "diagnosis_mismatch")
                        ? "Mismatch detected"
                        : "No issues"}
                    </p>
                  </div>

                  {/* Drug */}
                  <div className="p-4 rounded-xl bg-purple-50 border border-purple-100">
                    <h4 className="font-semibold text-purple-700">Medications</h4>
                    <p className="text-sm text-purple-600 mt-1">
                      {result.alerts.find(a => a.type === "drug_interaction")
                        ? "Interaction risk"
                        : "Safe"}
                    </p>
                  </div>

                  {/* Labs */}
                  <div className="p-4 rounded-xl bg-red-50 border border-red-100">
                    <h4 className="font-semibold text-red-700">Lab Results</h4>
                    <p className="text-sm text-red-600 mt-1">
                      {result.alerts.find(a => a.type === "lab_abnormality")
                        ? "Critical abnormalities"
                        : "Normal"}
                    </p>
                  </div>
                </div>

                {/* Summary */}
                <div className="mt-4 p-4 bg-slate-50 rounded-xl border">
                  <h4 className="font-semibold text-slate-700 mb-1">Why this risk?</h4>
                  <ul className="text-sm text-slate-600 list-disc ml-5 space-y-1">
                    {result.alerts.map((a, i) => (
                      <li key={i}>{a.type.replace("_", " ")}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Alert Cards */}
            {result.alerts && result.alerts.length > 0 && (
              <div className="pt-4">
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-px bg-slate-200 flex-1"></div>
                  <h3 className="text-lg font-bold text-slate-400 uppercase tracking-widest">
                    Clinical Insights ({result.alerts.length})
                  </h3>
                  <div className="h-px bg-slate-200 flex-1"></div>
                </div>

                <div className="grid gap-5">
                  {result.alerts.map((alert, index) => (
                    <div
                      key={index}
                      className="group bg-white rounded-2xl shadow-sm border border-slate-100 p-6 hover:shadow-xl hover:border-indigo-100 transition-all duration-300"
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 mt-1">
                          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300">
                            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </div>
                        </div>
                        <div className="w-full">
                          <div className="flex items-center gap-2">
                            <h4 className="text-lg font-bold text-slate-900">
                              {alert.type}
                            </h4>
                            <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700 font-semibold">
                              HIGH
                            </span>
                          </div>
                          <p className="mt-1.5 text-base text-slate-600 leading-relaxed">
                            {alert.message}
                          </p>

                          <div className="mt-5 bg-slate-50/80 rounded-xl p-4 border border-slate-100/50">
                            <div className="flex items-center gap-2 mb-1.5">
                              <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                              <span className="text-xs font-bold uppercase text-slate-500 tracking-wider">
                                Recommended Action
                              </span>
                            </div>
                            <p className="text-sm font-semibold text-slate-800">
                              {alert.recommended_action}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}