// src/components/EvaluationPage.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../EvaluationPage.css';

function EvaluationPage() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    questionsFile: null,
    modelAnswersFile: null,
    studentAnswersFile: null,
    questionsText: '',
    modelAnswersText: '',
    studentAnswersText: ''
  });
  const [uploadMode, setUploadMode] = useState('file');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState({});
  const [activeTab, setActiveTab] = useState(0);
  const [uploadProgress, setUploadProgress] = useState({});

  // Handle drag events for file uploads
  const handleDrag = (e, fieldName) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(prev => ({ ...prev, [fieldName]: true }));
    } else if (e.type === "dragleave") {
      setDragActive(prev => ({ ...prev, [fieldName]: false }));
    }
  };

  const handleDrop = (e, fieldName) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(prev => ({ ...prev, [fieldName]: false }));
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFormData({
        ...formData,
        [fieldName]: e.dataTransfer.files[0]
      });
    }
  };

  const handleFileChange = (e) => {
    const { name, files } = e.target;
    if (files && files[0]) {
      // Simulate upload progress
      setUploadProgress(prev => ({ ...prev, [name]: 0 }));
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          const current = prev[name] || 0;
          if (current >= 100) {
            clearInterval(interval);
            return prev;
          }
          return { ...prev, [name]: current + 10 };
        });
      }, 50);

      setFormData({
        ...formData,
        [name]: files[0]
      });

      // Clear progress after "upload"
      setTimeout(() => {
        clearInterval(interval);
        setUploadProgress(prev => ({ ...prev, [name]: 100 }));
        setTimeout(() => {
          setUploadProgress(prev => ({ ...prev, [name]: undefined }));
        }, 500);
      }, 500);
    }
  };

  const handleTextChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResults(null);

    // Check if user is logged in
    const token = localStorage.getItem('token');
    if (!token) {
      setError('Please log in to use the evaluation feature');
      setTimeout(() => navigate('/login'), 2000);
      return;
    }

    // Validation
    if (uploadMode === 'file') {
      if (!formData.questionsFile || !formData.modelAnswersFile || !formData.studentAnswersFile) {
        setError('Please upload Questions, Model Answers, and Student Answers files');
        return;
      }
    } else {
      if (!formData.questionsText || !formData.modelAnswersText || !formData.studentAnswersText) {
        setError('Please fill in Questions, Model Answers, and Student Answers');
        return;
      }
    }

    setLoading(true);

    try {
      const formDataToSend = new FormData();
      
      if (uploadMode === 'file') {
        formDataToSend.append('questionsFile', formData.questionsFile);
        formDataToSend.append('modelAnswersFile', formData.modelAnswersFile);
        formDataToSend.append('studentAnswersFile', formData.studentAnswersFile);
      } else {
        formDataToSend.append('questionsText', formData.questionsText);
        formDataToSend.append('modelAnswersText', formData.modelAnswersText);
        formDataToSend.append('studentAnswersText', formData.studentAnswersText);
      }
      
      formDataToSend.append('uploadMode', uploadMode);

      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/api/evaluate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formDataToSend
      });

      const data = await response.json();

      if (response.ok) {
        setResults(data);
        // Scroll to results
        setTimeout(() => {
          document.getElementById('results-section')?.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
          });
        }, 100);
      } else {
        if (response.status === 401) {
          setError('Session expired. Please log in again.');
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setTimeout(() => navigate('/login'), 2000);
        } else if (response.status === 503) {
          setError('ML models are not loaded. Please contact administrator or wait for models to load.');
        } else {
          setError(data.message || 'Evaluation failed');
        }
      }
    } catch (error) {
      setError('Network error. Please ensure the backend server is running.');
      console.error('Evaluation error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFormData({
      questionsFile: null,
      modelAnswersFile: null,
      studentAnswersFile: null,
      questionsText: '',
      modelAnswersText: '',
      studentAnswersText: ''
    });
    setResults(null);
    setError('');
    setActiveTab(0);
  };

  const handleDownloadReport = () => {
    if (!results) return;

    const currentDate = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    // Generate HTML report
    const htmlContent = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Report - ${currentDate}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            color: #1a202c;
        }
        
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .report-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem 2rem;
            text-align: center;
        }
        
        .report-header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        
        .report-header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .summary-section {
            padding: 2rem;
            background: #f7fafc;
            border-bottom: 3px solid #e2e8f0;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-top: 1.5rem;
        }
        
        .summary-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            border-left: 4px solid #667eea;
        }
        
        .summary-card h3 {
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #718096;
            margin-bottom: 0.75rem;
        }
        
        .summary-card .value {
            font-size: 2rem;
            font-weight: 800;
            color: #667eea;
        }
        
        .summary-card .percentage {
            font-size: 1.25rem;
            color: #48bb78;
            margin-top: 0.5rem;
        }
        
        .questions-section {
            padding: 2rem;
        }
        
        .question-card {
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            page-break-inside: avoid;
        }
        
        .question-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e2e8f0;
        }
        
        .question-number {
            font-size: 1.5rem;
            font-weight: 700;
            color: #667eea;
        }
        
        .score-badge {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 0.5rem 1.5rem;
            border-radius: 20px;
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        .question-text {
            background: #f7fafc;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            border-left: 4px solid #667eea;
        }
        
        .question-text strong {
            color: #667eea;
            display: block;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            font-size: 0.875rem;
            letter-spacing: 0.5px;
        }
        
        .answers-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        .answer-box {
            background: #f7fafc;
            padding: 1.5rem;
            border-radius: 8px;
            border: 2px solid #e2e8f0;
        }
        
        .answer-box h4 {
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .model-answer h4 {
            color: #48bb78;
        }
        
        .student-answer h4 {
            color: #4299e1;
        }
        
        .answer-box p {
            line-height: 1.7;
            color: #2d3748;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            padding: 1.5rem;
            background: #edf2f7;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .metric-item {
            text-align: center;
        }
        
        .metric-item span {
            display: block;
            font-size: 0.875rem;
            color: #718096;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .metric-item strong {
            font-size: 1.5rem;
            color: #2d3748;
        }
        
        .nli-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: capitalize;
        }
        
        .nli-badge.entailment {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .nli-badge.neutral {
            background: #feebc8;
            color: #7c2d12;
        }
        
        .nli-badge.contradiction {
            background: #fed7d7;
            color: #742a2a;
        }
        
        .feedback-box {
            background: #edf2f7;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            font-style: italic;
            color: #2d3748;
            line-height: 1.7;
        }
        
        .footer {
            background: #2d3748;
            color: white;
            padding: 2rem;
            text-align: center;
        }
        
        .footer p {
            opacity: 0.8;
        }
        
        @media print {
            body {
                background: white;
                padding: 0;
            }
            
            .report-container {
                box-shadow: none;
            }
        }
        
        @media (max-width: 768px) {
            .answers-grid {
                grid-template-columns: 1fr;
            }
            
            .summary-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="report-container">
        <!-- Header -->
        <div class="report-header">
            <h1>📊 Evaluation Report</h1>
            <p>Generated on ${currentDate}</p>
        </div>
        
        <!-- Summary Section -->
        <div class="summary-section">
            <h2 style="color: #2d3748; margin-bottom: 1rem;">Overall Performance</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Total Score</h3>
                    <div class="value">${Math.round(results.totalScore)}/${results.totalMaxMarks}</div>
                    <div class="percentage">${results.percentage.toFixed(1)}%</div>
                </div>
                <div class="summary-card">
                    <h3>Total Questions</h3>
                    <div class="value">${results.totalQuestions}</div>
                </div>
                <div class="summary-card">
                    <h3>Average Similarity</h3>
                    <div class="value">${(results.averageSimilarity * 100).toFixed(1)}%</div>
                </div>
            </div>
        </div>
        
        <!-- Questions Section -->
        <div class="questions-section">
            <h2 style="color: #2d3748; margin-bottom: 2rem;">Detailed Analysis</h2>
            ${results.questions.map((q, index) => `
                <div class="question-card">
                    <div class="question-header">
                        <div class="question-number">Question ${index + 1}</div>
                        <div class="score-badge">${Math.round(q.score)} / ${q.maxMarks}</div>
                    </div>
                    
                    <div class="question-text">
                        <strong>Question:</strong>
                        <p>${q.question}</p>
                    </div>
                    
                    <div class="answers-grid">
                        <div class="answer-box model-answer">
                            <h4>✓ Model Answer</h4>
                            <p>${q.modelAnswer}</p>
                        </div>
                        <div class="answer-box student-answer">
                            <h4>👤 Student Answer</h4>
                            <p>${q.studentAnswer}</p>
                        </div>
                    </div>
                    
                    <div class="metrics">
                        <div class="metric-item">
                            <span>Similarity Score</span>
                            <strong>${(q.similarity * 100).toFixed(0)}%</strong>
                        </div>
                        <div class="metric-item">
                            <span>NLI Result</span>
                            <strong><span class="nli-badge ${q.nliLabel.toLowerCase()}">${q.nliLabel}</span></strong>
                        </div>
                    </div>
                    
                    <div class="feedback-box">
                        <strong style="color: #667eea; font-style: normal; display: block; margin-bottom: 0.5rem;">💬 Feedback:</strong>
                        ${q.feedback}
                    </div>
                </div>
            `).join('')}
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p>AI-Powered Answer Evaluation System</p>
            <p style="margin-top: 0.5rem; font-size: 0.875rem;">This report was automatically generated by the evaluation system.</p>
        </div>
    </div>
</body>
</html>
    `;

    // Create blob and download
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evaluation-report-${new Date().getTime()}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const removeFile = (fieldName) => {
    setFormData({
      ...formData,
      [fieldName]: null
    });
  };

  return (
    <div className="evaluation-page">
      {/* Animated Background Elements */}
      <div className="bg-orb or-1"></div>
      <div className="bg-orb or-2"></div>
      <div className="bg-orb or-3"></div>
      <div className="grid-pattern"></div>

      {/* Navigation */}
      <nav className="eval-nav glass-effect">
        <button onClick={() => navigate(-1)} className="back-btn">
          <i className="fa-solid fa-arrow-left"></i>
          <span>Back</span>
        </button>
        <div className="eval-nav-title">
          <i className="fa-solid fa-robot"></i>
          <span>AI Evaluation Studio</span>
        </div>
        <div className="nav-status">
          <span className="status-indicator"></span>
          <span>Online</span>
        </div>
      </nav>

      <div className="eval-container">
        {/* Header Section */}
        <div className="eval-header glass-card">
          <div className="header-badge">
            <span className="badge-pulse">⚡ AI-Powered</span>
          </div>
          <h1 className="gradient-text">
            Answer Evaluation System
          </h1>
          <p className="header-description">
            Upload documents or enter text for batch evaluation with advanced AI models
          </p>
          
          {/* Format Info Cards */}
          <div className="format-cards">
            <div className="format-card">
              <div className="format-icon">📝</div>
              <h4>Questions Format</h4>
              <code>Q1: [5 marks] What is AI?</code>
              <code>Q2: [10 marks] Explain ML?</code>
            </div>
            <div className="format-card">
              <div className="format-icon">✓</div>
              <h4>Model Answers</h4>
              <code>A1: AI is the simulation...</code>
              <code>A2: ML is a subset...</code>
            </div>
            <div className="format-card">
              <div className="format-icon">👤</div>
              <h4>Student Answers</h4>
              <code>A1: Artificial Intelligence...</code>
              <code>A2: Machine learning uses...</code>
            </div>
          </div>
        </div>

        {/* Mode Toggle with Animation */}
        <div className="mode-toggle-container">
          <div className="mode-toggle glass-effect">
            <button 
              className={`mode-btn ${uploadMode === 'file' ? 'active' : ''}`}
              onClick={() => setUploadMode('file')}
            >
              <i className="fa-solid fa-cloud-upload-alt"></i>
              <span>Upload Files</span>
            </button>
            <button 
              className={`mode-btn ${uploadMode === 'text' ? 'active' : ''}`}
              onClick={() => setUploadMode('text')}
            >
              <i className="fa-solid fa-pen-to-square"></i>
              <span>Enter Text</span>
            </button>
          </div>
        </div>

        {/* Error Display with Animation */}
        {error && (
          <div className="error-message glass-card">
            <i className="fa-solid fa-circle-exclamation"></i>
            <div className="error-content">
              <strong>Error</strong>
              <p>{error}</p>
            </div>
            <button onClick={() => setError('')} className="close-error">
              <i className="fa-solid fa-times"></i>
            </button>
          </div>
        )}

        {/* Main Form */}
        <form onSubmit={handleSubmit} className="eval-form glass-card">
          {uploadMode === 'file' ? (
            <>
              {/* File Upload Sections */}
              <div className="form-grid">
                <FileUploadSection
                  title="Questions Document"
                  icon="fa-solid fa-list-ol"
                  fieldName="questionsFile"
                  formData={formData}
                  dragActive={dragActive}
                  uploadProgress={uploadProgress}
                  onFileChange={handleFileChange}
                  onDrag={handleDrag}
                  onDrop={handleDrop}
                  onRemove={removeFile}
                  disabled={loading}
                  hint="Format: Q1: [5 marks] Question? | Q2: [10 marks] Question?"
                />

                <FileUploadSection
                  title="Model Answers"
                  icon="fa-solid fa-check-double"
                  fieldName="modelAnswersFile"
                  formData={formData}
                  dragActive={dragActive}
                  uploadProgress={uploadProgress}
                  onFileChange={handleFileChange}
                  onDrag={handleDrag}
                  onDrop={handleDrop}
                  onRemove={removeFile}
                  disabled={loading}
                  hint="Format: A1: Model answer | A2: Model answer"
                />

                <FileUploadSection
                  title="Student Answers"
                  icon="fa-solid fa-file-lines"
                  fieldName="studentAnswersFile"
                  formData={formData}
                  dragActive={dragActive}
                  uploadProgress={uploadProgress}
                  onFileChange={handleFileChange}
                  onDrag={handleDrag}
                  onDrop={handleDrop}
                  onRemove={removeFile}
                  disabled={loading}
                  hint="Format: A1: Student answer | A2: Student answer"
                />
              </div>

            </>
          ) : (
            <>
              {/* Text Input Sections */}
              <div className="text-input-grid">
                <TextInputSection
                  title="Questions"
                  icon="fa-solid fa-list-ol"
                  name="questionsText"
                  value={formData.questionsText}
                  onChange={handleTextChange}
                  placeholder="Q1: [5 marks] What is machine learning? | Q2: [10 marks] Explain deep learning."
                  rows={6}
                  disabled={loading}
                  hint="Separate with ' | ' and include marks in [X marks]"
                />

                <TextInputSection
                  title="Model Answers"
                  icon="fa-solid fa-check-double"
                  name="modelAnswersText"
                  value={formData.modelAnswersText}
                  onChange={handleTextChange}
                  placeholder="A1: Machine learning is a subset of AI... | A2: Deep learning uses neural networks..."
                  rows={8}
                  disabled={loading}
                  hint="Separate answers with ' | ' matching question order"
                />

                <TextInputSection
                  title="Student Answers"
                  icon="fa-solid fa-file-lines"
                  name="studentAnswersText"
                  value={formData.studentAnswersText}
                  onChange={handleTextChange}
                  placeholder="A1: ML is about teaching computers... | A2: Deep learning involves multiple layers..."
                  rows={8}
                  disabled={loading}
                  hint="Separate answers with ' | ' in same order as questions"
                />
              </div>
            </>
          )}

          {/* Action Buttons */}
          <div className="form-actions">
            <button 
              type="button" 
              onClick={handleReset} 
              className="reset-btn"
              disabled={loading}
            >
              <i className="fa-solid fa-rotate-right"></i>
              <span>Reset All</span>
            </button>
            <button 
              type="submit" 
              className="submit-btn"
              disabled={loading}
            >
              {loading ? (
                <>
                  <i className="fa-solid fa-circle-notch fa-spin"></i>
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <i className="fa-solid fa-brain"></i>
                  <span>Evaluate Answers</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Results Section */}
        {results && (
          <div id="results-section" className="results-section glass-card">
            <div className="results-header">
              <h2>
                <i className="fa-solid fa-chart-line"></i>
                Evaluation Results
              </h2>
              <button onClick={handleReset} className="new-eval-btn">
                <i className="fa-solid fa-plus"></i>
                New Evaluation
              </button>
            </div>
            
            {/* Overall Stats */}
            <div className="stats-grid">
              <div className="stat-card premium">
                <div className="stat-icon">📊</div>
                <div className="stat-content">
                  <span className="stat-label">Total Score</span>
                  <div className="stat-value">
                    <span className="big-number">{results.totalScore}</span>
                    <span className="stat-max">/{results.totalMaxMarks}</span>
                  </div>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{width: `${results.percentage}%`}}
                    ></div>
                  </div>
                  <span className="percentage">{results.percentage}%</span>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">❓</div>
                <div className="stat-content">
                  <span className="stat-label">Questions</span>
                  <span className="stat-number">{results.totalQuestions}</span>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">📈</div>
                <div className="stat-content">
                  <span className="stat-label">Avg. Similarity</span>
                  <span className="stat-number">
                    {(results.averageSimilarity * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Individual Questions with Tabs */}
            <div className="questions-tabs">
              <div className="tabs-header">
                {results.questions && results.questions.map((_, index) => (
                  <button
                    key={index}
                    className={`tab-btn ${activeTab === index ? 'active' : ''}`}
                    onClick={() => setActiveTab(index)}
                  >
                    Q{index + 1}
                    <span className={`tab-status ${results.questions[index].nliLabel.toLowerCase()}`}>
                      {results.questions[index].score}/{results.questions[index].maxMarks}
                    </span>
                  </button>
                ))}
              </div>

              {results.questions && results.questions.map((q, index) => (
                <div 
                  key={index} 
                  className={`tab-panel ${activeTab === index ? 'active' : ''}`}
                >
                  <div className="question-analysis">
                    <div className="question-text">
                      <strong>Question:</strong>
                      <p>{q.question}</p>
                    </div>

                    <div className="answers-comparison">
                      <div className="answer-card model">
                        <div className="answer-header">
                          <i className="fa-solid fa-check-circle"></i>
                          <h4>Model Answer</h4>
                        </div>
                        <p>{q.modelAnswer}</p>
                      </div>

                      <div className="answer-card student">
                        <div className="answer-header">
                          <i className="fa-solid fa-user-graduate"></i>
                          <h4>Student Answer</h4>
                        </div>
                        <p>{q.studentAnswer}</p>
                      </div>
                    </div>

                    <div className="metrics-grid">
                      <div className="metric-item">
                        <span className="metric-label">Similarity Score</span>
                        <div className="metric-value-large">
                          <div className="circular-progress">
                            <svg viewBox="0 0 36 36">
                              <path
                                d="M18 2.0845
                                  a 15.9155 15.9155 0 0 1 0 31.831
                                  a 15.9155 15.9155 0 0 1 0 -31.831"
                                fill="none"
                                stroke="rgba(139, 92, 246, 0.2)"
                                strokeWidth="3"
                              />
                              <path
                                d="M18 2.0845
                                  a 15.9155 15.9155 0 0 1 0 31.831
                                  a 15.9155 15.9155 0 0 1 0 -31.831"
                                fill="none"
                                stroke="url(#gradient)"
                                strokeWidth="3"
                                strokeDasharray={`${q.similarity * 100}, 100`}
                              />
                            </svg>
                            <span className="percentage">
                              {(q.similarity * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="metric-item">
                        <span className="metric-label">NLI Result</span>
                        <div className={`nli-badge-large ${q.nliLabel.toLowerCase()}`}>
                          <i className={`fa-solid ${
                            q.nliLabel === 'entailment' ? 'fa-check-circle' :
                            q.nliLabel === 'neutral' ? 'fa-minus-circle' :
                            'fa-times-circle'
                          }`}></i>
                          <span>{q.nliLabel}</span>
                        </div>
                      </div>

                      <div className="metric-item full-width">
                        <span className="metric-label">Feedback</span>
                        <div className="feedback-bubble">
                          <i className="fa-solid fa-quote-left"></i>
                          <p>{q.feedback}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Download Options */}
            <div className="results-footer">
              <button className="download-btn" onClick={handleDownloadReport}>
                <i className="fa-solid fa-download"></i>
                Download Report
              </button>
              <button className="share-btn">
                <i className="fa-solid fa-share-alt"></i>
                Share Results
              </button>
            </div>
          </div>
        )}
      </div>

      {/* SVG Gradient Definition */}
      <svg style={{position: 'absolute', width: 0, height: 0}}>
        <defs>
          <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8B5CF6" />
            <stop offset="100%" stopColor="#60A5FA" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

// Sub-components for better organization
const FileUploadSection = ({ 
  title, icon, fieldName, formData, dragActive, uploadProgress,
  onFileChange, onDrag, onDrop, onRemove, disabled, hint 
}) => (
  <div className="file-section">
    <h3 className="section-title">
      <i className={icon}></i>
      {title}
    </h3>
    <div 
      className={`file-upload-area ${dragActive[fieldName] ? 'drag-active' : ''} ${formData[fieldName] ? 'has-file' : ''}`}
      onDragEnter={(e) => onDrag(e, fieldName)}
      onDragLeave={(e) => onDrag(e, fieldName)}
      onDragOver={(e) => onDrag(e, fieldName)}
      onDrop={(e) => onDrop(e, fieldName)}
    >
      <input
        type="file"
        id={fieldName}
        name={fieldName}
        accept=".txt,.doc,.docx,.pdf"
        onChange={onFileChange}
        disabled={disabled}
      />
      <label htmlFor={fieldName} className="file-label">
        {!formData[fieldName] ? (
          <>
            <div className="upload-icon">
              <i className="fa-solid fa-cloud-upload-alt"></i>
            </div>
            <div className="upload-text">
              <strong>Click to upload or drag and drop</strong>
              <small>Supported: TXT, DOC, DOCX, PDF</small>
            </div>
          </>
        ) : (
          <div className="file-info">
            <div className="file-details">
              <i className="fa-solid fa-file"></i>
              <div>
                <span className="file-name">{formData[fieldName].name}</span>
                <span className="file-size">
                  {(formData[fieldName].size / 1024).toFixed(2)} KB
                </span>
              </div>
            </div>
            {uploadProgress[fieldName] !== undefined && (
              <div className="upload-progress">
                <div 
                  className="progress-bar" 
                  style={{width: `${uploadProgress[fieldName]}%`}}
                ></div>
              </div>
            )}
            <button 
              type="button" 
              className="remove-file"
              onClick={() => onRemove(fieldName)}
            >
              <i className="fa-solid fa-times"></i>
            </button>
          </div>
        )}
      </label>
    </div>
    {hint && <small className="input-hint">{hint}</small>}
  </div>
);

const TextInputSection = ({ title, icon, name, value, onChange, placeholder, rows, disabled, hint }) => (
  <div className="text-section">
    <h3 className="section-title">
      <i className={icon}></i>
      {title}
    </h3>
    <div className="text-input-wrapper">
      <textarea
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
        className="text-input"
      />
      <div className="input-stats">
        <span>{value.split('|').length} answers</span>
        <span>{value.length} characters</span>
      </div>
    </div>
    {hint && <small className="input-hint">{hint}</small>}
  </div>
);

export default EvaluationPage;