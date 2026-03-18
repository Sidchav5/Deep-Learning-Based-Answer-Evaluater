// src/components/HeroSection.js
import React from 'react';
import Navbar from './Navbar';

function HeroSection() {
  return (
    <header id="home">
      <div className="hero-section">
        <Navbar />
        <div className="poster">
          <h1 className="poster-name">
            <i className="fa-solid fa-graduation-cap"></i>
            AI Answer Evaluator
          </h1>
          <div className="poster-info">
            <p>
              <strong className="Sid">Intelligent Grading Through Deep Learning</strong>
            </p>
            <p>
              Save hours of grading time while providing <strong>fair and consistent evaluations</strong>. 
              Perfect for educators, institutions, and online learning platforms—our AI understands context 
              and meaning, not just keywords. Upload questions and answers, get instant intelligent feedback, 
              and focus more on teaching while we handle the evaluation.
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}

export default HeroSection;
