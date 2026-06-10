# ocr_pipeline.py

import io
import re
import json
import os
import fitz
import easyocr
import numpy as np

from PIL import Image
from groq import Groq
from dotenv import load_dotenv

from mongodb import (
    student_collection,
    submission_collection
)

# =====================================
# ENV + MODELS
# =====================================

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

print("Loading EasyOCR...")

easyocr_reader = easyocr.Reader(
    ['en'],
    gpu=False
)

print("✅ EasyOCR Loaded")

# =====================================
# HELPERS
# =====================================

def call_llm(prompt, max_tokens=500):

    response = groq_client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=max_tokens
    )

    return (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

def normalize_text(text):

    text = text.lower()

    text = re.sub(
        r"[^\w\s]",
        "",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()

def extract_application_id(text):

    match = re.search(
        r'APP\d{4}',
        text.upper().replace("O", "0")
    )

    return match.group() if match else ""

# =====================================
# PDF TO IMAGE
# =====================================

def convert_pdf_to_images(pdf_bytes):

    images = []

    pdf = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    total_pages = min(
        len(pdf),
        2
    )

    for i in range(total_pages):

        page = pdf.load_page(i)

        pix = page.get_pixmap(
            matrix=fitz.Matrix(1.5, 1.5)
        )

        img = Image.frombytes(

            "RGB",

            [pix.width, pix.height],

            pix.samples
        )

        images.append(np.array(img))

    return images

# =====================================
# OCR
# =====================================

def vision_agent(file_bytes):

    texts = []
    confs = []

    # PDF

    if file_bytes[:4] == b"%PDF":

        images = convert_pdf_to_images(
            file_bytes
        )

    # IMAGE

    else:

        img = Image.open(
            io.BytesIO(file_bytes)
        )

        images = [np.array(img)]

    try:

        for image in images:

            res = easyocr_reader.readtext(
                image
            )

            for r in res:

                if len(r) >= 3:

                    texts.append(
                        str(r[1])
                    )

                    confs.append(
                        float(r[2]) * 100
                    )

    except Exception as e:

        print(
            "EasyOCR Error:",
            e
        )

    return (

        "\n".join(texts),

        np.mean(confs)
        if confs else 0
    )

# =====================================
# OCR RECONSTRUCTION
# =====================================

def reconstruction_agent(text):

    if len(text) < 50:
        return text

    prompt = f"""
Fix OCR spelling mistakes only.

Do not hallucinate.

TEXT:
{text}

Return corrected text only.
"""

    try:

        return call_llm(prompt)

    except:

        return text

# =====================================
# VALIDATION
# =====================================

def validation_agent(text):

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()

# =====================================
# SCHEMAS
# =====================================

SCHEMAS = {

    "10th_marksheet": {

        "student_name": "",
        "father_name": "",
        "mother_name": "",
        "board": "",
        "year_of_passing": "",
        "percentage": "",
        "application_id": ""
    },

    "12th_marksheet": {

        "student_name": "",
        "board": "",
        "school": "",
        "year_of_passing": "",
        "overall_percentage": "",
        "application_id": ""
    },

    "cet_scorecard": {

        "student_name": "",
        "cet_score": "",
        "application_id": ""
    },

    "leaving_certificate": {

        "student_name": "",
        "school": "",
        "date_of_birth": "",
        "application_id": ""
    },

    "caste_certificate": {

        "student_name": "",
        "caste_category": "",
        "application_id": ""
    }
}

FIELD_MAPPING = {

    "10th_marksheet": {

        "board": "tenth_board",
        "year_of_passing": "tenth_passing_year",
        "percentage": "tenth_percentage"
    },

    "12th_marksheet": {

        "board": "diploma_board",
        "school": "diploma_college",
        "year_of_passing": "diploma_passing_year",
        "overall_percentage": "diploma_percentage"
    },

    "cet_scorecard": {

        "cet_score": "current_percentage"
    },

    "leaving_certificate": {

        "school": "college_name",
        "date_of_birth": "dob"
    },

    "caste_certificate": {

        "caste_category": "category"
    }
}

# =====================================
# DOCUMENT EXTRACTION
# =====================================

def document_agent(text, doc_type):

    prompt = f"""
Extract structured information.

Return ONLY JSON.

DOCUMENT TYPE:
{doc_type}

TEXT:
{text}

FORMAT:
{json.dumps(SCHEMAS[doc_type])}
"""

    try:

        response = call_llm(prompt)

        response = (
            response
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        data = json.loads(response)

        data["application_id"] = (
            extract_application_id(text)
        )

        return data

    except Exception as e:

        print(
            "Document Agent Error:",
            e
        )

        return {}

# =====================================
# VERIFICATION
# =====================================

def mongodb_verification_agent(

    structured_output,
    doc_type,
    logged_in_application_id
):

    if not structured_output:

        return {

            "verification_status": "FAILED",
            "confidence_score": 0,
            "summary": "No data extracted"
        }

    app_id = (
        logged_in_application_id
        .strip()
        .upper()
    )

    db_record = student_collection.find_one({

        "application_id": app_id
    })

    if not db_record:

        return {

            "verification_status": "FAILED",
            "confidence_score": 0,
            "summary": "Student not found"
        }

    ocr_app_id = structured_output.get(
        "application_id",
        ""
    ).upper()

    if ocr_app_id and ocr_app_id != app_id:

        return {

            "verification_status": "FAILED",

            "confidence_score": 0,

            "summary": "Wrong applicant document"
        }

    matched = []
    mismatched = []

    mapping = FIELD_MAPPING.get(
        doc_type,
        {}
    )

    total = 0
    correct = 0

    for key, value in structured_output.items():

        if key == "application_id":
            continue

        total += 1

        db_key = mapping.get(
            key,
            key
        )

        db_value = normalize_text(
            str(
                db_record.get(
                    db_key,
                    ""
                )
            ).replace("%", "")
        )

        ocr_value = normalize_text(
            str(value).replace("%", "")
        )

        is_match = False

        try:

            is_match = (
                abs(
                    float(db_value)
                    -
                    float(ocr_value)
                ) < 1
            )

        except:

            is_match = (
                db_value == ocr_value
            )

        if is_match:

            matched.append(key)
            correct += 1

        else:

            mismatched.append({

                "field": key,

                "ocr_value": value,

                "db_value": db_record.get(
                    db_key,
                    ""
                )
            })

    confidence = int(
        (correct / total) * 100
    ) if total else 0

    status = (
        "VERIFIED"
        if confidence >= 90
        else
        "WARNING"
        if confidence >= 60
        else
        "FAILED"
    )

    return {

        "verification_status": status,

        "confidence_score": confidence,

        "matched_fields": matched,

        "mismatched_fields": mismatched,

        "summary": f"{correct}/{total} matched"
    }

# =====================================
# MAIN PIPELINE
# =====================================

def run_pipeline(

    file_bytes,
    doc_type,
    logged_in_application_id
):

    raw_text, conf = vision_agent(
        file_bytes
    )

    reconstructed = reconstruction_agent(
        raw_text
    )

    validated = validation_agent(
        reconstructed
    )

    structured = document_agent(
        validated,
        doc_type
    )

    verification = mongodb_verification_agent(

        structured,

        doc_type,

        logged_in_application_id
    )

    return (

        raw_text,

        reconstructed,

        validated,

        structured,

        verification
    )

# =====================================
# SAVE STATUS
# =====================================

def save_submission_status(

    application_id,
    doc_type,
    verification
):

    submission_collection.update_one(

        {
            "application_id": application_id
        },

        {
            "$set": {

                f"documents.{doc_type}": {

                    "submitted": True,

                    "verified": (
                        verification[
                            "verification_status"
                        ] == "VERIFIED"
                    ),

                    "status": verification[
                        "verification_status"
                    ],

                    "confidence": verification[
                        "confidence_score"
                    ],

                    "matched_fields": verification.get(
                        "matched_fields",
                        []
                    ),

                    "mismatched_fields": verification.get(
                        "mismatched_fields",
                        []
                    )
                }
            }
        },

        upsert=True
    )

    print(
        f"✅ Saved: "
        f"{application_id} - {doc_type}"
    )