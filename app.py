"""
BMD-HS Heart Disease Detection Agentic AI - FastAPI Backend Server.

Supports:
1. Four-valve input patient sessions (Aortic, Mitral, Pulmonary, Tricuspid).
2. Specialized Multi-Agent Orchestration:
   - Agent 1: Signal & Data Quality Agent
   - Agent 2: RosaNet Prediction & XAI Agent
   - Agent 3: ACC/AHA Clinical RAG Evidence Agent
3. Comprehensive Clinical Report Synthesis.
"""

import os
import io
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.agents.orchestrator import DiagnosticPipelineOrchestrator
from src.agents.schemas import FinalClinicalReport

app = FastAPI(
    title="BMD-HS Multi-Valvular Cardiovascular Diagnostic Assistant API",
    description="Agentic AI system for multi-valve phonocardiogram classification and ACC/AHA guideline retrieval.",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ORCHESTRATOR: Optional[DiagnosticPipelineOrchestrator] = None


@app.on_event("startup")
def initialize_system():
    global ORCHESTRATOR
    print("[INFO] Initializing Multi-Agent Diagnostic Pipeline Orchestrator...")
    try:
        model_orig = ROOT_DIR / "dataset" / "models" / "best_rosanet_model.keras"
        model_4v = ROOT_DIR / "dataset" / "models" / "best_rosanet_4valve_model.keras"
        # Prioritize full 8-branch patient model, falling back to 4-valve if not available
        model_path = model_orig if model_orig.exists() else model_4v
        chroma_dir = ROOT_DIR / "dataset" / "rag" / "chroma_db"
        ORCHESTRATOR = DiagnosticPipelineOrchestrator(
            model_checkpoint_path=str(model_path) if model_path.exists() else None,
            chroma_db_dir=str(chroma_dir) if chroma_dir.exists() else None
        )
        print("[SUCCESS] Multi-Agent Pipeline Orchestrator initialized.")
    except Exception as e:
        import traceback
        traceback.print_exc()
def get_orchestrator() -> Optional[DiagnosticPipelineOrchestrator]:
    global ORCHESTRATOR
    if ORCHESTRATOR is None:
        initialize_system()
    return ORCHESTRATOR


@app.get("/api/status")
def get_system_status():
    return {
        "status": "online",
        "engine": "RosaNet 8-Branch Patient Auscultation Multi-Agent Engine",
        "target_sr": 2000,
        "posture_groups": ["SITTING", "SUPINE"],
        "recordings_required": [
            "sit_Aor", "sit_Pul", "sit_Tri", "sit_Mit",
            "sup_Aor", "sup_Pul", "sup_Tri", "sup_Mit"
        ],
        "orchestrator_ready": ORCHESTRATOR is not None
    }


@app.get("/api/sample_patients")
def get_sample_patients():
    """
    Returns curated authentic clinical 8-recording patient sets from the dataset.
    Organized into TWO POSTURE GROUPS: SITTING (Aor, Pul, Tri, Mit) and SUPINE (Aor, Pul, Tri, Mit).
    """
    train_dir = ROOT_DIR / "train"
    if not train_dir.exists():
        return {"patients": []}

    # Curate authentic patients across all disease categories
    curated_pids = [
        ("patient_089", "Normal Healthy Subject", "Normal", "N_089"),
        ("patient_005", "Aortic Stenosis (AS)", "Aortic Stenosis", "AS_005"),
        ("patient_016", "Aortic Regurgitation (AR)", "Aortic Regurgitation", "AR_016"),
        ("patient_002", "Mitral Regurgitation (MR)", "Mitral Regurgitation", "MR_002"),
        ("patient_006", "Mitral Stenosis (MS)", "Mitral Stenosis", "MS_006"),
        ("patient_003", "Combined Multi-Valvular Disease (AS+AR)", "Multi-Disease", "MD_003")
    ]

    recording_keys = [
        ("sit_Aor", "sit_Aor"),
        ("sit_Pul", "sit_Pul"),
        ("sit_Tri", "sit_Tri"),
        ("sit_Mit", "sit_Mit"),
        ("sup_Aor", "sup_Aor"),
        ("sup_Pul", "sup_Pul"),
        ("sup_Tri", "sup_Tri"),
        ("sup_Mit", "sup_Mit")
    ]

    patients = []
    for pid, label, category, prefix in curated_pids:
        valves_map = {}
        all_found = True
        for key, suffix in recording_keys:
            fname = f"{prefix}_{suffix}.wav"
            if (train_dir / fname).exists():
                valves_map[key] = fname
            else:
                all_found = False
                break

        if all_found:
            patients.append({
                "patient_id": pid,
                "label": label,
                "category": category,
                "valves": valves_map
            })

    return {"patients": patients}


@app.get("/api/sample_audio/{filename}")
def stream_sample_audio(filename: str):
    file_path = ROOT_DIR / "train" / filename
    if not file_path.exists():
        file_path = ROOT_DIR / "dataset" / "augmented" / "train" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(str(file_path), media_type="audio/wav")


@app.post("/api/predict_patient")
async def analyze_patient_session(
    # GROUP 1: SITTING
    sit_aor: Optional[UploadFile] = File(None),
    sit_pul: Optional[UploadFile] = File(None),
    sit_tri: Optional[UploadFile] = File(None),
    sit_mit: Optional[UploadFile] = File(None),
    # GROUP 2: SUPINE
    sup_aor: Optional[UploadFile] = File(None),
    sup_pul: Optional[UploadFile] = File(None),
    sup_tri: Optional[UploadFile] = File(None),
    sup_mit: Optional[UploadFile] = File(None),
    # Legacy 4-valve parameters
    file_aor: Optional[UploadFile] = File(None),
    file_mit: Optional[UploadFile] = File(None),
    file_pul: Optional[UploadFile] = File(None),
    file_tri: Optional[UploadFile] = File(None),
    sample_patient_id: Optional[str] = Form(None)
):
    """
    Main Multi-Valvular Diagnostic Endpoint:
    Accepts 8 heart-sound WAV recordings organized into TWO POSTURE GROUPS:
      SITTING: Aortic, Pulmonary, Tricuspid, Mitral
      SUPINE:  Aortic, Pulmonary, Tricuspid, Mitral
    Executes Agent 1 (Quality & Preprocessing) -> Agent 2 (RosaNet 8-Branch Prediction & XAI) -> Agent 3 (RAG) -> Clinical Report.
    """
    orchestrator = get_orchestrator()
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Diagnostic Orchestrator is not initialized.")

    recording_inputs = {}
    train_dir = ROOT_DIR / "train"

    # Map parameter names to canonical internal branch keys
    param_map_8 = {
        "sit_Aor": sit_aor,
        "sit_Pul": sit_pul,
        "sit_Tri": sit_tri,
        "sit_Mit": sit_mit,
        "sup_Aor": sup_aor,
        "sup_Pul": sup_pul,
        "sup_Tri": sup_tri,
        "sup_Mit": sup_mit
    }
    label_map_8 = {
        "sit_Aor": "Sitting Aortic (sit_Aor)",
        "sit_Pul": "Sitting Pulmonary (sit_Pul)",
        "sit_Tri": "Sitting Tricuspid (sit_Tri)",
        "sit_Mit": "Sitting Mitral (sit_Mit)",
        "sup_Aor": "Supine Aortic (sup_Aor)",
        "sup_Pul": "Supine Pulmonary (sup_Pul)",
        "sup_Tri": "Supine Tricuspid (sup_Tri)",
        "sup_Mit": "Supine Mitral (sup_Mit)"
    }

    if sample_patient_id:
        samples = get_sample_patients()["patients"]
        matched = next((p for p in samples if p["patient_id"] == sample_patient_id), None)
        if not matched:
            raise HTTPException(status_code=404, detail=f"Sample patient {sample_patient_id} not found.")

        for key, fname in matched["valves"].items():
            f_path = train_dir / fname
            if not f_path.exists():
                f_path = ROOT_DIR / "dataset" / "augmented" / "train" / fname
            with open(f_path, "rb") as f:
                recording_inputs[key] = f.read()

        session_id = f"SESSION-{sample_patient_id.upper()}"
        metadata = {"patient_id": sample_patient_id}

    else:
        # Check if 8 posture-specific files or 4 legacy files are provided
        has_any_8 = any(f is not None for f in param_map_8.values())

        if has_any_8:
            missing = [k for k, f in param_map_8.items() if f is None]
            if missing:
                missing_names = [label_map_8[k] for k in missing]
                raise HTTPException(
                    status_code=400,
                    detail=f"Analysis requires all 8 recordings (4 Sitting + 4 Supine). Missing {len(missing)} recording(s): {', '.join(missing_names)}"
                )

            for key, up_file in param_map_8.items():
                content = await up_file.read()
                recording_inputs[key] = content

        else:
            # Fallback legacy 4 files
            legacy_uploaded = {
                "Aor": file_aor,
                "Mit": file_mit,
                "Pul": file_pul,
                "Tri": file_tri
            }
            missing_legacy = [v for v, f in legacy_uploaded.items() if f is None]
            if missing_legacy:
                raise HTTPException(
                    status_code=400,
                    detail=f"Analysis requires either all 8 recordings or all 4 valve files. Missing: {', '.join(missing_legacy)}"
                )
            for v_name, up_file in legacy_uploaded.items():
                content = await up_file.read()
                recording_inputs[v_name] = content

        session_id = f"SESSION-CUSTOM-{os.urandom(3).hex().upper()}"
        metadata = None

    try:
        report: FinalClinicalReport = orchestrator.process_session(
            valve_files=recording_inputs,
            session_id=session_id,
            patient_metadata=metadata
        )
        return report.model_dump() if hasattr(report, "model_dump") else report.dict()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


# Serve Web Frontend with zero browser caching
web_dir = ROOT_DIR / "web"
if web_dir.exists():
    @app.get("/")
    def get_index():
        return FileResponse(
            str(web_dir / "index.html"),
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    @app.get("/style.css")
    def get_css():
        return FileResponse(
            str(web_dir / "style.css"),
            media_type="text/css",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    @app.get("/script.js")
    def get_js():
        return FileResponse(
            str(web_dir / "script.js"),
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    @app.get("/results.html")
    def get_results_html():
        return FileResponse(
            str(web_dir / "results.html"),
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    @app.get("/results.js")
    def get_results_js():
        return FileResponse(
            str(web_dir / "results.js"),
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
        )

    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
