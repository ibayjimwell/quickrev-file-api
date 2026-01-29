# 🧠 QuickRev AI Generation API

**Backend engine for generating Reviewers & Flashcards from study files**

This API powers **QuickRev**, an AI-assisted study tool that converts uploaded learning materials into:

* 📘 Structured reviewers
* 🧠 Flashcards

It handles **file management**, **content processing**, and **AI-based generation**.

🔗 **Frontend App:** [https://github.com/ibayjimwell/quickrev-app](https://github.com/ibayjimwell/quickrev-app)
🌐 **Live App:** [https://quickrev-app.vercel.app/](https://quickrev-app.vercel.app/)

---

## 🚀 Tech Stack

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge\&logo=python\&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white)
![Google Gemini](https://img.shields.io/badge/AI-Google_Gemini-4285F4?style=for-the-badge\&logo=google\&logoColor=white)

* **FastAPI** — High-performance Python API framework
* **Gemini AI** — Content generation (reviewers & flashcards)
* **Cloud Storage (Appwrite)** — File storage and management
* **Python Controllers** — Business logic layer

---

## 📖 What This API Does

✔ Upload and manage student files
✔ Extract learning content
✔ Generate structured reviewer notes
✔ Generate flashcards in multiple formats
✔ Convert reviewers into downloadable DOCX files
✔ Associate generated files with original uploads

---

## 🌍 Base URL

```
/ (root)
```

---

# 📚 API Endpoints

---

## 🧾 Generation Endpoints

### 📘 Generate Reviewer

```
POST /generate/reviewer
```

**Form Data**

| Field   | Type   | Description                |
| ------- | ------ | -------------------------- |
| file_id | string | ID of uploaded lesson file |
| user_id | string | User identifier            |

---

### 🧠 Generate Flashcards

```
POST /generate/flashcards
```

**Form Data**

| Field           | Type   | Default | Description            |
| --------------- | ------ | ------- | ---------------------- |
| file_id         | string | —       | Source file            |
| user_id         | string | —       | User identifier        |
| multiple_choice | int    | 10      | Number of MC questions |
| identification  | int    | 10      | Identification items   |
| true_or_false   | int    | 10      | T/F questions          |
| enumeration     | int    | 10      | Enumeration items      |

---

### 📄 Download Reviewer as DOCX

```
POST /download/reviewer/docx
```

| Field            | Type   | Description                |
| ---------------- | ------ | -------------------------- |
| reviewer_file_id | string | Generated reviewer file ID |

---

## ☁️ File Management (Cloud)

### 📤 Upload File

```
POST /cloud/file/upload
```

| Field   | Type        |
| ------- | ----------- |
| file    | file upload |
| user_id | string      |

---

### 📂 List Files

```
GET /cloud/file/list
```

Query Params:

| Param   | Description                          |
| ------- | ------------------------------------ |
| user_id | Owner of files                       |
| type    | File type filter (default: original) |

---

### 👁 View File

```
GET /cloud/file/view?file_id=...
```

---

### 🔗 File Association

```
GET /cloud/file/associate?source_file_id=...
```

Returns generated files related to an original upload.

---

### ❌ Delete File

```
DELETE /cloud/file/delete?file_id=...&user_id=...
```

---

## 🧠 How the System Works

1. User uploads a study file
2. File is stored in cloud storage
3. User requests reviewer or flashcards
4. Backend extracts content
5. **Gemini AI** generates structured study material
6. Files are saved and linked to the original upload
7. User can download or study online

---

## 🛠 Running Locally

### 1️⃣ Clone the repository

```bash
git clone <repo-url>
cd quickrev-api
```

### 2️⃣ Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Setup Environment Variables

Create a `.env` file:

```
GEMINI_API_KEY=your_api_key
APPWRITE_ENDPOINT=your_endpoint
APPWRITE_PROJECT_ID=your_project
APPWRITE_API_KEY=your_key
```

### 5️⃣ Start server

```bash
uvicorn main:app --reload
```

Server runs at:

```
http://127.0.0.1:8000
```

---

## 🎯 Who This Is For

* Students
* EdTech platforms
* Learning productivity tools

---

## 🔮 Future Improvements

* Quiz mode generation
* Difficulty-level control
* Multi-language support
* User study history
* PDF export for flashcards

---

## 👨‍💻 Author

**Jimwell Ibay**
Creator & Maintainer
