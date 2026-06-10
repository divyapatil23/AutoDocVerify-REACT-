import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mongodb import (
    get_student_submissions,
    student_collection,
    submission_collection,
    validate_student_login,
)

from ocr_pipeline import run_pipeline

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

DOCUMENT_TYPES = {
    "10th_marksheet": "10th Marksheet",
    "12th_marksheet": "12th/Diploma Marksheet",
    "cet_scorecard": "CET Scorecard",
    "leaving_certificate": "Leaving Certificate",
    "caste_certificate": "Caste Certificate",
}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AI Academic Verification API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    application_id: str | None = None
    username: str | None = None
    password: str


def clean_mongo(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: clean_mongo(item)
            for key, item in value.items()
            if key != "_id"
        }

    if isinstance(value, list):
        return [clean_mongo(item) for item in value]

    return value


def document_payload(application_id: str) -> dict[str, Any]:
    submission = get_student_submissions(application_id) or {}
    docs = submission.get("documents", {})

    return {
        key: {
            "label": label,
            "submitted": bool(docs.get(key, {}).get("submitted", False)),
            "status": docs.get(key, {}).get("status", "Not Submitted"),
            "confidence": docs.get(key, {}).get("confidence", "-"),
            "matched_fields": docs.get(key, {}).get("matched_fields", []),
            "mismatched_fields": docs.get(key, {}).get("mismatched_fields", []),
        }
        for key, label in DOCUMENT_TYPES.items()
    }


def application_status(documents: dict[str, Any]) -> str:
    submitted = [doc for doc in documents.values() if doc.get("submitted")]

    if not submitted:
        return "Not Submitted"

    verified = sum(
        1 for doc in submitted if doc.get("status") == "VERIFIED"
    )

    failed = any(
        doc.get("status") == "FAILED"
        for doc in submitted
    )

    if verified == len(DOCUMENT_TYPES):
        return "Verified"

    if failed:
        return "Failed"

    return "Pending"


def application_row(student: dict[str, Any]) -> dict[str, Any]:
    app_id = student.get("application_id", "")

    documents = document_payload(app_id)

    submitted_count = sum(
        1 for doc in documents.values()
        if doc.get("submitted")
    )

    confidence_values = [
        doc.get("confidence")
        for doc in documents.values()
        if isinstance(doc.get("confidence"), (int, float))
    ]

    return {
        "application_id": app_id,
        "student_name": student.get("student_name", ""),
        "course": student.get("course", student.get("branch", "")),
        "documents_count": f"{submitted_count}/{len(DOCUMENT_TYPES)}",
        "confidence": (
            round(sum(confidence_values) / len(confidence_values))
            if confidence_values
            else "-"
        ),
        "status": application_status(documents),
        "documents": documents,
    }


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/auth/student")
def student_login(payload: LoginRequest):
    application_id = (payload.application_id or "").strip().upper()

    student = validate_student_login(
        application_id,
        payload.password
    )

    if not student:
        raise HTTPException(
            status_code=401,
            detail="Invalid student credentials"
        )

    return {
        "role": "student",
        "application_id": student["application_id"],
        "student": clean_mongo(student),
        "documents": document_payload(student["application_id"]),
    }


@app.post("/api/auth/admin")
def admin_login(payload: LoginRequest):
    if (
        payload.username != ADMIN_USERNAME
        or payload.password != ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials"
        )

    return {
        "role": "admin",
        "username": payload.username
    }


@app.get("/api/students/{application_id}")
def student_profile(application_id: str):
    student = student_collection.find_one(
        {"application_id": application_id.upper()}
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    return clean_mongo(student)


@app.get("/api/students/{application_id}/documents")
def student_documents(application_id: str):
    return document_payload(application_id.upper())


@app.post("/api/students/{application_id}/documents/{doc_type}")
async def upload_document(
    application_id: str,
    doc_type: str,
    file: UploadFile = File(...),
):
    if doc_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid document type"
        )

    file_bytes = await file.read()

    ext = Path(file.filename or "document").suffix or ".bin"

    safe_path = (
        UPLOAD_DIR
        / f"{application_id.upper()}_{doc_type}{ext}"
    )

    safe_path.write_bytes(file_bytes)

    try:
        raw_text, reconstructed, validated, structured, verification = run_pipeline(
            file_bytes,
            doc_type,
            application_id.upper(),
        )

        verification_data = {
            "submitted": True,
            "status": verification.get("verification_status", "PENDING"),
            "confidence": verification.get("confidence_score", 0),
            "matched_fields": verification.get("matched_fields", []),
            "mismatched_fields": verification.get("mismatched_fields", []),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {exc}"
        )

    submission = submission_collection.find_one({
        "application_id": application_id.upper()
    })

    if not submission:
        submission_collection.insert_one({
            "application_id": application_id.upper(),
            "documents": {}
        })

    submission_collection.update_one(
        {"application_id": application_id.upper()},
        {
            "$set": {
                f"documents.{doc_type}": verification_data
            }
        }
    )

    return {
        "document_type": doc_type,
        "file_name": file.filename,
        "structured_data": structured,
        "raw_text": validated,
        "verification": verification_data,
        "documents": document_payload(application_id.upper()),
    }


@app.get("/api/admin/applications")
def admin_applications():
    students = list(
        student_collection.find().sort("application_id", 1)
    )

    rows = [
        application_row(clean_mongo(student))
        for student in students
    ]

    return {"applications": rows}


@app.get("/api/admin/stats")
def admin_stats():
    students = list(student_collection.find())

    rows = [
        application_row(clean_mongo(student))
        for student in students
    ]

    return {
        "total": len(rows),
        "verified": sum(
            1 for row in rows
            if row["status"] == "Verified"
        ),
        "pending": sum(
            1 for row in rows
            if row["status"] == "Pending"
        ),
        "failed": sum(
            1 for row in rows
            if row["status"] == "Failed"
        ),
        "not_submitted": sum(
            1 for row in rows
            if row["status"] == "Not Submitted"
        ),
    }