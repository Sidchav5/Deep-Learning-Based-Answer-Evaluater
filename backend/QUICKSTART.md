# Quick Start Guide - Llama Pipeline Integration

## 🎯 What this backend now uses

- External **Colab/Kaggle FastAPI** Llama pipeline (your final notebook)
- Endpoint contract:
  - `POST /generate-answer`
  - `POST /evaluate`
  - `POST /batch-evaluate`
  - `GET /health`
- Question format with marks is preserved:

```text
What is underfitting in Machine Learning?
Marks: 5
```

---

## 🚀 Setup (3 steps)

### 1) Run your final notebook API

Run your final pipeline notebook in Colab and keep the server cell running.
Make sure the ngrok URL is live, for example:

```text
https://overjealous-kimberley-nonoperative.ngrok-free.app
```

### 2) Configure backend `.env`

In `backend/.env` set:

```env
LLAMA_API_BASE_URL=https://overjealous-kimberley-nonoperative.ngrok-free.app
LLAMA_TIMEOUT_SECONDS=300
```

Optional alias (not required when `LLAMA_API_BASE_URL` is set):

```env
KAGGLE_NGROK_URL=
```

### 3) Start backend

```powershell
cd backend
python main.py
```

---

## ✅ Verify integration

### Health check

```bash
curl http://localhost:5000/api/health
```

Expected important fields:

```json
{
  "llama_api_configured": true,
  "llama_api_healthy": true
}
```

### Evaluation flow

- Frontend evaluation uses the Llama pipeline by default
- Backend forwards question + student answer to your notebook API
- Backend receives:
  - `reference_answer` (Llama output)
  - semantic/keyword scores
  - `awarded_marks`
- Result is returned in app’s existing report format

---

## 🧩 Notes

- If question text does not include `Marks: X`, backend appends it automatically.
- If question already includes marks, backend sends it unchanged.
- Study material upload is optional and no longer required for Llama API scoring mode.
- Keep your Colab runtime alive; if it stops, evaluation requests will fail until the endpoint is active again.
