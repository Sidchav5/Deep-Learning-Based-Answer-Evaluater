# 🤖 AI Answer Evaluator

An intelligent answer evaluation system powered by an external Colab/Kaggle Llama pipeline for reference answer generation and scoring.

## 🌟 Features

- **🎯 Automatic Answer Evaluation**: Llama pipeline-based grading with semantic and keyword-aware scoring
- **📊 Multi-Metric Scoring**: Evaluates answers on similarity, grading labels, and marks
- **🤖 Llama Pipeline Integration**: Uses your external Colab/Kaggle FastAPI pipeline for answer generation and scoring
- **👥 Role-Based System**: Separate interfaces for teachers and students
- **🔐 Secure Authentication**: JWT-based authentication with MongoDB
- **📁 Document Processing**: Support for DOCX and PDF files
- **🎨 Modern UI**: Clean, responsive React frontend

## 🏗️ Architecture

```
├── backend/           # Flask API server
│   ├── services/     # Evaluation and external Llama client
│   ├── routes/       # API endpoints
│   └── utils/        # Helper functions
├── frontend/         # React application
└── uploads/          # Document storage
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+
- MongoDB Atlas account
- Running Colab/Kaggle Llama FastAPI endpoint (ngrok URL)

### Backend Setup

1. **Navigate to backend:**
   ```bash
   cd backend
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your credentials:
   ```env
   MONGO_URI=your_mongodb_connection_string
   SECRET_KEY=your_secret_key
   LLAMA_API_BASE_URL=https://overjealous-kimberley-nonoperative.ngrok-free.app
   ```

4. **Run the server:**
   ```bash
   python main.py
   ```
   Backend runs on `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```
   Frontend runs on `http://localhost:3000`

## 📖 Documentation

- [Setup Guide](SETUP_GUIDE.md) - Detailed setup instructions
- [Backend API](backend/README.md) - API documentation
- [Quickstart](backend/QUICKSTART.md) - Get started quickly

## 🎯 How It Works

1. **Teacher uploads** model answers and question papers
2. **Students submit** their answers in DOCX/PDF format
3. **AI evaluates** answers using your external Llama scoring pipeline
4. **Results provided** with detailed scores and AI feedback

## 🔧 Technology Stack

### Backend
- **Framework**: Flask
- **Database**: MongoDB Atlas
- **AI Integration**: External Llama FastAPI endpoint from Colab/Kaggle notebook

### Frontend
- **Framework**: React
- **Routing**: React Router
- **Styling**: CSS3
- **HTTP Client**: Fetch API

## 📊 Evaluation Metrics

The system evaluates answers across multiple dimensions:

- **Semantic Similarity**: Measures meaning alignment with model answer
- **Relevance Score**: Checks if answer addresses the question
- **Completeness**: Evaluates coverage of key points
- **Clarity**: Assesses writing quality and structure
- **Keyword Match**: Traditional keyword-based scoring
- **Overall Score**: Weighted combination of all metrics

## 🔐 Security Features

- JWT-based authentication
- Password hashing with Werkzeug
- Environment variable configuration
- Secure file upload handling
- Role-based access control

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is developed as part of an academic project.

## 👥 Team

Developed by the Deep Learning team.

## 🙏 Acknowledgments

- Llama pipeline for AI inference and grading
- MongoDB for database services
- All open-source contributors

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This is an educational project for demonstrating AI-powered answer evaluation systems.