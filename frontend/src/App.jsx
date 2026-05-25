import React, { useState, useEffect } from 'react';

const API_BASE = window.location.port === '5173' ? 'http://127.0.0.1:8000' : window.location.origin;

function App() {
  const [activeTab, setActiveTab] = useState('jobs');
  const [onboarded, setOnboarded] = useState(false);
  const [hasCompiler, setHasCompiler] = useState(false);
  const [compilerName, setCompilerName] = useState('');
  const [cvDetails, setCvDetails] = useState(null);
  
  // Dashboard states
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [devPlan, setDevPlan] = useState({ missing_skills: [], plan: [] });
  const [loading, setLoading] = useState(false);

  // Add job form state
  const [showJobForm, setShowJobForm] = useState(false);
  const [newJob, setNewJob] = useState({ company: '', title: '', jd_text: '', location: 'Remote' });

  // Onboarding wizard states
  const [cvFile, setCvFile] = useState(null);
  const [onboardingQuestions, setOnboardingQuestions] = useState([]);
  const [currentOnboardIdx, setCurrentOnboardIdx] = useState(0);
  const [onboardAnswers, setOnboardAnswers] = useState([]);
  
  // Specific JD questioning states
  const [activeJob, setActiveJob] = useState(null);
  const [activeJobAnalysis, setActiveJobAnalysis] = useState(null);
  const [grillQuestions, setGrillQuestions] = useState([]);
  const [currentGrillIdx, setCurrentGrillIdx] = useState(0);
  const [grillAnswers, setGrillAnswers] = useState([]);
  const [tailorResult, setTailorResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isTailoring, setIsTailoring] = useState(false);
  const [grillModalOpen, setGrillModalOpen] = useState(false);
  const [tailorModalOpen, setTailorModalOpen] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      const data = await res.json();
      setOnboarded(data.onboarded);
      setHasCompiler(data.has_compiler);
      setCompilerName(data.compiler_detected || 'None');
      if (data.onboarded) {
        setCvDetails(data.cv_details);
        fetchDashboardData();
      }
    } catch (err) {
      console.error('Error fetching backend status:', err);
    }
  };

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Jobs
      const jobsRes = await fetch(`${API_BASE}/api/jobs`);
      const jobsData = await jobsRes.json();
      setJobs(jobsData);

      // 2. Fetch Applications
      const appsRes = await fetch(`${API_BASE}/api/tracker`);
      const appsData = await appsRes.json();
      setApplications(appsData);

      // 3. Fetch Development Plan
      const devRes = await fetch(`${API_BASE}/api/devplan`);
      const devData = await devRes.json();
      setDevPlan(devData);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Onboarding upload handlers
  const handleCVUpload = async (e) => {
    e.preventDefault();
    if (!cvFile) return;
    setLoading(true);

    const formData = new FormData();
    formData.append('file', cvFile);

    try {
      const res = await fetch(`${API_BASE}/api/upload-cv`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setOnboardingQuestions(data.questions || []);
      setCurrentOnboardIdx(0);
      setOnboardAnswers([]);
      
      if (!data.questions || data.questions.length === 0) {
        // No questions generated, finalize
        setOnboarded(true);
        checkStatus();
      }
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleOnboardAnswerSubmit = async (answerText) => {
    const currentQ = onboardingQuestions[currentOnboardIdx];
    const newAnswers = [
      ...onboardAnswers,
      { question: currentQ.question, answer: answerText, category: currentQ.category }
    ];
    setOnboardAnswers(newAnswers);

    if (currentOnboardIdx + 1 < onboardingQuestions.length) {
      setCurrentOnboardIdx(currentOnboardIdx + 1);
    } else {
      // Finalized onboarding questions
      setLoading(true);
      try {
        await fetch(`${API_BASE}/api/onboard/answers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers: newAnswers }),
        });
        setOnboarded(true);
        checkStatus();
      } catch (err) {
        console.error('Failed submitting onboard answers:', err);
      } finally {
        setLoading(false);
      }
    }
  };

  // Job feeds
  const triggerJobMonitor = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/monitor`, { method: 'POST' });
      const data = await res.json();
      alert(data.detail);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddManualJob = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/api/jobs/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newJob),
      });
      if (res.ok) {
        setShowJobForm(false);
        setNewJob({ company: '', title: '', jd_text: '', location: 'Remote' });
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const analyzeJob = async (jobId) => {
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}/analyze`, { method: 'POST' });
      const data = await res.json();
      
      // Update local job analysis report immediately
      setJobs(prevJobs => prevJobs.map(j => j.id === jobId ? { ...j, confidence_score: data.score, match_report: JSON.stringify(data.analysis) } : j));
      
      const targetJob = jobs.find(j => j.id === jobId);
      if (targetJob) {
        setActiveJob({ ...targetJob, confidence_score: data.score, match_report: JSON.stringify(data.analysis) });
        setActiveJobAnalysis(data.analysis);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // /grill-me loop handlers
  const openGrillSession = async (job) => {
    setActiveJob(job);
    if (job.match_report) {
      setActiveJobAnalysis(JSON.parse(job.match_report));
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${job.id}/questions`);
      const data = await res.json();
      setGrillQuestions(data.questions || []);
      setCurrentGrillIdx(0);
      setGrillAnswers([]);
      setGrillModalOpen(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleGrillAnswerSubmit = async (ansText) => {
    const currentQ = grillQuestions[currentGrillIdx];
    const newAnswers = [
      ...grillAnswers,
      { question: currentQ.question, answer: ansText, category: currentQ.skill_target }
    ];
    setGrillAnswers(newAnswers);

    if (currentGrillIdx + 1 < grillQuestions.length && ansText.toLowerCase() !== 'skip') {
      setCurrentGrillIdx(currentGrillIdx + 1);
    } else {
      // Submit answers and trigger tailoring
      setLoading(true);
      try {
        await fetch(`${API_BASE}/api/jobs/${activeJob.id}/answers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers: newAnswers }),
        });
        setGrillModalOpen(false);
        // Automatically start tailoring
        triggerTailoring(activeJob.id);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
  };

  const triggerTailoring = async (jobId) => {
    setIsTailoring(true);
    setTailorResult(null);
    setTailorModalOpen(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}/tailor`, { method: 'POST' });
      const data = await res.json();
      setTailorResult(data);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      alert('Failed to compile tailored CV.');
      setTailorModalOpen(false);
    } finally {
      setIsTailoring(false);
    }
  };

  const confirmApplication = async (jobId, notesText) => {
    try {
      await fetch(`${API_BASE}/api/jobs/${jobId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'applied', notes: notesText }),
      });
      setTailorModalOpen(false);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  const updateApplicationStatus = async (jobId, newStatus) => {
    try {
      await fetch(`${API_BASE}/api/tracker/${jobId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchDashboardData();
    } catch (err) {
      console.error(err);
    }
  };

  // Onboard View
  if (!onboarded) {
    return (
      <div style={{ display: 'flex', width: '100%', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <div className="onboard-container">
          <div className="logo" style={{ paddingLeft: 0, textAlign: 'center', fontSize: '24px', margin: '0 auto 48px auto' }}>GO FOR IT</div>
          <h2 style={{ textAlign: 'center', marginBottom: '24px' }}>Welcome! Upload your LaTeX CV</h2>
          <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginBottom: '24px' }}>
            To begin, please drop your current resume source file (.tex format) below. We will parse it and run a general profiling session to start matching roles.
          </p>

          {onboardingQuestions.length === 0 ? (
            <form onSubmit={handleCVUpload}>
              <div className="dropzone" onClick={() => document.getElementById('latex_file').click()}>
                <input 
                  type="file" 
                  id="latex_file" 
                  accept=".tex" 
                  style={{ display: 'none' }} 
                  onChange={(e) => setCvFile(e.target.files[0])} 
                />
                {cvFile ? cvFile.name : 'Drag & drop or click to select a .tex file'}
              </div>
              <div style={{ textAlign: 'center' }}>
                <button type="submit" className="button" disabled={!cvFile || loading}>
                  {loading ? 'Uploading & Parsing...' : 'Parse Baseline Resume'}
                </button>
              </div>
            </form>
          ) : (
            <div>
              <div style={{ marginBottom: '16px', fontWeight: '600' }}>
                Onboarding Question ({currentOnboardIdx + 1} of {onboardingQuestions.length})
              </div>
              <div className="chat-bubble assistant" style={{ marginBottom: '24px', width: '100%', maxWidth: '100%' }}>
                {onboardingQuestions[currentOnboardIdx].question}
              </div>
              
              <div className="chat-input-area" style={{ padding: 0, border: 'none' }}>
                <input
                  type="text"
                  placeholder="Type your answer, or press Enter/click Skip..."
                  className="chat-input"
                  id="onboard_answer"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleOnboardAnswerSubmit(e.target.value || 'skip');
                      e.target.value = '';
                    }
                  }}
                />
                <button 
                  className="button"
                  onClick={() => {
                    const inp = document.getElementById('onboard_answer');
                    handleOnboardAnswerSubmit(inp.value || 'skip');
                    inp.value = '';
                  }}
                >
                  Submit
                </button>
                <button 
                  className="button secondary"
                  onClick={() => {
                    handleOnboardAnswerSubmit('skip');
                    document.getElementById('onboard_answer').value = '';
                  }}
                >
                  Skip
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <React.Fragment>
      {/* Sidebar navigation */}
      <div className="sidebar">
        <div className="logo">GO FOR IT</div>
        <div className="nav-links">
          <div className={`nav-link ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab('jobs')}>
            Discovered Jobs
          </div>
          <div className={`nav-link ${activeTab === 'tracker' ? 'active' : ''}`} onClick={() => setActiveTab('tracker')}>
            Tracker Dashboard
          </div>
          <div className={`nav-link ${activeTab === 'devplan' ? 'active' : ''}`} onClick={() => setActiveTab('devplan')}>
            Development Plan
          </div>
          <div className={`nav-link ${activeTab === 'onboard' ? 'active' : ''}`} onClick={() => setActiveTab('onboard')}>
            Resume Settings
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '12px', fontSize: '11px', color: 'var(--text-secondary)' }}>
          <div>LaTeX Compiler:</div>
          <div style={{ color: hasCompiler ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: '600' }}>
            {hasCompiler ? compilerName : 'Undetected'}
          </div>
        </div>
      </div>

      {/* Main layout contents */}
      <div className="content-area">
        {loading && <div style={{ color: 'var(--accent-blue)', marginBottom: '16px', fontWeight: '600' }}>Refreshing database...</div>}
        
        {/* Tab 1: Jobs */}
        {activeTab === 'jobs' && (
          <div>
            <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h1 className="panel-title">Discovered Jobs</h1>
                <p className="panel-subtitle">Filter keywords and countries dynamically using the monitor scheduler</p>
              </div>
              <div style={{ display: 'flex', gap: '12px' }}>
                <button className="button secondary" onClick={() => setShowJobForm(true)}>+ Add Manually</button>
                <button className="button" onClick={triggerJobMonitor}>Fetch Feed Updates</button>
              </div>
            </div>

            {/* Manual job creation dialog overlay */}
            {showJobForm && (
              <div className="modal-overlay">
                <div className="modal-content">
                  <button className="close-modal" onClick={() => setShowJobForm(false)}>✕</button>
                  <h2 style={{ marginBottom: '24px' }}>Add Job Description Manually</h2>
                  <form onSubmit={handleAddManualJob}>
                    <div className="form-group">
                      <label>Company Name</label>
                      <input 
                        type="text" 
                        required 
                        className="form-input" 
                        value={newJob.company} 
                        onChange={(e) => setNewJob({ ...newJob, company: e.target.value })} 
                      />
                    </div>
                    <div className="form-group">
                      <label>Job Title</label>
                      <input 
                        type="text" 
                        required 
                        className="form-input" 
                        value={newJob.title} 
                        onChange={(e) => setNewJob({ ...newJob, title: e.target.value })} 
                      />
                    </div>
                    <div className="form-group">
                      <label>Location / Country</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        value={newJob.location} 
                        onChange={(e) => setNewJob({ ...newJob, location: e.target.value })} 
                      />
                    </div>
                    <div className="form-group">
                      <label>Job Description Content</label>
                      <textarea 
                        required 
                        className="form-input" 
                        value={newJob.jd_text} 
                        onChange={(e) => setNewJob({ ...newJob, jd_text: e.target.value })} 
                      />
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
                      <button type="button" className="button secondary" onClick={() => setShowJobForm(false)}>Cancel</button>
                      <button type="submit" className="button">Add Job</button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* List jobs */}
            <div className="jobs-layout">
              {jobs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                  No jobs logged. Click "Fetch Feed Updates" or "+ Add Manually" to begin.
                </div>
              ) : (
                jobs.map(job => {
                  const report = job.match_report ? JSON.parse(job.match_report) : null;
                  
                  return (
                    <div key={job.id} className="job-card">
                      <div className="job-info">
                        <h3>{job.title}</h3>
                        <div className="job-company">{job.company}</div>
                        <div className="job-meta">
                          <span>{job.location || 'Remote'}</span>
                          <span>{job.created_at.split('T')[0]}</span>
                          <span className={`status-badge ${job.status}`}>{job.status}</span>
                        </div>

                        {report && (
                          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            <div style={{ display: 'flex', gap: '12px', fontSize: '12px' }}>
                              <span style={{ color: 'var(--accent-green)' }}>Matched: {(report.skills_matched || []).slice(0, 4).join(', ')}</span>
                              <span style={{ color: 'var(--text-secondary)' }}>|</span>
                              <span style={{ color: 'var(--text-secondary)' }}>Missing: {(report.skills_missing || []).slice(0, 4).join(', ')}</span>
                            </div>
                            {report.transferable_skills && report.transferable_skills.length > 0 && (
                              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                                Transferable: {report.transferable_skills[0].missing} bridged by {report.transferable_skills[0].transferable}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'flex-end' }}>
                        {job.confidence_score !== null ? (
                          <div style={{ fontSize: '20px', fontWeight: '700', color: job.confidence_score > 70 ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                            {job.confidence_score.toFixed(0)}% Match
                          </div>
                        ) : (
                          <button className="button secondary" disabled={isAnalyzing} onClick={() => analyzeJob(job.id)}>
                            {isAnalyzing ? 'Analyzing...' : 'Analyze Score'}
                          </button>
                        )}
                        
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            className="button secondary" 
                            disabled={job.confidence_score === null}
                            onClick={() => openGrillSession(job)}
                          >
                            Grill Me
                          </button>
                          <button 
                            className="button"
                            disabled={job.confidence_score === null}
                            onClick={() => triggerTailoring(job.id)}
                          >
                            Tailor CV
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Tracker */}
        {activeTab === 'tracker' && (
          <div>
            <div className="panel-header">
              <h1 className="panel-title">Application Tracker</h1>
              <p className="panel-subtitle">Keep track of your active recruitment pipelines</p>
            </div>

            <div className="tracker-columns">
              {['applied', 'interviewing', 'offer', 'rejected'].map(col => {
                const columnApps = applications.filter(a => a.status.toLowerCase() === col);
                const colTitle = col.charAt(0).toUpperCase() + col.slice(1);
                
                return (
                  <div key={col} className="tracker-column">
                    <div className="tracker-column-header">
                      <span>{colTitle}</span>
                      <span className="status-badge discovered">{columnApps.length}</span>
                    </div>
                    
                    {columnApps.length === 0 ? (
                      <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px', fontSize: '12px' }}>
                        No items
                      </div>
                    ) : (
                      columnApps.map(app => (
                        <div key={app.job_id} className="tracker-card">
                          <h4>{app.title}</h4>
                          <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '8px' }}>{app.company}</div>
                          {app.tailored_cv_path && (
                            <div style={{ fontSize: '11px', marginBottom: '8px' }}>
                              <a href={`${API_BASE}/output/${app.tailored_cv_path.split('/').pop()}`} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}>Tailored CV</a>
                            </div>
                          )}
                          
                          <select 
                            className="form-input" 
                            style={{ padding: '4px 8px', fontSize: '12px' }}
                            value={app.status} 
                            onChange={(e) => updateApplicationStatus(app.job_id, e.target.value)}
                          >
                            <option value="applied">Applied</option>
                            <option value="interviewing">Interviewing</option>
                            <option value="offer">Offer</option>
                            <option value="rejected">Rejected</option>
                          </select>
                        </div>
                      ))
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab 3: Development Plan */}
        {activeTab === 'devplan' && (
          <div>
            <div className="panel-header">
              <h1 className="panel-title">Career Development Roadmap</h1>
              <p className="panel-subtitle">Aggregated learning actions mapped to your skill gaps</p>
            </div>

            {!Array.isArray(devPlan.plan) || devPlan.plan.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                No active skill gaps registered in analyzed jobs yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '800px' }}>
                <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <h3>Skills Identified as Missing:</h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px' }}>
                    {(devPlan.missing_skills || []).map(s => (
                      <span key={s} className="status-badge discovered" style={{ fontSize: '12px', padding: '6px 12px' }}>{s}</span>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {devPlan.plan.map((item, idx) => (
                    <div key={idx} style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <h4 style={{ margin: 0, fontSize: '18px' }}>{item.skill}</h4>
                        <span className={`status-badge ${item.difficulty === 'Beginner' ? 'discovered' : 'grilled'}`}>{item.difficulty}</span>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.5' }}>{item.action}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Resume Settings */}
        {activeTab === 'onboard' && (
          <div>
            <div className="panel-header">
              <h1 className="panel-title">CV Baseline Settings</h1>
              <p className="panel-subtitle">Upload or update your current baseline LaTeX document</p>
            </div>

            <div className="onboard-container" style={{ margin: 0, maxWidth: '500px' }}>
              <h3>Update Base CV</h3>
              <form onSubmit={handleCVUpload}>
                <div className="dropzone" onClick={() => document.getElementById('latex_file_update').click()}>
                  <input 
                    type="file" 
                    id="latex_file_update" 
                    accept=".tex" 
                    style={{ display: 'none' }} 
                    onChange={(e) => setCvFile(e.target.files[0])} 
                  />
                  {cvFile ? cvFile.name : 'Click to select a new .tex file'}
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button type="submit" className="button" disabled={!cvFile || loading}>Update Resume</button>
                  {cvFile && <button type="button" className="button secondary" onClick={() => setCvFile(null)}>Clear</button>}
                </div>
              </form>
            </div>
          </div>
        )}
      </div>

      {/* Specific Job Grill-Me Interview Modal */}
      {grillModalOpen && activeJob && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button className="close-modal" onClick={() => setGrillModalOpen(false)}>✕</button>
            <h2 style={{ marginBottom: '8px' }}>Interviewing for: {activeJob.title}</h2>
            <p style={{ color: 'var(--text-secondary)', margin: '0 0 24px 0' }}>{activeJob.company}</p>

            {grillQuestions.length > 0 ? (
              <div>
                <div style={{ marginBottom: '16px', fontWeight: '600' }}>
                  Question ({currentGrillIdx + 1} of {grillQuestions.length})
                </div>
                <div className="chat-bubble assistant" style={{ marginBottom: '24px', width: '100%', maxWidth: '100%' }}>
                  {grillQuestions[currentGrillIdx].question}
                </div>
                
                <div className="chat-input-area" style={{ padding: 0, border: 'none' }}>
                  <input
                    type="text"
                    placeholder="Enter details, or click skip..."
                    className="chat-input"
                    id="grill_answer"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleGrillAnswerSubmit(e.target.value || 'skip');
                        e.target.value = '';
                      }
                    }}
                  />
                  <button 
                    className="button"
                    onClick={() => {
                      const inp = document.getElementById('grill_answer');
                      handleGrillAnswerSubmit(inp.value || 'skip');
                      inp.value = '';
                    }}
                  >
                    Submit
                  </button>
                  <button 
                    className="button secondary"
                    onClick={() => {
                      handleGrillAnswerSubmit('skip');
                      document.getElementById('grill_answer').value = '';
                    }}
                  >
                    Skip
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px' }}>No targeted questions required for this JD. Ready to compile tailored resume.</div>
            )}
          </div>
        </div>
      )}

      {/* Tailor & Apply Wizard Modal */}
      {tailorModalOpen && activeJob && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '850px', width: '90%' }}>
            <button className="close-modal" onClick={() => setTailorModalOpen(false)}>✕</button>
            
            <h2 style={{ marginBottom: '8px' }}>Tailored CV Compilation</h2>
            <p style={{ color: 'var(--text-secondary)', margin: '0 0 24px 0' }}>{activeJob.company} — {activeJob.title}</p>

            {isTailoring ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '12px', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--accent-blue)', marginBottom: '16px', fontWeight: '600' }}>Compiling</div>
                <h3>Optimizing LaTeX and Compiling...</h3>
                <p style={{ color: 'var(--text-secondary)' }}>Performing layout formatting checks and enforcing page budget.</p>
              </div>
            ) : tailorResult ? (
              <div>
                <div className="split-view" style={{ marginBottom: '24px' }}>
                  <div>
                    <h3>Successfully Compiled!</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.5' }}>
                      We optimized your resume text content to fit the target JD and ensured it complies with the strict 1-page layout requirement.
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {tailorResult.has_pdf ? (
                        <a 
                          href={`${API_BASE}${tailorResult.pdf_file}`} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="button"
                          style={{ textDecoration: 'none', textAlign: 'center' }}
                        >
                          Download Tailored PDF
                        </a>
                      ) : (
                        <div style={{ color: 'var(--accent-red)', fontWeight: '600', fontSize: '12px' }}>
                          PDF compilation warning: Tectonic/pdflatex not found. You can compile the LaTeX file yourself.
                        </div>
                      )}
                      
                      <a 
                        href={`${API_BASE}${tailorResult.tex_file}`} 
                        download 
                        className="button secondary"
                        style={{ textDecoration: 'none', textAlign: 'center' }}
                      >
                        Download LaTeX Source
                      </a>
                    </div>
                  </div>

                  <div className="preview-box">
                    <div style={{ fontSize: '12px', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '12px', fontWeight: '600' }}>Preview</div>
                    <div style={{ fontWeight: '600' }}>1 Page Tailored CV</div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '11px', marginTop: '6px' }}>Checked against layout template constraints</div>
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                  <h3>Confirm Application</h3>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>If you submit this resume to the employer, confirm here to log it on your pipeline dashboard.</p>
                  
                  <div className="form-group">
                    <input 
                      type="text" 
                      placeholder="Add application details (e.g. 'Applied via LinkedIn')" 
                      className="form-input" 
                      id="app_notes" 
                    />
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                    <button className="button secondary" onClick={() => setTailorModalOpen(false)}>Discard</button>
                    <button 
                      className="button" 
                      onClick={() => {
                        const notesVal = document.getElementById('app_notes').value;
                        confirmApplication(activeJob.id, notesVal);
                      }}
                    >
                      Confirm Applied
                    </button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </React.Fragment>
  );
}

export default App;
