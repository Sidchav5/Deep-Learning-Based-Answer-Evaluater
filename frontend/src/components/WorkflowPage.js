import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../WorkflowPage.css';
import Navbar from './Navbar';

const API_BASE = 'http://localhost:5000/api';

function WorkflowPage() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const [teacherForm, setTeacherForm] = useState({
    title: '',
    subject: '',
    dueDate: '',
    questionsFile: null,
    modelAnswersFile: null,
    studyMaterialFile: null,
    inputMode: 'file'
  });
  const [, setTeacherAssignments] = useState([]);
  const [selectedAssignmentId] = useState('');
  const [teacherSubmissions, setTeacherSubmissions] = useState([]);
  const [teacherOverrides, setTeacherOverrides] = useState({
    questionsFile: null,
    modelAnswersFile: null,
    studentAnswersFile: null,
    studyMaterialFile: null,
    inputMode: 'file',
    questionsText: '',
    studentAnswersText: '',
    marksValue: 5
  });

  const [studentSubject, setStudentSubject] = useState('');
  const [studentAssignments, setStudentAssignments] = useState([]);
  const [studentAssignmentId, setStudentAssignmentId] = useState('');
  const [studentAnswersFile, setStudentAnswersFile] = useState(null);
  const [studentSubmissions, setStudentSubmissions] = useState([]);
  const [studentResult, setStudentResult] = useState(null);

  const getToken = useCallback(() => localStorage.getItem('token'), []);

  const getAuthHeaders = useCallback(() => ({
    Authorization: `Bearer ${getToken()}`
  }), [getToken]);

  const formatDateTime = (value) => {
    if (!value) {
      return '-';
    }
    try {
      return new Date(value).toLocaleString();
    } catch (e) {
      return value;
    }
  };

  const normalizeAnswerText = (value) => {
    if (typeof value !== 'string') {
      return 'N/A';
    }

    const cleaned = value
      .replace(/^A\d+\s*:\s*/i, '')
      .replace(/\\n/g, '\n')
      .trim();

    return cleaned || 'N/A';
  };

  const resetMessages = () => {
    setError('');
    setSuccess('');
  };

  const fetchSubjects = useCallback(async () => {
    const response = await fetch(`${API_BASE}/subjects`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Failed to load subjects');
    }

    setSubjects(data.subjects || []);
    if (user?.role === 'student') {
      const userSubjects = data.userSubjects || [];
      if (userSubjects.length > 0) {
        setStudentSubject((current) => current || userSubjects[0]);
      }
    }
    if (user?.role === 'teacher' && !teacherForm.subject && (data.userSubjects || []).length > 0) {
      setTeacherForm((prev) => ({ ...prev, subject: data.userSubjects[0] }));
    }
  }, [getAuthHeaders, user, teacherForm.subject]);

  const loadTeacherAssignments = useCallback(async () => {
    const response = await fetch(`${API_BASE}/teacher/assignments`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Failed to load assignments');
    }
    setTeacherAssignments(data.assignments || []);
  }, [getAuthHeaders]);

  const loadTeacherSubmissions = useCallback(async (assignmentId) => {
    if (!assignmentId) {
      setTeacherSubmissions([]);
      return;
    }

    const response = await fetch(`${API_BASE}/teacher/assignments/${assignmentId}/submissions`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Failed to load submissions');
    }
    setTeacherSubmissions(data.submissions || []);
  }, [getAuthHeaders]);

  const loadStudentAssignments = useCallback(async (subjectValue = '') => {
    const query = subjectValue ? `?subject=${encodeURIComponent(subjectValue)}` : '';
    const response = await fetch(`${API_BASE}/student/assignments${query}`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Failed to load assignments');
    }
    setStudentAssignments(data.assignments || []);
  }, [getAuthHeaders]);

  const loadStudentSubmissions = useCallback(async () => {
    const response = await fetch(`${API_BASE}/student/submissions`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Failed to load submissions');
    }
    setStudentSubmissions(data.submissions || []);
  }, [getAuthHeaders]);

  useEffect(() => {
    const token = getToken();
    const userData = localStorage.getItem('user');
    if (!token || !userData) {
      navigate('/login');
      return;
    }

    setUser(JSON.parse(userData));
  }, [getToken, navigate]);

  useEffect(() => {
    if (!user) {
      return;
    }

    const initialize = async () => {
      try {
        setLoading(true);
        resetMessages();
        await fetchSubjects();

        if (user.role === 'teacher') {
          await loadTeacherAssignments();
        }

        if (user.role === 'student') {
          await loadStudentAssignments(studentSubject);
          await loadStudentSubmissions();
        }
      } catch (e) {
        setError(e.message || 'Failed to initialize dashboard');
      } finally {
        setLoading(false);
      }
    };

    initialize();
  }, [
    user,
    studentSubject,
    fetchSubjects,
    loadTeacherAssignments,
    loadStudentAssignments,
    loadStudentSubmissions
  ]);

  const handleTeacherEvaluateSubmission = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);

      const formData = new FormData();

      // Handle input mode
      if (teacherOverrides.inputMode === 'text') {
        formData.append('uploadMode', 'text');
        formData.append('questionsText', teacherOverrides.questionsText);
        formData.append('modelAnswersText', teacherOverrides.modelAnswersText);
        formData.append('studentAnswersText', teacherOverrides.studentAnswersText);
      } else {
        formData.append('uploadMode', 'file');
        if (teacherOverrides.questionsFile) {
          formData.append('questionsFile', teacherOverrides.questionsFile);
        }
        if (teacherOverrides.modelAnswersFile) {
          formData.append('modelAnswersFile', teacherOverrides.modelAnswersFile);
        }
        if (teacherOverrides.studentAnswersFile) {
          formData.append('studentAnswersFile', teacherOverrides.studentAnswersFile);
        }
      }

      if (teacherOverrides.studyMaterialFile) {
        formData.append('studyMaterialFile', teacherOverrides.studyMaterialFile);
      }

      const response = await fetch(`${API_BASE}/teacher/submissions/${submissionId}/evaluate`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Evaluation failed');
      }

      setSuccess('Submission evaluated successfully. Release it to make it visible to student.');
      if (selectedAssignmentId) {
        await loadTeacherSubmissions(selectedAssignmentId);
      }
    } catch (e) {
      setError(e.message || 'Evaluation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherReleaseSubmission = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);

      const response = await fetch(`${API_BASE}/teacher/submissions/${submissionId}/release`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Release failed');
      }

      setSuccess('Result released to student successfully');
      if (selectedAssignmentId) {
        await loadTeacherSubmissions(selectedAssignmentId);
      }
    } catch (e) {
      setError(e.message || 'Release failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStudentSubjectChange = async (e) => {
    const value = e.target.value;
    setStudentSubject(value);
    resetMessages();
    try {
      setLoading(true);
      await loadStudentAssignments(value);
    } catch (err) {
      setError(err.message || 'Could not load assignments');
    } finally {
      setLoading(false);
    }
  };

  const handleStudentSubmission = async (e) => {
    e.preventDefault();
    resetMessages();

    if (!studentAssignmentId || !studentAnswersFile) {
      setError('Please select assignment and upload student answers file');
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('assignmentId', studentAssignmentId);
      formData.append('studentAnswersFile', studentAnswersFile);

      const response = await fetch(`${API_BASE}/student/submissions`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Submission failed');
      }

      setSuccess('Answer uploaded successfully');
      setStudentAnswersFile(null);
      await loadStudentAssignments(studentSubject);
      await loadStudentSubmissions();
    } catch (e) {
      setError(e.message || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  const handleStudentViewResult = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/student/results/${submissionId}`, {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Could not fetch result');
      }
      setStudentResult(data);
      openReportPreview(data);
      setSuccess('Released result loaded');
    } catch (e) {
      setError(e.message || 'Could not fetch result');
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherViewResult = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/teacher/results/${submissionId}`, {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Could not fetch result');
      }
      openReportPreview(data);
      setSuccess('Result preview opened');
    } catch (e) {
      setError(e.message || 'Could not fetch result');
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherDownloadResult = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/teacher/results/${submissionId}`, {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Could not fetch result');
      }

      const reportHtml = buildReportHtml(data);
      const fileName = `evaluation-report-${submissionId || Date.now()}.html`;
      downloadReportHtml(reportHtml, fileName);
      setSuccess('Report downloaded');
    } catch (e) {
      setError(e.message || 'Could not download report');
    } finally {
      setLoading(false);
    }
  };

  const buildReportHtml = (resultData) => {
    const currentDate = new Date().toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    const results = {
      totalScore: resultData.totalScore ?? 0,
      totalMaxMarks: resultData.totalMaxMarks ?? 0,
      percentage: resultData.percentage ?? 0,
      totalQuestions: resultData.totalQuestions ?? 0,
      averageSimilarity: resultData.averageSimilarity ?? 0,
      questions: resultData.questions || []
    };

    return `
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
        
      .nli-badge.contradiction,
      .nli-badge.low-similarity,
      .nli-badge.low_similarity {
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
      <div class="report-header">
        <h1>📊 Evaluation Report</h1>
        <p>Generated on ${currentDate}</p>
        <p style="margin-top: 0.5rem; font-size: 0.95rem; opacity: 0.85;">
          Assignment: ${(resultData.assignment && resultData.assignment.title) || 'N/A'} | Subject: ${(resultData.assignment && resultData.assignment.subject) || 'N/A'}
        </p>
      </div>
        
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
                <strong><span class="nli-badge ${(q.nliLabel || '').toLowerCase().replace(/\s+/g, '-').replace(/_/g, '-')}">${q.nliLabel}</span></strong>
              </div>
            </div>
                    
            <div class="feedback-box">
              <strong style="color: #667eea; font-style: normal; display: block; margin-bottom: 0.5rem;">💬 Feedback:</strong>
              ${q.feedback}
            </div>
          </div>
        `).join('')}
      </div>
        
      <div class="footer">
        <p>AI-Powered Answer Evaluation System</p>
        <p style="margin-top: 0.5rem; font-size: 0.875rem;">This report was automatically generated by the evaluation system.</p>
      </div>
    </div>
  </body>
  </html>
    `;
  };

  const openReportPreview = (resultData) => {
    const reportHtml = buildReportHtml(resultData);
    const blob = new Blob([reportHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank', 'noopener,noreferrer');
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  };

  const downloadReportHtml = (reportHtml, fileName) => {
    const blob = new Blob([reportHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadStudentReport = () => {
    if (!studentResult) {
      return;
    }

    const reportHtml = buildReportHtml(studentResult);
    const fileName = `evaluation-report-${studentResult.submissionId || Date.now()}.html`;
    downloadReportHtml(reportHtml, fileName);
  };

  if (!user) {
    return null;
  }

  return (
    <div className="workflow-page">
      <Navbar />
      <div className="workflow-header">
        <h1>{user.role === 'teacher' ? 'Teacher Assignment Dashboard' : 'Student Assignment Dashboard'}</h1>
        <p>Welcome, {user.name} ({user.role})</p>
      </div>

      {error && <div className="workflow-alert error">{error}</div>}
      {success && <div className="workflow-alert success">{success}</div>}

      {user.role === 'teacher' && (
        <>
          <section className="workflow-section">
            <h2>⚡ Direct Evaluation (Llama Pipeline)</h2>
            <form className="workflow-form" onSubmit={async (e) => {
              e.preventDefault();
              resetMessages();

              if (!teacherOverrides.questionsText || !teacherOverrides.studentAnswersText || !teacherOverrides.marksValue) {
                setError('Please fill in Question, Marks, and Student Answer fields');
                return;
              }

              try {
                setLoading(true);
                
                // Step 1: Generate model answer from Colab via Llama
                setSuccess('Generating model answer from Llama...');
                const generatePayload = {
                  question: teacherOverrides.questionsText,
                  marks: teacherOverrides.marksValue
                };

                const generateResponse = await fetch(`${API_BASE}/generate-answer`, {
                  method: 'POST',
                  headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify(generatePayload)
                });

                const generateData = await generateResponse.json();
                if (!generateResponse.ok) {
                  throw new Error(generateData.message || 'Failed to generate model answer');
                }

                const modelAnswer = generateData.answer || generateData.reference_answer || '';
                if (!modelAnswer) {
                  throw new Error('No model answer generated from Llama');
                }

                setSuccess('Model answer generated. Now evaluating student answer...');

                // Step 2: Evaluate student answer against generated model answer
                const formData = new FormData();
                formData.append('uploadMode', 'text');
                
                // Format question with marks: "Q1: [marks] question text"
                const formattedQuestion = `Q1: [${teacherOverrides.marksValue} marks] ${teacherOverrides.questionsText}`;
                formData.append('questionsText', formattedQuestion);
                
                // Format model answer: "A1: answer text"
                const formattedModelAnswer = `A1: ${modelAnswer}`;
                formData.append('modelAnswersText', formattedModelAnswer);
                
                // Format student answer: "A1: answer text"
                const formattedStudentAnswer = `A1: ${teacherOverrides.studentAnswersText}`;
                formData.append('studentAnswersText', formattedStudentAnswer);

                const response = await fetch(`${API_BASE}/evaluate`, {
                  method: 'POST',
                  headers: getAuthHeaders(),
                  body: formData
                });

                const data = await response.json();
                if (!response.ok) {
                  throw new Error(data.message || 'Evaluation failed');
                }

                setSuccess('✅ Evaluation completed! Results below.');
                // Store results for display (backend returns top-level result fields)
                const resultPayload = data.results || data;
                setStudentResult({
                  ...resultPayload,
                  assignment: { title: 'Direct Evaluation', subject: 'N/A' },
                  generatedModelAnswer: modelAnswer
                });
              } catch (e) {
                setError(e.message || 'Evaluation failed');
              } finally {
                setLoading(false);
              }
            }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Question</label>
                <textarea
                  rows="3"
                  placeholder="What is machine learning? Explain with examples."
                  value={teacherOverrides.questionsText}
                  onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, questionsText: e.target.value }))}
                  required
                />
              </div>

              <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Marks</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={teacherOverrides.marksValue}
                    onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, marksValue: parseInt(e.target.value) || 5 }))}
                    required
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Student Answer</label>
                <textarea
                  rows="4"
                  placeholder="Student's answer here..."
                  value={teacherOverrides.studentAnswersText}
                  onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, studentAnswersText: e.target.value }))}
                  required
                />
              </div>

              <button type="submit" disabled={loading} style={{ marginTop: '1rem' }}>Evaluate with Llama</button>
            </form>
          </section>

          {studentResult && (
            <section className="workflow-section">
              <h2>📊 Evaluation Results</h2>
              <div className="workflow-card" style={{ marginBottom: '1.5rem' }}>
                <div>
                  <p><strong>Marks Awarded:</strong> {studentResult.totalScore} / {studentResult.totalMaxMarks}</p>
                  <p><strong>Percentage:</strong> {studentResult.percentage}%</p>
                  
                  <hr style={{ margin: '1rem 0', borderColor: 'rgba(255,255,255,0.1)' }} />
                  
                  <p><strong>🤖 Model Answer (Generated by Llama):</strong></p>
                  <div className="result-answer-box result-answer-model">
                    <div className="result-answer-content">{normalizeAnswerText(studentResult.generatedModelAnswer || studentResult.questions?.[0]?.referenceAnswer)}</div>
                  </div>
                  
                  <hr style={{ margin: '1rem 0', borderColor: 'rgba(255,255,255,0.1)' }} />
                  
                  <p><strong>📝 Student Answer:</strong></p>
                  <div className="result-answer-box result-answer-student">
                    <div className="result-answer-content">{normalizeAnswerText(studentResult.questions?.[0]?.studentAnswer)}</div>
                  </div>
                  
                  <hr style={{ margin: '1rem 0', borderColor: 'rgba(255,255,255,0.1)' }} />
                  
                  <p><strong>Semantic Similarity:</strong> {((studentResult.questions?.[0]?.similarity || 0) * 100).toFixed(1)}%</p>
                  <p><strong>Grade:</strong> {studentResult.questions?.[0]?.grade || 'N/A'}</p>
                </div>
                <button type="button" onClick={handleDownloadStudentReport} style={{ marginTop: '1rem' }}>📥 Download Report</button>
              </div>
            </section>
          )}

          <section className="workflow-section" style={{ display: 'none' }}>
            <h2>Submissions for Selected Assignment</h2>

            <div className="workflow-form inline-form">
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Input Mode</label>
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <label className="radio-label">
                      <input
                        type="radio"
                        name="inputMode"
                        value="file"
                        checked={teacherOverrides.inputMode === 'file'}
                        onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, inputMode: e.target.value }))}
                      />
                      Upload Files
                    </label>
                    <label className="radio-label">
                      <input
                        type="radio"
                        name="inputMode"
                        value="text"
                        checked={teacherOverrides.inputMode === 'text'}
                        onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, inputMode: e.target.value }))}
                      />
                      Enter Text
                    </label>
                  </div>
                </div>

                {teacherOverrides.inputMode === 'file' ? (
                  <>
                    <label>
                      Override Questions (optional)
                      <input type="file" onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, questionsFile: e.target.files[0] || null }))} />
                    </label>
                    <label>
                      Override Model Answers (optional)
                      <input type="file" onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, modelAnswersFile: e.target.files[0] || null }))} />
                    </label>
                    <label>
                      Override Student Answers (optional)
                      <input type="file" onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, studentAnswersFile: e.target.files[0] || null }))} />
                    </label>
                  </>
                ) : (
                  <>
                    <label>
                      Questions (Format: Q1: [5 marks] Question text)
                      <textarea
                        rows="4"
                        placeholder="Q1: [5 marks] What is machine learning?&#10;Q2: [3 marks] Define neural networks?"
                        value={teacherOverrides.questionsText}
                        onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, questionsText: e.target.value }))}
                      />
                    </label>
                    <label>
                      Model Answers (Format: A1: Answer text)
                      <textarea
                        rows="4"
                        placeholder="A1: Machine learning is a subset of AI...&#10;A2: Neural networks are computing systems..."
                        value={teacherOverrides.modelAnswersText}
                        onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, modelAnswersText: e.target.value }))}
                      />
                    </label>
                    <label>
                      Student Answers (Format: A1: Answer text)
                      <textarea
                        rows="4"
                        placeholder="A1: Student's answer...&#10;A2: Student's answer..."
                        value={teacherOverrides.studentAnswersText}
                        onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, studentAnswersText: e.target.value }))}
                      />
                    </label>
                  </>
                )}

                <label>
                  Override Study Material (optional)
                  <input type="file" onChange={(e) => setTeacherOverrides((prev) => ({ ...prev, studyMaterialFile: e.target.files[0] || null }))} />
                </label>
              </div>

              <div className="workflow-list">
                {teacherSubmissions.length === 0 && <p>No student submissions yet.</p>}
                {teacherSubmissions.map((submission) => (
                  <div key={submission.id} className="workflow-card">
                    <div>
                      <h3>{submission.studentName || 'Student'}</h3>
                      <p>{submission.studentEmail}</p>
                      <p>Status: {submission.status}</p>
                      <p className="muted">Submitted: {formatDateTime(submission.submittedAt)}</p>
                      {submission.finalScore !== null && submission.finalScore !== undefined && (
                        <p>Score: {submission.finalScore} / {submission.totalMaxMarks} ({submission.percentage}%)</p>
                      )}
                    </div>
                    <div className="actions">
                      <button type="button" disabled={loading} onClick={() => handleTeacherEvaluateSubmission(submission.id)}>
                        Evaluate
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => handleTeacherViewResult(submission.id)}
                        disabled={loading || submission.status === 'submitted'}
                      >
                        View Result
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => handleTeacherDownloadResult(submission.id)}
                        disabled={loading || submission.status === 'submitted'}
                      >
                        Download Report
                      </button>
                      <button type="button" disabled={loading || submission.released} onClick={() => handleTeacherReleaseSubmission(submission.id)}>
                        {submission.released ? 'Released' : 'Release'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {user.role === 'student' && (
        <>
          <section className="workflow-section">
            <h2>Upload Answers</h2>
            <form className="workflow-form" onSubmit={handleStudentSubmission}>
              <select value={studentSubject} onChange={handleStudentSubjectChange}>
                <option value="">All Subjects</option>
                {subjects.map((subject) => (
                  <option key={subject} value={subject}>{subject}</option>
                ))}
              </select>

              <select value={studentAssignmentId} onChange={(e) => setStudentAssignmentId(e.target.value)}>
                <option value="">Select Assignment</option>
                {studentAssignments.map((assignment) => (
                  <option key={assignment.id} value={assignment.id} disabled={assignment.alreadySubmitted}>
                    {assignment.title} - {assignment.subject} {assignment.alreadySubmitted ? '(Submitted)' : ''}
                  </option>
                ))}
              </select>

              <label>
                Student Answer Doc
                <input type="file" onChange={(e) => setStudentAnswersFile(e.target.files[0] || null)} />
              </label>

              <button type="submit" disabled={loading}>Submit Answer</button>
            </form>
          </section>

          <section className="workflow-section">
            <h2>My Submissions</h2>
            <div className="workflow-list">
              {studentSubmissions.length === 0 && <p>No submissions yet.</p>}
              {studentSubmissions.map((submission) => (
                <div key={submission.id} className="workflow-card">
                  <div>
                    <h3>{submission.assignmentTitle || 'Assignment'}</h3>
                    <p>{submission.subject}</p>
                    <p>Status: {submission.status}</p>
                    <p className="muted">Submitted: {formatDateTime(submission.submittedAt)}</p>
                    {submission.canViewResult && (
                      <p>Score: {submission.finalScore} / {submission.totalMaxMarks} ({submission.percentage}%)</p>
                    )}
                  </div>
                  <div className="actions">
                    {submission.canViewResult ? (
                      <button type="button" disabled={loading} onClick={() => handleStudentViewResult(submission.id)}>
                        View Result
                      </button>
                    ) : (
                      <span className="muted">Waiting for teacher release</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {studentResult && (
            <section className="workflow-section">
              <h2>Released Result</h2>
              <div className="workflow-card">
                <div>
                  <p><strong>Assignment:</strong> {(studentResult.assignment && studentResult.assignment.title) || 'N/A'}</p>
                  <p><strong>Subject:</strong> {(studentResult.assignment && studentResult.assignment.subject) || 'N/A'}</p>
                  <p><strong>Total Score:</strong> {studentResult.totalScore} / {studentResult.totalMaxMarks}</p>
                  <p><strong>Percentage:</strong> {studentResult.percentage}%</p>
                </div>
                <button type="button" onClick={handleDownloadStudentReport}>Download Report</button>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default WorkflowPage;