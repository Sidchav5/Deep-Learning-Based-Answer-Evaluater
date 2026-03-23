// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import HeroSection from './components/HeroSection';
import ServicesSection from './components/ServicesSection';
import Footer from './components/Footer';
import SignUp from './components/SignUp';
import Login from './components/Login';
import EvaluationPage from './components/EvaluationPage';
import WorkflowPage from './components/WorkflowPage';

// Home Page Component
function HomePage() {
  return (
    <>
      <HeroSection />
      <ServicesSection />
      <Footer />
    </>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/login" element={<Login />} />
        <Route path="/evaluate/*" element={<WorkflowPage />} />
        <Route path="/legacy-evaluate" element={<EvaluationPage />} />
      </Routes>
    </Router>
  );
}

export default App;
