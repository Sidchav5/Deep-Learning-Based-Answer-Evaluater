import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import '../WorkflowPage.css';
import Navbar from './Navbar';
import Toast from './Toast';

const API_BASE = 'http://localhost:5000/api';

const emptyQuestion = () => ({ id: `${Date.now()}-${Math.random()}`, question: '', marks: 5 });

function WorkflowPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [user, setUser] = useState(null);
  const [subjects, setSubjects] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState({ message: '', type: 'info' });

  const [teacherForm, setTeacherForm] = useState({
    title: '',
    subject: '',
    dueDate: '',
    questions: [emptyQuestion()]
  });
  const [teacherAssignments, setTeacherAssignments] = useState([]);
  const [selectedTeacherAssignment, setSelectedTeacherAssignment] = useState(null);
  const [teacherSubmissions, setTeacherSubmissions] = useState([]);
  const [teacherSubmissionDetail, setTeacherSubmissionDetail] = useState(null);

  const [studentSubject, setStudentSubject] = useState('');
  const [studentAssignments, setStudentAssignments] = useState([]);
  const [selectedStudentAssignment, setSelectedStudentAssignment] = useState(null);
  const [studentAnswers, setStudentAnswers] = useState({});
  const [studentSubmissions, setStudentSubmissions] = useState([]);
  const [studentResult, setStudentResult] = useState(null);

  const getToken = useCallback(() => localStorage.getItem('token'), []);

  const getAuthHeaders = useCallback(() => ({
    Authorization: `Bearer ${getToken()}`
  }), [getToken]);

  const resetMessages = () => {
    setError('');
    setSuccess('');
  };

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  const formatDateTime = (value) => {
    if (!value) return '-';
    try {
      return new Date(value).toLocaleString();
    } catch (e) {
      return value;
    }
  };

  const routeParts = useMemo(() => (
    location.pathname.replace(/^\/evaluate\/?/, '').split('/').filter(Boolean)
  ), [location.pathname]);

  const rolePart = routeParts[0] || '';
  const viewPart = routeParts[1] || '';
  const idPart = routeParts[2] || '';

  const isTeacherHome = rolePart === 'teacher' && !viewPart;
  const isTeacherCreate = rolePart === 'teacher' && viewPart === 'create';
  const isTeacherAssignments = rolePart === 'teacher' && viewPart === 'assignments' && !idPart;
  const isTeacherAssignmentDetail = rolePart === 'teacher' && viewPart === 'assignments' && Boolean(idPart);

  const isStudentHome = rolePart === 'student' && !viewPart;
  const isStudentAssignments = rolePart === 'student' && viewPart === 'assignments' && !idPart;
  const isStudentAssignmentDetail = rolePart === 'student' && viewPart === 'assignments' && Boolean(idPart);
  const isStudentSubmissions = rolePart === 'student' && viewPart === 'submissions';
  const isStudentResultDetail = rolePart === 'student' && viewPart === 'results' && Boolean(idPart);

  const currentTeacherAssignmentId = isTeacherAssignmentDetail ? idPart : '';
  const currentStudentAssignmentId = isStudentAssignmentDetail ? idPart : '';
  const currentStudentResultId = isStudentResultDetail ? idPart : '';

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
  }, [getAuthHeaders, teacherForm.subject, user]);

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

  const loadTeacherAssignmentDetail = useCallback(async (assignmentId) => {
    if (!assignmentId) {
      setSelectedTeacherAssignment(null);
      setTeacherSubmissions([]);
      return;
    }

    const [assignmentRes, submissionsRes] = await Promise.all([
      fetch(`${API_BASE}/teacher/assignments/${assignmentId}`, { headers: getAuthHeaders() }),
      fetch(`${API_BASE}/teacher/assignments/${assignmentId}/submissions`, { headers: getAuthHeaders() })
    ]);

    const assignmentData = await assignmentRes.json();
    if (!assignmentRes.ok) {
      throw new Error(assignmentData.message || 'Failed to load assignment details');
    }

    const submissionsData = await submissionsRes.json();
    if (!submissionsRes.ok) {
      throw new Error(submissionsData.message || 'Failed to load submissions');
    }

    setSelectedTeacherAssignment(assignmentData.assignment || null);
    setTeacherSubmissions(submissionsData.submissions || []);
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

  const loadStudentAssignmentDetail = useCallback(async (assignmentId) => {
    if (!assignmentId) {
      setSelectedStudentAssignment(null);
      setStudentAnswers({});
      return;
    }

    const response = await fetch(`${API_BASE}/student/assignments/${assignmentId}`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Failed to load assignment');
    }

    const assignment = data.assignment || null;
    setSelectedStudentAssignment(assignment);

    const defaultAnswers = {};
    (assignment?.questions || []).forEach((question) => {
      defaultAnswers[question.number] = '';
    });
    setStudentAnswers(defaultAnswers);
  }, [getAuthHeaders]);

  const loadStudentResult = useCallback(async (submissionId) => {
    if (!submissionId) {
      setStudentResult(null);
      return;
    }

    const response = await fetch(`${API_BASE}/student/results/${submissionId}`, {
      headers: getAuthHeaders()
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || 'Could not fetch result');
    }

    setStudentResult(data);
  }, [getAuthHeaders]);

  useEffect(() => {
    const token = getToken();
    const userData = localStorage.getItem('user');
    if (!token || !userData) {
      navigate('/login');
      return;
    }

    try {
      const parsedUser = JSON.parse(userData);
      setUser(parsedUser);
    } catch (e) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
    }
  }, [getToken, navigate]);

  useEffect(() => {
    if (!user) return;
    if (location.pathname === '/evaluate') {
      navigate(`/evaluate/${user.role}`, { replace: true });
    }
  }, [location.pathname, navigate, user]);

  useEffect(() => {
    if (!user) return;

    const initialize = async () => {
      try {
        setLoading(true);
        resetMessages();
        await fetchSubjects();

        if (user.role === 'teacher') {
          if (isTeacherHome || isTeacherAssignments || isTeacherAssignmentDetail) {
            await loadTeacherAssignments();
          }
          if (isTeacherAssignmentDetail && currentTeacherAssignmentId) {
            await loadTeacherAssignmentDetail(currentTeacherAssignmentId);
          }
        }

        if (user.role === 'student') {
          if (isStudentHome || isStudentAssignments || isStudentAssignmentDetail) {
            await loadStudentAssignments(studentSubject);
          }
          if (isStudentAssignmentDetail && currentStudentAssignmentId) {
            await loadStudentAssignmentDetail(currentStudentAssignmentId);
          }
          if (isStudentHome || isStudentSubmissions || isStudentResultDetail) {
            await loadStudentSubmissions();
          }
          if (isStudentResultDetail && currentStudentResultId) {
            await loadStudentResult(currentStudentResultId);
          }
        }
      } catch (e) {
        setError(e.message || 'Failed to initialize dashboard');
      } finally {
        setLoading(false);
      }
    };

    initialize();
  }, [
    currentStudentAssignmentId,
    currentStudentResultId,
    currentTeacherAssignmentId,
    fetchSubjects,
    isStudentAssignmentDetail,
    isStudentAssignments,
    isStudentHome,
    isStudentResultDetail,
    isStudentSubmissions,
    isTeacherAssignmentDetail,
    isTeacherAssignments,
    isTeacherHome,
    loadStudentAssignmentDetail,
    loadStudentAssignments,
    loadStudentResult,
    loadStudentSubmissions,
    loadTeacherAssignmentDetail,
    loadTeacherAssignments,
    studentSubject,
    user
  ]);

  const addTeacherQuestion = () => {
    setTeacherForm((prev) => ({
      ...prev,
      questions: [...prev.questions, emptyQuestion()]
    }));
  };

  const removeTeacherQuestion = (id) => {
    setTeacherForm((prev) => {
      if (prev.questions.length === 1) return prev;
      return {
        ...prev,
        questions: prev.questions.filter((question) => question.id !== id)
      };
    });
  };

  const updateTeacherQuestion = (id, field, value) => {
    setTeacherForm((prev) => ({
      ...prev,
      questions: prev.questions.map((question) => (
        question.id === id ? { ...question, [field]: value } : question
      ))
    }));
  };

  const handleCreateAssignment = async (e) => {
    e.preventDefault();
    resetMessages();

    const cleanedQuestions = teacherForm.questions
      .map((item) => ({
        question: item.question.trim(),
        marks: Number(item.marks)
      }))
      .filter((item) => item.question && item.marks > 0);

    if (!teacherForm.subject) {
      setError('Please select subject');
      return;
    }

    if (cleanedQuestions.length === 0) {
      setError('Add at least one valid question with marks');
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(`${API_BASE}/teacher/assignments`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: teacherForm.title,
          subject: teacherForm.subject,
          dueDate: teacherForm.dueDate,
          questions: cleanedQuestions
        })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Failed to create assignment');
      }

      setSuccess('Assignment created successfully');
      showToast('✓ Assignment created', 'success');
      setTeacherForm((prev) => ({
        ...prev,
        title: '',
        dueDate: '',
        questions: [emptyQuestion()]
      }));

      await loadTeacherAssignments();
      navigate('/evaluate/teacher/assignments');
    } catch (err) {
      setError(err.message || 'Assignment creation failed');
      showToast(`✕ ${err.message || 'Assignment creation failed'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherViewSubmission = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/teacher/submissions/${submissionId}`, {
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Failed to load submission details');
      }

      setTeacherSubmissionDetail(data.submission || null);
      showToast('✓ Submission loaded', 'success');
    } catch (err) {
      setError(err.message || 'Failed to load submission details');
      showToast(`✕ ${err.message || 'Failed to load submission details'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherEvaluateSubmission = async (submissionId) => {
    resetMessages();
    try {
      setLoading(true);
      showToast('✓ Evaluation started for this submission...', 'success');

      const response = await fetch(`${API_BASE}/teacher/submissions/${submissionId}/evaluate`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Evaluation failed');
      }

      setTeacherSubmissions((prev) => prev.map((row) => (
        row.id === submissionId
          ? {
              ...row,
              status: row.status === 'released' ? 'released' : 'evaluated',
              isEvaluated: true
            }
          : row
      )));

      setSuccess('Student assignment evaluated successfully');
      showToast('✓ Submission evaluated successfully!', 'success');
      if (currentTeacherAssignmentId) {
        await loadTeacherAssignmentDetail(currentTeacherAssignmentId);
      }
    } catch (err) {
      const errorMsg = err.message || 'Evaluation failed';
      setError(errorMsg);
      showToast(`✕ ${errorMsg}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleTeacherEvaluateAll = async () => {
    if (!currentTeacherAssignmentId) {
      setError('Select an assignment first');
      return;
    }

    resetMessages();
    let progressInterval = null;
    let timeoutHandler = null;

    try {
      setLoading(true);
      showToast('📋 Preparing to evaluate all submissions...', 'progress');

      timeoutHandler = setTimeout(() => {
        setLoading(false);
        showToast('✕ Evaluation timeout - please refresh and try again', 'error');
      }, 15 * 60 * 1000);

      let progressStep = 0;
      progressInterval = setInterval(() => {
        progressStep += 1;
        const messages = [
          '⏳ Querying submitted answers...',
          '🤖 Initializing LLaMA evaluation...',
          '⚙️ Processing question 1...',
          '⚙️ Processing answers...',
          '💾 Saving evaluation results...'
        ];
        const msg = messages[Math.min(progressStep, messages.length - 1)];
        showToast(msg, 'progress');
      }, 3000);

      const response = await fetch(`${API_BASE}/teacher/assignments/${currentTeacherAssignmentId}/evaluate-all?force=true`, {
        method: 'POST',
        headers: getAuthHeaders()
      });

      if (progressInterval) clearInterval(progressInterval);
      if (timeoutHandler) clearTimeout(timeoutHandler);

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Evaluate all failed');
      }

      const failedCount = Number(data.failedCount || 0);
      const evaluatedCount = Number(data.evaluatedCount || 0);
      const skippedCount = Number(data.skippedCount || 0);

      if (failedCount > 0) {
        showToast(`✓ Completed! Evaluated: ${evaluatedCount}, Failed: ${failedCount}, Skipped: ${skippedCount}`, 'success');
      } else if (evaluatedCount > 0) {
        showToast(`✓ All ${evaluatedCount} submissions evaluated successfully!`, 'success');
      } else if (skippedCount > 0) {
        showToast(`✓ All ${skippedCount} submissions already evaluated`, 'success');
      }

      if (data.batchFallbackUsed) {
        setTimeout(() => {
          showToast('ℹ️ Used per-answer mode (batch endpoint unavailable)', 'info');
        }, 500);
      }

      setSuccess(`Evaluation complete. Evaluated: ${evaluatedCount}, Failed: ${failedCount}, Skipped: ${skippedCount}`);
      await loadTeacherAssignmentDetail(currentTeacherAssignmentId);
    } catch (err) {
      const errorMsg = err.message || 'Evaluate all failed';
      setError(errorMsg);
      showToast(`✕ ${errorMsg}`, 'error');
    } finally {
      if (progressInterval) clearInterval(progressInterval);
      if (timeoutHandler) clearTimeout(timeoutHandler);
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

      setSuccess('Result released to student');
      showToast('✓ Result released', 'success');
      if (currentTeacherAssignmentId) {
        await loadTeacherAssignmentDetail(currentTeacherAssignmentId);
      }
    } catch (err) {
      setError(err.message || 'Release failed');
      showToast(`✕ ${err.message || 'Release failed'}`, 'error');
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

  const handleStudentAnswerChange = (questionNumber, value) => {
    setStudentAnswers((prev) => ({
      ...prev,
      [questionNumber]: value
    }));
  };

  const studentCanSubmit = useMemo(() => {
    if (!selectedStudentAssignment || selectedStudentAssignment.alreadySubmitted) {
      return false;
    }
    const questions = selectedStudentAssignment.questions || [];
    if (questions.length === 0) {
      return false;
    }
    return questions.every((question) => Boolean((studentAnswers[question.number] || '').trim()));
  }, [selectedStudentAssignment, studentAnswers]);

  const handleStudentSubmission = async (e) => {
    e.preventDefault();
    resetMessages();

    if (!selectedStudentAssignment || !currentStudentAssignmentId) {
      setError('Open an assignment first');
      return;
    }

    const answers = (selectedStudentAssignment.questions || []).map((question) => ({
      questionNumber: question.number,
      answer: (studentAnswers[question.number] || '').trim()
    }));

    if (answers.some((answer) => !answer.answer)) {
      setError('Please answer all questions before submitting');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/student/submissions`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          assignmentId: currentStudentAssignmentId,
          answers
        })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.message || 'Submission failed');
      }

      setSuccess('Assignment submitted successfully');
      showToast('✓ Assignment submitted', 'success');
      setSelectedStudentAssignment(null);
      setStudentAnswers({});

      await loadStudentAssignments(studentSubject);
      await loadStudentSubmissions();
      navigate('/evaluate/student/submissions');
    } catch (err) {
      setError(err.message || 'Submission failed');
      showToast(`✕ ${err.message || 'Submission failed'}`, 'error');
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
      setStudentResult(data);
      setSuccess('Evaluation details loaded');
      showToast('✓ Evaluation details loaded', 'success');
    } catch (err) {
      setError(err.message || 'Could not fetch result');
      showToast(`✕ ${err.message || 'Could not fetch result'}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const buildReportHtml = (resultData) => {
    const results = {
      totalScore: resultData.totalScore ?? 0,
      totalMaxMarks: resultData.totalMaxMarks ?? 0,
      percentage: resultData.percentage ?? 0,
      questions: resultData.questions || []
    };

    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Evaluation Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; color: #111; }
    h1, h2 { margin: 0 0 12px; }
    .summary { margin-bottom: 16px; padding: 12px; border: 1px solid #ddd; }
    .q { margin-bottom: 14px; padding: 12px; border: 1px solid #ddd; }
    .label { font-weight: bold; }
  </style>
</head>
<body>
  <h1>Evaluation Report</h1>
  <div class="summary">
    <div><span class="label">Assignment:</span> ${(resultData.assignment && resultData.assignment.title) || 'N/A'}</div>
    <div><span class="label">Subject:</span> ${(resultData.assignment && resultData.assignment.subject) || 'N/A'}</div>
    <div><span class="label">Score:</span> ${results.totalScore} / ${results.totalMaxMarks}</div>
    <div><span class="label">Percentage:</span> ${results.percentage}%</div>
  </div>
  <h2>Question-wise</h2>
  ${results.questions.map((question, index) => `
    <div class="q">
      <div><span class="label">Q${index + 1}:</span> ${question.question || ''}</div>
      <div><span class="label">Score:</span> ${question.score} / ${question.maxMarks}</div>
      <div><span class="label">Grade:</span> ${question.grade || question.nliLabel || 'N/A'}</div>
      <div><span class="label">Model Answer:</span> ${question.modelAnswer || ''}</div>
      <div><span class="label">Student Answer:</span> ${question.studentAnswer || ''}</div>
      <div><span class="label">Feedback:</span> ${question.feedback || ''}</div>
    </div>
  `).join('')}
</body>
</html>
    `;
  };

  const handleDownloadReport = () => {
    if (!studentResult) return;
    const reportHtml = buildReportHtml(studentResult);
    const blob = new Blob([reportHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evaluation-report-${studentResult.submissionId || Date.now()}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!user) return null;

  return (
    <div className="workflow-page">
      <Navbar />
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: '', type: 'info' })}
      />

      <div className="workflow-header">
        <h1>{user.role === 'teacher' ? 'Teacher Dashboard' : 'Student Dashboard'}</h1>
        <p>Welcome, {user.name} ({user.role})</p>
      </div>

      {error && <div className="workflow-alert error">{error}</div>}
      {success && <div className="workflow-alert success">{success}</div>}

      {user.role === 'teacher' && (
        <div className="workflow-subnav">
          <button type="button" className={isTeacherHome ? 'btn-secondary active-nav' : 'btn-secondary'} onClick={() => navigate('/evaluate/teacher')}>Dashboard</button>
          <button type="button" className={isTeacherCreate ? 'btn-secondary active-nav' : 'btn-secondary'} onClick={() => navigate('/evaluate/teacher/create')}>Create Assignment</button>
          <button type="button" className={(isTeacherAssignments || isTeacherAssignmentDetail) ? 'btn-secondary active-nav' : 'btn-secondary'} onClick={() => navigate('/evaluate/teacher/assignments')}>My Assignments</button>
        </div>
      )}

      {user.role === 'student' && (
        <div className="workflow-subnav">
          <button type="button" className={isStudentHome ? 'btn-secondary active-nav' : 'btn-secondary'} onClick={() => navigate('/evaluate/student')}>Dashboard</button>
          <button type="button" className={(isStudentAssignments || isStudentAssignmentDetail) ? 'btn-secondary active-nav' : 'btn-secondary'} onClick={() => navigate('/evaluate/student/assignments')}>Assignments</button>
          <button type="button" className={(isStudentSubmissions || isStudentResultDetail) ? 'btn-secondary active-nav' : 'btn-secondary'} onClick={() => navigate('/evaluate/student/submissions')}>My Submissions</button>
        </div>
      )}

      {user.role === 'teacher' && isTeacherHome && (
        <section className="workflow-section">
          <h2>Quick Actions</h2>
          <div className="workflow-list compact-grid">
            <div className="workflow-card">
              <h3>Create New Assignment</h3>
              <p>Build and publish a new assignment for your students.</p>
              <div className="actions">
                <button type="button" onClick={() => navigate('/evaluate/teacher/create')}>Go to Create</button>
              </div>
            </div>
            <div className="workflow-card">
              <h3>Manage Assignments</h3>
              <p>Open assignment, evaluate responses, and release results.</p>
              <div className="actions">
                <button type="button" onClick={() => navigate('/evaluate/teacher/assignments')}>View Assignments</button>
              </div>
            </div>
          </div>
        </section>
      )}

      {user.role === 'teacher' && isTeacherCreate && (
        <section className="workflow-section">
          <h2>Create Assignment</h2>
          <form className="workflow-form" onSubmit={handleCreateAssignment}>
            <input
              type="text"
              placeholder="Assignment title (optional)"
              value={teacherForm.title}
              onChange={(e) => setTeacherForm((prev) => ({ ...prev, title: e.target.value }))}
              disabled={loading}
            />

            <select
              value={teacherForm.subject}
              onChange={(e) => setTeacherForm((prev) => ({ ...prev, subject: e.target.value }))}
              disabled={loading}
            >
              <option value="">Select subject</option>
              {subjects.map((subject) => (
                <option key={subject} value={subject}>{subject}</option>
              ))}
            </select>

            <input
              type="datetime-local"
              value={teacherForm.dueDate}
              onChange={(e) => setTeacherForm((prev) => ({ ...prev, dueDate: e.target.value }))}
              disabled={loading}
            />

            {teacherForm.questions.map((question, index) => (
              <div key={question.id} className="workflow-card">
                <h3>Question {index + 1}</h3>
                <textarea
                  rows="3"
                  placeholder="Enter question"
                  value={question.question}
                  onChange={(e) => updateTeacherQuestion(question.id, 'question', e.target.value)}
                  disabled={loading}
                />
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={question.marks}
                  onChange={(e) => updateTeacherQuestion(question.id, 'marks', e.target.value)}
                  disabled={loading}
                />
                <div className="actions">
                  <button type="button" className="btn-secondary" disabled={loading} onClick={addTeacherQuestion}>Add Question</button>
                  <button type="button" className="btn-secondary" disabled={loading || teacherForm.questions.length === 1} onClick={() => removeTeacherQuestion(question.id)}>Remove</button>
                </div>
              </div>
            ))}

            <button type="submit" disabled={loading}>Create Assignment</button>
          </form>
        </section>
      )}

      {user.role === 'teacher' && isTeacherAssignments && (
        <section className="workflow-section">
          <h2>My Assignments</h2>
          <div className="workflow-list">
            {teacherAssignments.length === 0 && <p>No assignments yet.</p>}
            {teacherAssignments.map((assignment) => (
              <div key={assignment.id} className="workflow-card">
                <div>
                  <h3>{assignment.title}</h3>
                  <p>{assignment.subject}</p>
                  <p>Questions: {assignment.questionCount} | Total Marks: {assignment.totalMarks}</p>
                  <p>Submissions: {assignment.submissionCount}</p>
                  <p className="muted">Due: {formatDateTime(assignment.dueDate)}</p>
                </div>
                <div className="actions">
                  <button type="button" disabled={loading} onClick={() => navigate(`/evaluate/teacher/assignments/${assignment.id}`)}>View Assignment</button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {user.role === 'teacher' && isTeacherAssignmentDetail && selectedTeacherAssignment && (
        <>
          <section className="workflow-section">
            <h2>{selectedTeacherAssignment.title}</h2>
            <p>Subject: {selectedTeacherAssignment.subject}</p>
            <p>Total Questions: {selectedTeacherAssignment.questionCount} | Total Marks: {selectedTeacherAssignment.totalMarks}</p>
            <div className="actions">
              <button type="button" className="btn-secondary" disabled={loading} onClick={() => navigate('/evaluate/teacher/assignments')}>Back to Assignments</button>
              <button type="button" className="btn-evaluate-all" disabled={loading} onClick={handleTeacherEvaluateAll}>Evaluate All</button>
              <button type="button" className="btn-secondary" disabled={loading} onClick={() => loadTeacherAssignmentDetail(currentTeacherAssignmentId)}>Refresh</button>
            </div>
          </section>

          <section className="workflow-section">
            <h2>Student Submissions</h2>
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
                    <button type="button" className="btn-action" disabled={loading} onClick={() => handleTeacherViewSubmission(submission.id)}>View Submission</button>
                    <button type="button" className="btn-evaluate" disabled={loading} onClick={() => handleTeacherEvaluateSubmission(submission.id)}>Evaluate</button>
                    <button type="button" className="btn-secondary" disabled={loading || !submission.isEvaluated} onClick={() => handleTeacherViewResult(submission.id)}>View Evaluation</button>
                    <button type="button" className="btn-secondary" disabled={loading || !submission.isEvaluated || submission.released} onClick={() => handleTeacherReleaseSubmission(submission.id)}>{submission.released ? 'Released' : 'Release'}</button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {teacherSubmissionDetail && (
            <section className="workflow-section">
              <h2>Submission: {teacherSubmissionDetail.student?.name}</h2>
              <p>{teacherSubmissionDetail.student?.email}</p>
              <p>Status: {teacherSubmissionDetail.status}</p>
              <div className="workflow-list">
                {(teacherSubmissionDetail.answers || []).map((item) => (
                  <div key={item.questionNumber} className="workflow-card">
                    <p><strong>Q{item.questionNumber}</strong> ({item.marks} marks)</p>
                    <p>{item.question}</p>
                    <div className="result-answer-box result-answer-student">
                      <div className="result-answer-content">{item.studentAnswer || 'No answer'}</div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {user.role === 'student' && isStudentHome && (
        <section className="workflow-section">
          <h2>Quick Actions</h2>
          <div className="workflow-list compact-grid">
            <div className="workflow-card">
              <h3>Open Assignments</h3>
              <p>Find pending assignments and submit answers.</p>
              <div className="actions">
                <button type="button" onClick={() => navigate('/evaluate/student/assignments')}>Go to Assignments</button>
              </div>
            </div>
            <div className="workflow-card">
              <h3>My Submissions</h3>
              <p>Track status and view released results.</p>
              <div className="actions">
                <button type="button" onClick={() => navigate('/evaluate/student/submissions')}>View Submissions</button>
              </div>
            </div>
          </div>
        </section>
      )}

      {user.role === 'student' && isStudentAssignments && (
        <section className="workflow-section">
          <h2>Available Assignments</h2>
          <select value={studentSubject} onChange={handleStudentSubjectChange} disabled={loading}>
            <option value="">All Subjects</option>
            {subjects.map((subject) => (
              <option key={subject} value={subject}>{subject}</option>
            ))}
          </select>

          <div className="workflow-list">
            {studentAssignments.length === 0 && <p>No assignments available.</p>}
            {studentAssignments.map((assignment) => (
              <div key={assignment.id} className="workflow-card">
                <div>
                  <h3>{assignment.title}</h3>
                  <p>{assignment.subject}</p>
                  <p>Questions: {assignment.questionCount} | Total Marks: {assignment.totalMarks}</p>
                  <p className="muted">Due: {formatDateTime(assignment.dueDate)}</p>
                  <p>{assignment.alreadySubmitted ? 'Submitted' : 'Pending'}</p>
                </div>
                <button type="button" className="btn-secondary" disabled={loading || assignment.alreadySubmitted} onClick={() => navigate(`/evaluate/student/assignments/${assignment.id}`)}>{assignment.alreadySubmitted ? 'Submitted' : 'Open Assignment'}</button>
              </div>
            ))}
          </div>
        </section>
      )}

      {user.role === 'student' && isStudentAssignmentDetail && selectedStudentAssignment && (
        <section className="workflow-section">
          <h2>{selectedStudentAssignment.title}</h2>
          <p>Subject: {selectedStudentAssignment.subject}</p>
          <p>Total Marks: {selectedStudentAssignment.totalMarks}</p>
          <div className="actions">
            <button type="button" className="btn-secondary" onClick={() => navigate('/evaluate/student/assignments')}>Back to Assignments</button>
          </div>

          <form className="workflow-form" onSubmit={handleStudentSubmission}>
            {(selectedStudentAssignment.questions || []).map((question) => (
              <div key={question.number} className="workflow-card">
                <p><strong>Q{question.number}</strong> ({question.marks} marks)</p>
                <p>{question.question}</p>
                <textarea
                  rows="4"
                  placeholder="Write your answer"
                  value={studentAnswers[question.number] || ''}
                  onChange={(e) => handleStudentAnswerChange(question.number, e.target.value)}
                  disabled={loading || selectedStudentAssignment.alreadySubmitted}
                />
              </div>
            ))}

            <button type="submit" disabled={loading || !studentCanSubmit || selectedStudentAssignment.alreadySubmitted}>{selectedStudentAssignment.alreadySubmitted ? 'Submitted' : 'Submit Assignment'}</button>
          </form>
        </section>
      )}

      {user.role === 'student' && isStudentSubmissions && (
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
                    <button type="button" disabled={loading} onClick={() => navigate(`/evaluate/student/results/${submission.id}`)}>View Result</button>
                  ) : (
                    <span className="muted">Waiting for teacher release</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {user.role === 'student' && isStudentResultDetail && studentResult && (
        <section className="workflow-section">
          <h2>Evaluation Details</h2>
          <div className="workflow-card">
            <div>
              <p><strong>Assignment:</strong> {(studentResult.assignment && studentResult.assignment.title) || 'N/A'}</p>
              <p><strong>Subject:</strong> {(studentResult.assignment && studentResult.assignment.subject) || 'N/A'}</p>
              <p><strong>Total Score:</strong> {studentResult.totalScore} / {studentResult.totalMaxMarks}</p>
              <p><strong>Percentage:</strong> {studentResult.percentage}%</p>
            </div>
            <div className="actions">
              <button type="button" className="btn-secondary" onClick={() => navigate('/evaluate/student/submissions')}>Back to Submissions</button>
              <button type="button" onClick={handleDownloadReport}>Download Report</button>
            </div>
          </div>

          <div className="workflow-list">
            {(studentResult.questions || []).map((question) => (
              <div key={question.questionNumber} className="workflow-card">
                <p><strong>Q{question.questionNumber}</strong> ({question.maxMarks} marks)</p>
                <p>{question.question}</p>
                <p><strong>Score:</strong> {question.score} / {question.maxMarks}</p>
                <p><strong>Grade:</strong> {question.grade || question.nliLabel || 'N/A'}</p>
                <p><strong>Similarity:</strong> {((question.similarity || 0) * 100).toFixed(1)}%</p>
                <div className="result-answer-box result-answer-model">
                  <div className="result-answer-content"><strong>Model:</strong> {question.modelAnswer || 'N/A'}</div>
                </div>
                <div className="result-answer-box result-answer-student">
                  <div className="result-answer-content"><strong>Student:</strong> {question.studentAnswer || 'N/A'}</div>
                </div>
                <p><strong>Feedback:</strong> {question.feedback || 'N/A'}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {studentResult && user.role === 'teacher' && (
        <section className="workflow-section">
          <h2>Evaluation Details</h2>
          <div className="workflow-card">
            <div>
              <p><strong>Assignment:</strong> {(studentResult.assignment && studentResult.assignment.title) || 'N/A'}</p>
              <p><strong>Subject:</strong> {(studentResult.assignment && studentResult.assignment.subject) || 'N/A'}</p>
              <p><strong>Total Score:</strong> {studentResult.totalScore} / {studentResult.totalMaxMarks}</p>
              <p><strong>Percentage:</strong> {studentResult.percentage}%</p>
            </div>
          </div>

          <div className="workflow-list">
            {(studentResult.questions || []).map((question) => (
              <div key={question.questionNumber} className="workflow-card">
                <p><strong>Q{question.questionNumber}</strong> ({question.maxMarks} marks)</p>
                <p>{question.question}</p>
                <p><strong>Score:</strong> {question.score} / {question.maxMarks}</p>
                <p><strong>Grade:</strong> {question.grade || question.nliLabel || 'N/A'}</p>
                <p><strong>Similarity:</strong> {((question.similarity || 0) * 100).toFixed(1)}%</p>
                <div className="result-answer-box result-answer-model">
                  <div className="result-answer-content"><strong>Llama Answer:</strong> {question.modelAnswer || 'N/A'}</div>
                </div>
                <div className="result-answer-box result-answer-student">
                  <div className="result-answer-content"><strong>Student Answer:</strong> {question.studentAnswer || 'N/A'}</div>
                </div>
                <p><strong>Feedback:</strong> {question.feedback || 'N/A'}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

export default WorkflowPage;
