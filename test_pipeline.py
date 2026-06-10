from ocr_pipeline import run_pipeline

pdf_path = r"C:\Users\patil\Downloads\222ocrr\db\PDF_Documents\APP0001_10th_Marksheet.pdf"

with open(pdf_path, "rb") as f:
    file_bytes = f.read()

print("Running OCR pipeline...")

result = run_pipeline(
    file_bytes,
    "10th_marksheet",
    "APP0001"
)

print("\n===== OCR RESULT =====\n")
print(result)