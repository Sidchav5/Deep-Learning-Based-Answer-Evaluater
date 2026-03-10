// src/components/Navbar.js
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    // Check if user is logged in
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    } else {
      setUser(null);
    }
  }, [location]); // Re-check when location changes

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDropdown]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setShowDropdown(false);
    navigate('/');
  };

  return (
    <nav className="nav-bar">
      <div className="nav-logo" onClick={() => navigate('/')}>
        <i className="fa-solid fa-graduation-cap"></i>
        <span className="nav-logo-text">AI Answer Evaluator</span>
      </div>
      <div className="nav-links">
        <a href="#home" className="nav-link" onClick={(e) => {
          if (location.pathname !== '/') {
            e.preventDefault();
            navigate('/');
            setTimeout(() => window.location.hash = 'home', 100);
          }
        }}>Home</a>
        <a href="#services" className="nav-link" onClick={(e) => {
          if (location.pathname !== '/') {
            e.preventDefault();
            navigate('/');
            setTimeout(() => window.location.hash = 'services', 100);
          }
        }}>Services</a>
        <a href="#about" className="nav-link" onClick={(e) => {
          if (location.pathname !== '/') {
            e.preventDefault();
            navigate('/');
            setTimeout(() => window.location.hash = 'about', 100);
          }
        }}>About</a>
      </div>
      <div className="nav-actions">
        {user ? (
          <div className="user-profile" onClick={() => setShowDropdown(!showDropdown)} ref={dropdownRef}>
            <div className="user-avatar">
              <i className="fa-solid fa-user"></i>
            </div>
            <div className="user-info">
              <span className="user-name">{user.name}</span>
              <span className="user-role">{user.role}</span>
            </div>
            <i className={`fa-solid fa-chevron-${showDropdown ? 'up' : 'down'}`}></i>
            
            {showDropdown && (
              <div className="user-dropdown">
                <div className="dropdown-header">
                  <p className="dropdown-user-name">{user.name}</p>
                  <p className="dropdown-user-email">{user.email}</p>
                </div>
                <div className="dropdown-divider"></div>
                <button className="dropdown-item">
                  <i className="fa-solid fa-user"></i>
                  Profile
                </button>
                <button className="dropdown-item">
                  <i className="fa-solid fa-gear"></i>
                  Settings
                </button>
                <div className="dropdown-divider"></div>
                <button className="dropdown-item logout-item" onClick={handleLogout}>
                  <i className="fa-solid fa-right-from-bracket"></i>
                  Logout
                </button>
              </div>
            )}
          </div>
        ) : (
          <>
            <button onClick={() => navigate('/login')} className="nav-btn nav-btn-secondary">Login</button>
            <button onClick={() => navigate('/signup')} className="nav-btn nav-btn-primary">Get Started</button>
          </>
        )}
      </div>
    </nav>
  );
}

export default Navbar;
