# Backend API Documentation

## 🏗️ Project Structure

```
backend/
├── app.py                      # Main application entry point (new)
├── app_new.py                  # Refactored application
├── config/                     # Configuration modules
│   ├── __init__.py
│   └── settings.py            # App settings and environment variables
├── models/                     # ML model management
│   ├── __init__.py
│   └── ml_models.py           # SBERT, NLI, ANN model loader
├── services/                   # Business logic
│   ├── __init__.py
│   ├── evaluation_service.py  # Answer evaluation logic
│   └── rag_service.py         # RAG with Groq API integration
├── routes/                     # API endpoints
│   ├── __init__.py
│   ├── auth_routes.py         # Authentication endpoints
│   └── evaluation_routes.py   # Evaluation endpoints
├── utils/                      # Helper functions
│   ├── __init__.py
│   ├── auth.py                # JWT utilities
│   ├── file_processing.py     # File extraction utilities
│   └── parsers.py             # Q&A parsing utilities
├── uploads/                    # Temporary file storage
├── vector_store/              # FAISS vector store storage
├── .env                        # Environment variables (create from .env.example)
├── .env.example               # Environment template
└── requirements.txt           # Python dependencies
```

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` and add your **Groq API Key**:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get your Groq API key from: https://console.groq.com/

### 3. Run the Application

**Option 1: Use new refactored version (recommended)**

```bash
python app_new.py
```

**Option 2: Keep existing version**

```bash
python app.py
```

## 📡 API Endpoints

### Authentication Routes (`/api/auth`)

#### 1. **Sign Up**

- **POST** `/api/auth/signup`
- **Body:**

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword",
  "role": "teacher" // or "student"
}
```

- **Response:**

```json
{
  "message": "User registered successfully",
  "token": "jwt_token_here",
  "user": {
    "id": "user_id",
    "name": "John Doe",
    "email": "john@example.com",
    "role": "teacher"
  }
}
```

#### 2. **Login**

- **POST** `/api/auth/login`
- **Body:**

```json
{
  "email": "john@example.com",
  "password": "securepassword"
}
```

#### 3. **Verify Token**

- **GET** `/api/auth/verify`
- **Headers:** `Authorization: Bearer <token>`

### Evaluation Routes (`/api`)

#### 1. **Batch Evaluation** (with RAG support)

- **POST** `/api/evaluate`
- **Headers:** `Authorization: Bearer <token>`
- **Form Data (File Mode):**
  - `uploadMode`: "file"
  - `questionsFile`: File
  - `modelAnswersFile`: File
  - `studentAnswersFile`: File
  - `useRAG`: "true" or "false"
  - `studyMaterialFile`: File (optional, required if useRAG=true)

- **Form Data (Text Mode):**
  - `uploadMode`: "text"
  - `questionsText`: Text
  - `modelAnswersText`: Text
  - `studentAnswersText`: Text
  - `useRAG`: "true" or "false"

- **Response:**

```json
{
  "message": "Evaluation completed successfully",
  "totalScore": 46.06,
  "totalMaxMarks": 75,
  "percentage": 61.41,
  "totalQuestions": 10,
  "averageSimilarity": 0.8395,
  "questions": [
    {
      "questionNumber": 1,
      "question": "What is AI?",
      "modelAnswer": "AI is...",
      "studentAnswer": "Artificial Intelligence is...",
      "score": 3.69,
      "maxMarks": 5,
      "similarity": 0.918,
      "nliLabel": "entailment",
      "feedback": "Excellent work! Your answer shows high semantic similarity...",
      "ragEnabled": true,
      "contextUsed": 3
    }
  ]
}
```

#### 2. **Ingest Study Material** (RAG)

- **POST** `/api/rag/ingest`
- **Headers:** `Authorization: Bearer <token>`
- **Form Data:**
  - `file`: File (PDF, DOCX, TXT)
  - OR `text`: Raw text

#### 3. **Clear RAG Store**

- **POST** `/api/rag/clear`
- **Headers:** `Authorization: Bearer <token>`

#### 4. **Health Check**

- **GET** `/api/health`
- **Response:**

```json
{
  "status": "healthy",
  "models_loaded": true,
  "rag_enabled": true,
  "groq_configured": true
}
```

## 🧠 RAG System Features

### How RAG Works

1. **Document Ingestion:**
   - Study material is split into chunks (500 words with 50-word overlap)
   - Each chunk is embedded using SBERT (all-MiniLM-L6-v2)
   - Embeddings stored in FAISS vector database

2. **Retrieval:**
   - When evaluating, relevant chunks are retrieved based on question + student answer
   - Top-K similar chunks (default: 3) are selected

3. **Enhanced Feedback with Groq:**
   - Retrieved context + evaluation metrics sent to Groq LLM
   - Groq generates detailed, constructive feedback
   - References study material in feedback

### Configuration Options

Edit `.env` to customize RAG behavior:

```env
RAG_ENABLED=True                    # Enable/disable RAG
RAG_CHUNK_SIZE=500                  # Words per chunk
RAG_CHUNK_OVERLAP=50                # Overlap between chunks
RAG_TOP_K=3                         # Number of chunks to retrieve
RAG_SIMILARITY_THRESHOLD=0.3        # Minimum similarity score

GROQ_MODEL=llama-3.3-70b-versatile  # Groq model to use
GROQ_MAX_TOKENS=1024                # Max response length
GROQ_TEMPERATURE=0.3                # Creativity (0=deterministic, 1=creative)
```

## 🔧 Migration from Old to New Structure

The new architecture provides:

✅ **Modular Design** - Separated concerns (routes, services, models, utils)
✅ **RAG Integration** - Groq-powered enhanced feedback  
✅ **Better Maintainability** - Easier to test and extend
✅ **Configuration Management** - Environment-based settings
✅ **Singleton Pattern** - Efficient model loading and caching

### To migrate:

1. Install new dependencies: `pip install groq faiss-cpu`
2. Create `.env` from `.env.example`
3. Add your Groq API key
4. Run `python app_new.py` instead of `python app.py`

## 🎯 Testing the RAG System

1. **Start the server:**

```bash
python app_new.py
```

2. **Test health check:**

```bash
curl http://localhost:5000/api/health
```

3. **Login and get token:**

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}'
```

4. **Evaluate with RAG:**
   Upload files through the frontend with RAG checkbox enabled, or use curl with form data.

## 📊 Performance Notes

- First request may be slower (model loading)
- Subsequent requests are cached and fast
- RAG adds ~2-3 seconds per evaluation (Groq API latency)
- Vector store persists between sessions

## 🔐 Security Notes

- Always use HTTPS in production
- Keep `.env` file secret (never commit to Git)
- Rotate JWT secret keys regularly
- Use strong passwords for MongoDB
- Rate limit API endpoints in production

## 📝 Development Tips

- Use `DEBUG=True` in `.env` for detailed error messages
- Check logs for ML model loading status
- Monitor Groq API usage (free tier has limits)
- Clear vector store if study material changes: `POST /api/rag/clear`

## 🆘 Troubleshooting

**Models not loading?**

- Check if Model/ directory exists with .h5 and .pkl files
- Ensure all ML dependencies are installed

**Groq API errors?**

- Verify API key is correct in `.env`
- Check Groq API rate limits
- Ensure internet connection is available

**RAG not working?**

- Confirm `RAG_ENABLED=True` in `.env`
- Check if GROQ_API_KEY is set
- Verify study material was uploaded

**MongoDB connection issues?**

- Check MONGO_URI in `.env`
- Ensure network allows MongoDB Atlas connections
- Verify credentials are correct
