// src/components/Footer.js
import React from 'react';

function Footer() {
  return (
    <footer id="about">
      <div className="footer-container">
        <div className="footer-logo">
          <i className="fa-solid fa-graduation-cap"></i>
          AI Answer Evaluator
        </div>
        <div className="footer-links">
          <a href="#home">Home</a>
          <a href="#services">Services</a>
          <a href="#about">About</a>
          <a href="#contact">Contact</a>
          <a href="#privacy">Privacy</a>
        </div>
        <div className="footer-social">
          <a href="https://facebook.com" target="_blank" rel="noopener noreferrer"><i className="fa-brands fa-facebook"></i></a>
          <a href="https://instagram.com" target="_blank" rel="noopener noreferrer"><i className="fa-brands fa-instagram"></i></a>
          <a href="https://twitter.com" target="_blank" rel="noopener noreferrer"><i className="fa-brands fa-twitter"></i></a>
          <a href="https://youtube.com" target="_blank" rel="noopener noreferrer"><i className="fa-brands fa-youtube"></i></a>
        </div>
        <div className="footer-credit">
          <p>© 2025 AI Answer Evaluator. All Rights Reserved.</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;