# Auto-Doc Verify 📄✅

An automated document verification system that extracts and validates information from uploaded documents in real time using OCR, NLP, and a rule-based verification engine.

---

## 🏗️ Project Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite |
| Backend | FastAPI (Python) |
| Database | MongoDB |
| OCR Engine | EasyOCR + PyMuPDF |
| Verification | Rule-based field matching & confidence scoring |

---

## ✨ Features

- 🔐 Dual-role authentication — Admin and Student login
- 📤 Document upload interface
- 🔍 OCR-based text extraction from PDF documents
- ✅ Automated field verification with confidence scores
- 📊 Admin dashboard with verification status tracking
- 🗂️ MongoDB-backed student record management

---

## ⚙️ Prerequisites

Install the following before setup:

- [Python 3.11](https://www.python.org/downloads/) — ✅ Check **Add Python to PATH** during installation
- [Node.js LTS](https://nodejs.org/)
- [MongoDB Community Server](https://www.mongodb.com/try/download/community) — Start MongoDB service after installation

---

## 🚀 Setup & Run

### 1. Extract the Project

Extract the project ZIP to any folder. Example:
```
C:\Users\YourName\Documents\Auto-Doc-Verify
```

---

### 2. Backend Setup

Open a terminal and navigate to the project folder:
```bash
cd "C:\Users\YourName\Documents\Auto-Doc-Verify"
```

**Create virtual environment:**
```bash
python -m venv venv
```

**Activate virtual environment (Windows PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
```

> If you get an execution policy error, run this first:
> ```bash
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Then activate again.

**Install Python dependencies:**
```bash
pip install -r backend_requirements.txt
```

**Install stable OCR dependencies:**
```bash
pip uninstall pymupdf fitz -y
pip install pymupdf==1.23.8
pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu
pip install easyocr==1.7.1
```

**Run the backend:**
```bash
uvicorn backend_api:app --host 127.0.0.1 --port 8000 --reload
```

Backend runs at: `http://127.0.0.1:8000`  
Swagger API docs: `http://127.0.0.1:8000/docs`

---

### 3. Frontend Setup

Open a **new terminal** and navigate to the project folder:
```bash
cd "C:\Users\YourName\Documents\Auto-Doc-Verify"
```

**Install Node modules:**
```bash
npm install
```

**Run the React frontend:**
```bash
npm run dev
```

Frontend runs at: `http://localhost:5173`  
*(If port is busy, Vite automatically uses 5174 or 5175)*

---

## 🔑 Login Credentials

### Admin Login
| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

### Student Login
Uses MongoDB student records. Example:
| Field | Value |
|-------|-------|
| Application ID | `APP0001` |
| Password / DOB | `2004-12-20` |

---

## ⚠️ Important Notes

Keep **both terminals running** simultaneously:

- **Terminal 1** → Backend: `uvicorn backend_api:app --reload`
- **Terminal 2** → Frontend: `npm run dev`

---

## 🛠️ Troubleshooting

| Issue | Fix |
|-------|-----|
| Upload fails | Reinstall OCR: `pip install pymupdf==1.23.8` |
| Frontend says "Failed to fetch" | Ensure backend is running at `http://127.0.0.1:8000` |
| Port 5173 busy | Open whichever URL Vite shows — 5174 or 5175 |

---

## 👩‍💻 Author

**Divya Sandeep Patil**  
Final-year B.Tech Computer Science (Data Science)  
D.Y. Patil College of Engineering & Technology, Kolhapur  
[LinkedIn](https://linkedin.com/in/divyap23) • [GitHub](https://github.com/divyapatil23)
