# AI Answer Evaluator - Setup Guide

## 🚀 Complete Setup Instructions

### Frontend Setup (React)

1. **Install dependencies:**

   ```bash
   cd frontend
   npm install react-router-dom
   ```

2. **Start the React development server:**
   ```bash
   npm start
   ```
   Frontend will run on `http://localhost:3000`

### Backend Setup (Flask)

1. **Navigate to backend directory:**

   ```bash
   cd backend
   ```

2. **Install Python dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Flask server:**
   ```bash
   python app.py
   ```
   Backend will run on `http://localhost:5000`

## 📋 Features Implemented

### Authentication System

- ✅ **Sign Up Page** - Users can register as Student or Teacher
- ✅ **Login Page** - Secure authentication with JWT tokens
- ✅ **Role-based accounts** - Two user roles (Student/Teacher)
- ✅ **Password hashing** - Secure password storage with Werkzeug
- ✅ **MongoDB integration** - Cloud database with connection string
- ✅ **JWT authentication** - Secure token-based sessions

### User Collections Schema

```javascript
{
  name: String,
  email: String (unique),
  password: String (hashed),
  role: "student" | "teacher",
  created_at: Date,
  updated_at: Date
}
```

## 🔐 MongoDB Configuration

**Connection String:**

```
mongodb+srv://DL_user:Edaigrp1@dl.pmyowfm.mongodb.net/
```

**Database:** `dl_database`  
**Collection:** `users`

## 📱 Using the Application

### Sign Up Flow:

1. Navigate to `/signup` or click "Get Started"
2. Fill in: Name, Email, Role (Student/Teacher), Password
3. Click "Sign Up"
4. Redirected to Login page

### Login Flow:

1. Navigate to `/login` or click "Login"
2. Enter email and password
3. Click "Login"
4. Token saved to localStorage
5. Redirected to home page

### API Routes:

- `POST /api/signup` - Register new user
- `POST /api/login` - Authenticate user
- `GET /api/verify` - Verify JWT token
- `GET /api/users` - Get all users (testing)

## 🎨 Pages Created

1. **Home Page** (`/`) - Landing page with hero section and services
2. **Sign Up Page** (`/signup`) - User registration
3. **Login Page** (`/login`) - User authentication

## 🔒 Security Features

- Password hashing (pbkdf2:sha256)
- JWT token authentication with expiration
- CORS enabled for secure cross-origin requests
- Input validation on both frontend and backend
- Secure MongoDB connection with credentials

## 📝 Next Steps (Future Implementation)

- [ ] Role-based access control (restrict features by role)
- [ ] Teacher dashboard (create evaluations)
- [ ] Student dashboard (take evaluations)
- [ ] Logout functionality
- [ ] Password reset/forgot password
- [ ] Protected routes
- [ ] User profile management

## 🐛 Troubleshooting

**Port 3000 already in use:**

```bash
# Kill the process and restart
npm start
```

**MongoDB connection error:**

- Check internet connection
- Verify MongoDB credentials
- Ensure IP whitelist in MongoDB Atlas

**CORS errors:**

- Ensure Flask backend is running
- Check CORS is enabled in Flask app

## 📦 Dependencies

**Frontend:**

- react-router-dom (routing)
- Font Awesome (icons)

**Backend:**

- Flask (web framework)
- Flask-CORS (CORS handling)
- PyMongo (MongoDB driver)
- PyJWT (JWT tokens)
- Werkzeug (password hashing)
