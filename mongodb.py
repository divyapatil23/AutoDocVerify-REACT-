# mongodb.py

from pymongo import MongoClient
from dotenv import load_dotenv
import os

# =========================================
# LOAD ENV VARIABLES
# =========================================

load_dotenv()

# =========================================
# MONGODB URI
# =========================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

# =========================================
# CONNECT TO MONGODB
# =========================================

try:

    client = MongoClient(MONGO_URI)

    client.admin.command("ping")

    print("✅ MongoDB Connected Successfully")

except Exception as e:

    print("❌ MongoDB Connection Failed")

    print(e)

# =========================================
# DATABASE
# =========================================

db = client["college_verify"]

# =========================================
# COLLECTIONS
# =========================================

# MASTER STUDENT DATA
student_collection = db["students"]

# DOCUMENT SUBMISSION STATUS
submission_collection = db["documents"]

# =========================================
# HELPER FUNCTIONS
# =========================================

# -----------------------------------------
# GET STUDENT BY APPLICATION ID
# -----------------------------------------

def get_student(application_id):

    return student_collection.find_one({

        "application_id": application_id
    })

# -----------------------------------------
# STUDENT LOGIN
# -----------------------------------------

def validate_student_login(

    application_id,
    dob
):

    student = student_collection.find_one({

        "application_id": application_id,

        "dob": dob
    })

    return student

# -----------------------------------------
# SAVE DOCUMENT STATUS
# -----------------------------------------

def save_document_status(

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

# -----------------------------------------
# GET STUDENT SUBMISSIONS
# -----------------------------------------

def get_student_submissions(

    application_id
):

    return submission_collection.find_one({

        "application_id": application_id
    })

# -----------------------------------------
# GET ALL SUBMISSIONS
# -----------------------------------------

def get_all_submissions():

    return list(
        submission_collection.find()
    )

# -----------------------------------------
# TOTAL STUDENTS
# -----------------------------------------

def get_total_students():

    return student_collection.count_documents({})

# -----------------------------------------
# TOTAL VERIFIED STUDENTS
# -----------------------------------------

def get_verified_students():

    data = list(
        submission_collection.find()
    )

    verified = 0

    for student in data:

        docs = student.get(
            "documents",
            {}
        )

        verified_docs = 0

        for _, value in docs.items():

            if value.get("status") == "VERIFIED":

                verified_docs += 1

        if verified_docs == 5:

            verified += 1

    return verified

# -----------------------------------------
# TOTAL PENDING STUDENTS
# -----------------------------------------

def get_pending_students():

    data = list(
        submission_collection.find()
    )

    pending = 0

    for student in data:

        docs = student.get(
            "documents",
            {}
        )

        verified_docs = 0

        for _, value in docs.items():

            if value.get("status") == "VERIFIED":

                verified_docs += 1

        if verified_docs > 0 and verified_docs < 5:

            pending += 1

    return pending

# -----------------------------------------
# TOTAL FAILED STUDENTS
# -----------------------------------------

def get_failed_students():

    data = list(
        submission_collection.find()
    )

    failed = 0

    for student in data:

        docs = student.get(
            "documents",
            {}
        )

        verified_docs = 0

        for _, value in docs.items():

            if value.get("status") == "VERIFIED":

                verified_docs += 1

        if verified_docs == 0:

            failed += 1

    return failed

# =========================================
# CREATE INDEXES
# =========================================

student_collection.create_index(

    "application_id",

    unique=True
)

submission_collection.create_index(

    "application_id",

    unique=True
)

print("✅ MongoDB Indexes Created")