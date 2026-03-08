# Backend README

## Flask Authentication API

### Setup Instructions

1. **Install Python dependencies:**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run the Flask server:**
   ```bash
   python app.py
   ```
   Server will start on `http://localhost:5000`

### API Endpoints

#### 1. Sign Up

- **URL:** `POST /api/signup`
- **Body:**
  ```json
  {
    "name": "John Doe",
    "email": "john@example.com",
    "password": "password123",
    "role": "student"
  }
  ```
- **Response:** `201 Created`

#### 2. Login

- **URL:** `POST /api/login`
- **Body:**
  ```json
  {
    "email": "john@example.com",
    "password": "password123"
  }
  ```
- **Response:**
  ```json
  {
    "token": "jwt_token_here",
    "user": {
      "id": "user_id",
      "name": "John Doe",
      "email": "john@example.com",
      "role": "student"
    }
  }
  ```

#### 3. Verify Token

- **URL:** `GET /api/verify`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `200 OK` with user details

### MongoDB Schema

**Users Collection:**

```javascript
{
  _id: ObjectId,
  name: String,
  email: String (unique, indexed),
  password: String (hashed),
  role: String (enum: ['student', 'teacher']),
  created_at: Date,
  updated_at: Date
}
```

### Security Features

- Password hashing with Werkzeug (pbkdf2:sha256)
- JWT token authentication
- CORS enabled for frontend communication
- Token expiration (24 hours default)
