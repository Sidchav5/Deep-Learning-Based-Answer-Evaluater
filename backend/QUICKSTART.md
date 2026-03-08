# Quick Start Guide - RAG System with Groq

## 🎯 What's New?

Your backend has been **completely refactored** with:

1. ✅ **Modular Architecture** - Clean separation of concerns
2. ✅ **RAG System** - Retrieval-Augmented Generation with Groq API
3. ✅ **Enhanced Feedback** - AI-powered detailed explanations
4. ✅ **Vector Store** - FAISS-based document retrieval
5. ✅ **Better Organization** - Easy to maintain and extend

## 🚀 Quick Setup (3 Steps)

### Step 1: Install New Dependencies

```powershell
cd backend
pip install groq faiss-cpu python-dotenv
```

### Step 2: Get Your Groq API Key

1. Visit: https://console.groq.com/
2. Sign up (it's free!)
3. Go to "API Keys" section
4. Click "Create API Key"
5. Copy your key

### Step 3: Configure Environment

**Windows:**

```powershell
Copy-Item .env.example .env
notepad .env
```

**Linux/Mac:**

```bash
cp .env.example .env
nano .env
```

Then add your Groq API key:

```env
GROQ_API_KEY=gsk_your_actual_api_key_here
```

## 🏃 Run the New Backend

```powershell
python app_new.py
```

You should see:

```
🚀 Starting AI Answer Evaluation System
================================================
📋 Configuration:
   - Environment: Development
   - RAG Enabled: True
   - Groq API Key: ✅ Configured
   - Model Directory: D:\SEM6\DL\CP\Model

✅ ML Models initialization complete

================================================
🎉 Application ready!
================================================

🌐 Server starting on http://localhost:5000
```

## 🧪 Test RAG System

### Test 1: Health Check

```bash
curl http://localhost:5000/api/health
```

Expected response:

```json
{
  "status": "healthy",
  "models_loaded": true,
  "rag_enabled": true,
  "groq_configured": true
}
```

### Test 2: Use Frontend

1. Start frontend (in another terminal):

   ```powershell
   cd frontend
   npm start
   ```

2. Login to your account

3. Go to Evaluation page

4. **Enable RAG checkbox** ✅

5. Upload:
   - Questions file
   - Model answers file
   - Student answers file
   - **Study material file** (this is new!)

6. Click "Evaluate Answers"

7. You'll see **enhanced feedback** powered by Groq AI!

## 📁 New Folder Structure

```
backend/
├── config/              # ⚙️ Configuration
│   ├── settings.py
│   └── __init__.py
├── models/              # 🧠 ML Models
│   ├── ml_models.py
│   └── __init__.py
├── services/            # 🔧 Business Logic
│   ├── evaluation_service.py
│   ├── rag_service.py
│   └── __init__.py
├── routes/              # 🌐 API Endpoints
│   ├── auth_routes.py
│   ├── evaluation_routes.py
│   └── __init__.py
├── utils/               # 🛠️ Helpers
│   ├── auth.py
│   ├── file_processing.py
│   ├── parsers.py
│   └── __init__.py
├── app_new.py          # 🚀 New Entry Point
├── .env                # 🔐 Your secrets
└── README_NEW.md       # 📖 Full docs
```

## 🎨 What Changed in Frontend?

Nothing! The API is **fully backward compatible**.

When RAG checkbox is enabled:

- Study material is automatically ingested
- Groq generates enhanced feedback
- Context is shown in results

## ⚡ Performance

- First request: ~5-10 seconds (model loading)
- RAG request: +2-3 seconds (Groq API)
- Regular evaluation: ~1-2 seconds
- Vector store: Persists between sessions

## 🔧 Configuration Options

Edit `.env` to customize:

```env
# RAG Settings
RAG_ENABLED=True                  # Toggle RAG on/off
RAG_CHUNK_SIZE=500                # Words per chunk
RAG_TOP_K=3                       # Context chunks to retrieve

# Groq Settings
GROQ_MODEL=llama-3.3-70b-versatile  # LLM model
GROQ_MAX_TOKENS=1024                # Max response length
GROQ_TEMPERATURE=0.3                # Creativity level
```

## 🆚 Old vs New Backend

| Feature           | Old (`app.py`) | New (`app_new.py`) |
| ----------------- | -------------- | ------------------ |
| Structure         | Monolithic     | Modular            |
| RAG               | ❌             | ✅                 |
| Groq Integration  | ❌             | ✅                 |
| Vector Store      | ❌             | ✅ FAISS           |
| Enhanced Feedback | Basic          | ✅ AI-powered      |
| Maintainability   | Hard           | ✅ Easy            |
| Configuration     | Hardcoded      | ✅ .env file       |

## 🐛 Troubleshooting

### "Groq API error"

- Check your API key in `.env`
- Verify internet connection
- Check Groq API status

### "RAG not working"

- Ensure RAG checkbox is enabled
- Upload study material file
- Check `.env` has `RAG_ENABLED=True`

### "Models not loading"

- Verify `Model/` directory exists
- Check all `.h5` and `.pkl` files present
- Ensure TensorFlow is installed

## 📚 Next Steps

1. ✅ Test with sample documents
2. ✅ Try different Groq models
3. ✅ Experiment with RAG parameters
4. ✅ Compare feedback quality with/without RAG
5. ✅ Read full documentation in `README_NEW.md`

## 🎉 Benefits of RAG

**Without RAG:**

```
Feedback: "Good answer with room for minor improvements.
Your answer shows good alignment with the model answer."
```

**With RAG:**

```
Feedback: "Excellent work! Your answer correctly identifies
supervised learning and provides relevant examples. However,
based on the study material provided, you could enhance your
response by including:

1. The mathematical formulation of the cost function
2. Discussion of overfitting prevention techniques mentioned
   in Chapter 3
3. Real-world applications from the case studies section

Specifically, the study material emphasizes..."
```

## 💡 Tips

- Upload comprehensive study materials for best results
- Use specific, detailed questions
- RAG works best with well-structured documents
- Monitor your Groq API usage (free tier limits)

---

**Ready to go?** Run `python app_new.py` and enjoy RAG-powered evaluations! 🚀
