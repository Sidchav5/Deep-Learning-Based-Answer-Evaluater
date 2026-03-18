// src/components/Login.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../Auth.css';
import Navbar from './Navbar';

function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validation
    if (!formData.email || !formData.password) {
      setError('Please enter both email and password');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('http://localhost:5000/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok) {
        // Store user data and token
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        alert(`Welcome ${data.user.name}! You are logged in as ${data.user.role}.`);
        navigate('/');
      } else {
        setError(data.message || 'Login failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <i className="fa-solid fa-graduation-cap"></i>
          <h1>Welcome Back</h1>
          <p>Login to AI Answer Evaluator</p>
        </div>

        {error && (
          <div className="auth-error">
            <i className="fa-solid fa-circle-exclamation"></i>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">
              <i className="fa-solid fa-envelope"></i>
              Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">
              <i className="fa-solid fa-lock"></i>
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              disabled={loading}
            />
          </div>

          <div className="form-options">
            <label className="remember-me">
              <input type="checkbox" />
              <span>Remember me</span>
            </label>
            <button type="button" className="forgot-password">
              Forgot Password?
            </button>
          </div>

          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? (
              <>
                <i className="fa-solid fa-spinner fa-spin"></i>
                Logging in...
              </>
            ) : (
              <>
                <i className="fa-solid fa-right-to-bracket"></i>
                Login
              </>
            )}
          </button>
        </form>

        <div className="auth-divider">
          <span>OR</span>
        </div>

        <div className="auth-footer">
          <p>Don't have an account?</p>
          <button onClick={() => navigate('/signup')} className="auth-link-btn">
            Sign up here
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
