import React, { useState, useEffect } from 'react';

const API_BASE = window.location.port === '5173' ? 'http://127.0.0.1:8000' : window.location.origin;

function App() {
  const [activeTab, setActiveTab] = useState('jobs');
  const [onboarded, setOnboarded] = useState(false);
  const [hasCompiler, setHasCompiler] = useState(false);
  const [compilerName, setCompilerName] = useState('');
  const [cvDetails, setCvDetails] = useState(null);
  const [appVersion, setAppVersion] = useState('');
  
  const [searchConfig, setSearchConfig] = useState({
    keywords: '',
    countries: '',
    cities: '',
    remote: true,
    languages: '',
    citizenship_restrictions: '',
    target_culture: 'Nordic'
  });
  
  // Dashboard states
  const [jobs, setJobs] = useState([]);
  const [applications, setApplications] = useState([]);
  const [devPlan, setDevPlan] = useState({ missing_skills: [], plan: [] });
  const [loading, setLoading] = useState(false);

  // Add job form state
  const [showJobForm, setShowJobForm] = useState(false);
  const [newJob, setNewJob] = useState({ company: '', title: '', jd_text: '', location: 'Remote' });

  // Job Monitors states
  const [monitors, setMonitors] = useState([]);
  const [monitorForm, setMonitorForm] = useState({ name: '', keywords: '', locations: '', remote: true, active: true });
  const [aiExtractorText, setAiExtractorText] = useState('');
  const [editingMonitorId, setEditingMonitorId] = useState(null);

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

  // Unified Tailor & Apply Wizard states
  const [wizardStep, setWizardStep] = useState(null); // 'loading', 'options', 'grilling', 'completed', or null
  const [wizardStatusText, setWizardStatusText] = useState('');

  useEffect(() => {
    checkStatus();
    fetchConfig();
    fetchMonitors();
  }, []);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`);
      const data = await res.json();
      if (data && data.search) {
        setSearchConfig({
          keywords: (data.search.keywords || []).join(', '),
          countries: (data.search.countries || []).join(', '),
          cities: (data.search.cities || []).join(', '),
          remote: data.search.remote ?? true,
          languages: (data.search.languages || []).join(', '),
          citizenship_restrictions: (data.search.citizenship_restrictions || []).join(', '),
          target_culture: data.culture?.target_culture || 'Nordic'
        });
      }
    } catch (err) {
      console.error('Error fetching config:', err);
    }
  };

  const fetchMonitors = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/monitors`);
      const data = await res.json();
      setMonitors(data);
    } catch (err) {
      console.error('Error fetching monitors:', err);
    }
  };

  const handleSaveMonitor = async (e) => {
    e.preventDefault();
    if (!monitorForm.name.trim()) {
      alert('Please provide a name for the monitor.');
      return;
    }
    setLoading(true);
    const payload = {
      name: monitorForm.name,
      keywords: monitorForm.keywords.split(',').map(s => s.trim()).filter(Boolean),
      locations: monitorForm.locations.split(',').map(s => s.trim()).filter(Boolean),
      remote: monitorForm.remote,
      active: monitorForm.active
    };

    try {
      let res;
      if (editingMonitorId) {
        res = await fetch(`${API_BASE}/api/monitors/${editingMonitorId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(`${API_BASE}/api/monitors`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      if (res.ok) {
        setMonitorForm({ name: '', keywords: '', locations: '', remote: true, active: true });
        setEditingMonitorId(null);
        await fetchMonitors();
        alert(editingMonitorId ? 'Monitor updated successfully!' : 'Monitor created successfully!');
      } else {
        alert('Failed to save monitor.');
      }
    } catch (err) {
      console.error(err);
      alert('Error saving monitor.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleMonitorActive = async (monitor) => {
    try {
      const payload = {
        name: monitor.name,
        keywords: monitor.keywords,
        locations: monitor.locations,
        remote: monitor.remote,
        active: !monitor.active
      };
      const res = await fetch(`${API_BASE}/api/monitors/${monitor.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        await fetchMonitors();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteMonitor = async (monitorId) => {
    if (!confirm('Are you sure you want to delete this monitor?')) return;
    try {
      const res = await fetch(`${API_BASE}/api/monitors/${monitorId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchMonitors();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleExtractPreferences = async () => {
    if (!aiExtractorText.trim()) {
      alert('Please type or paste some text describing the jobs you want to monitor.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/monitors/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: aiExtractorText })
      });
      if (res.ok) {
        const data = await res.json();
        setMonitorForm({
          name: data.name || 'Extracted Monitor',
          keywords: (data.keywords || []).join(', '),
          locations: (data.locations || []).join(', '),
          remote: data.remote ?? true,
          active: true
        });
        setAiExtractorText('');
        alert('Job preferences extracted successfully! Review the populated form below and click Save.');
      } else {
        alert('Failed to extract preferences.');
      }
    } catch (err) {
      console.error(err);
      alert('Error extracting preferences.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const payload = {
      search: {
        keywords: searchConfig.keywords.split(',').map(s => s.trim()).filter(Boolean),
        countries: searchConfig.countries.split(',').map(s => s.trim()).filter(Boolean),
        cities: searchConfig.cities.split(',').map(s => s.trim()).filter(Boolean),
        remote: searchConfig.remote,
        languages: searchConfig.languages.split(',').map(s => s.trim()).filter(Boolean),
        citizenship_restrictions: searchConfig.citizenship_restrictions.split(',').map(s => s.trim()).filter(Boolean),
      },
      culture: {
        target_culture: searchConfig.target_culture
      }
    };

    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        alert('System preferences saved successfully!');
      } else {
        alert('Failed to save configuration.');
      }
    } catch (err) {
      console.error(err);
      alert('Error saving configuration.');
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      const data = await res.json();
      setOnboarded(data.onboarded);
      setHasCompiler(data.has_compiler);
      setCompilerName(data.compiler_detected || 'None');
      setAppVersion(data.version || '');
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

      // 4. Fetch Monitors
      await fetchMonitors();
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Onboarding upload handlers
  const handleSkipOnboarding = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/onboard/skip`, {
        method: 'POST'
      });
      if (res.ok) {
        setOnboarded(true);
        checkStatus();
      } else {
        alert('Failed to skip onboarding.');
      }
    } catch (err) {
      console.error(err);
      alert('Error skipping onboarding.');
    } finally {
      setLoading(false);
    }
  };

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

  // Unified Tailor & Apply Wizard handlers
  const startTailorApplyWizard = async (job) => {
    setActiveJob(job);
    setTailorResult(null);
    setGrillAnswers([]);
    setCurrentGrillIdx(0);
    setGrillQuestions([]);
    
    if (job.confidence_score !== null) {
      if (job.match_report) {
        setActiveJobAnalysis(JSON.parse(job.match_report));
      }
      setWizardStep('options');
    } else {
      setWizardStep('loading');
      setWizardStatusText('Analyzing Job Match and Skill Gaps...');
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${job.id}/analyze`, { method: 'POST' });
        if (!res.ok) throw new Error('Analysis failed');
        const data = await res.json();
        
        // Update local jobs list so the score shows up
        setJobs(prevJobs => prevJobs.map(j => j.id === job.id ? { ...j, confidence_score: data.score, match_report: JSON.stringify(data.analysis) } : j));
        
        // Update active job reference and analysis
        setActiveJob({ ...job, confidence_score: data.score, match_report: JSON.stringify(data.analysis) });
        setActiveJobAnalysis(data.analysis);
        setWizardStep('options');
      } catch (err) {
        console.error(err);
        alert('Failed to analyze job match.');
        setWizardStep(null);
        setActiveJob(null);
      }
    }
  };

  const startWizardGrilling = async () => {
    setWizardStep('loading');
    setWizardStatusText('Generating targeted interview questions...');
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${activeJob.id}/questions`);
      if (!res.ok) throw new Error('Failed to fetch questions');
      const data = await res.json();
      if (data.questions && data.questions.length > 0) {
        setGrillQuestions(data.questions);
        setCurrentGrillIdx(0);
        setGrillAnswers([]);
        setWizardStep('grilling');
      } else {
        alert('No gap-bridging questions required for this job description. Proceeding to tailor CV...');
        await triggerWizardTailoring();
      }
    } catch (err) {
      console.error(err);
      alert('Error fetching interview questions. Proceeding to tailor CV directly.');
      await triggerWizardTailoring();
    }
  };

  const triggerWizardTailoring = async () => {
    setWizardStep('loading');
    setWizardStatusText('Personalizing resume text and checking page budget constraints...');
    setTailorResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${activeJob.id}/tailor`, { method: 'POST' });
      if (!res.ok) throw new Error('Tailoring failed');
      const data = await res.json();
      setTailorResult(data);
      
      // Update jobs list in background to mark as tailored
      setJobs(prevJobs => prevJobs.map(j => j.id === activeJob.id ? { ...j, status: 'tailored' } : j));
      
      // Refresh dashboard data
      fetchDashboardData();
      
      setWizardStep('completed');
    } catch (err) {
      console.error(err);
      alert('Failed to compile tailored CV.');
      setWizardStep('options');
    }
  };

  const handleWizardGrillAnswerSubmit = async (ansText) => {
    const currentQ = grillQuestions[currentGrillIdx];
    const newAnswers = [
      ...grillAnswers,
      { question: currentQ.question, answer: ansText, category: currentQ.skill_target }
    ];
    setGrillAnswers(newAnswers);

    if (currentGrillIdx + 1 < grillQuestions.length && ansText.toLowerCase() !== 'skip') {
      setCurrentGrillIdx(currentGrillIdx + 1);
    } else {
      setWizardStep('loading');
      setWizardStatusText('Saving answers and personalizing resume text...');
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${activeJob.id}/answers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers: newAnswers }),
        });
        if (!res.ok) throw new Error('Failed to save answers');
        
        await triggerWizardTailoring();
      } catch (err) {
        console.error(err);
        alert('Failed to save interview answers. Proceeding to tailor CV anyway.');
        await triggerWizardTailoring();
      }
    }
  };

  const confirmWizardApplication = async (notesText) => {
    setWizardStep('loading');
    setWizardStatusText('Logging application in tracker dashboard...');
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${activeJob.id}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'applied', notes: notesText }),
      });
      if (!res.ok) throw new Error('Failed to apply');
      
      setWizardStep(null);
      setActiveJob(null);
      fetchDashboardData();
    } catch (err) {
      console.error(err);
      alert('Failed to log application status. Close the wizard to view the dashboard.');
      setWizardStep('completed');
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
          <div className="logo" style={{ paddingLeft: 0, textAlign: 'center', fontSize: '24px' }}>🤖 JOB AGENT SYSTEM</div>
          <h2 style={{ textAlign: 'center', marginBottom: '24px' }}>Welcome! Upload your Resume</h2>
          <p style={{ color: 'var(--text-secondary)', textAlign: 'center', marginBottom: '24px' }}>
            To begin, please drop your current resume file (.tex or .pdf format) below. We will parse it and run a general profiling session to start matching roles.
          </p>

          {onboardingQuestions.length === 0 ? (
            <form onSubmit={handleCVUpload}>
              <div className="dropzone" onClick={() => document.getElementById('latex_file').click()}>
                <input 
                  type="file" 
                  id="latex_file" 
                  accept=".tex,.pdf" 
                  style={{ display: 'none' }} 
                  onChange={(e) => setCvFile(e.target.files[0])} 
                />
                {cvFile ? `📄 ${cvFile.name}` : 'Drag & drop or click to select a .tex or .pdf file'}
              </div>
              <div style={{ textAlign: 'center' }}>
                <button type="submit" className="button" disabled={!cvFile || loading}>
                  {loading ? 'Uploading & Parsing...' : 'Parse Baseline Resume'}
                </button>
              </div>
              <div style={{ textAlign: 'center', marginTop: '16px' }}>
                <button type="button" className="button secondary" onClick={handleSkipOnboarding} disabled={loading}>
                  Skip & Go to Dashboard (Blank Slate)
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
        <div className="logo">🤖 JOB TAILOR AGENT</div>
        <div className="nav-links">
          <div className={`nav-link ${activeTab === 'jobs' ? 'active' : ''}`} onClick={() => setActiveTab('jobs')}>
            🔍 Discovered Jobs
          </div>
          <div className={`nav-link ${activeTab === 'tracker' ? 'active' : ''}`} onClick={() => setActiveTab('tracker')}>
            📋 Tracker Dashboard
          </div>
          <div className={`nav-link ${activeTab === 'devplan' ? 'active' : ''}`} onClick={() => setActiveTab('devplan')}>
            ⚡ Development Plan
          </div>
          <div className={`nav-link ${activeTab === 'onboard' ? 'active' : ''}`} onClick={() => setActiveTab('onboard')}>
            ⚙️ System Settings
          </div>
        </div>

        <div style={{ marginTop: 'auto', padding: '12px', fontSize: '11px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div>
            <div>LaTeX Compiler:</div>
            <div style={{ color: hasCompiler ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: '600', marginTop: '2px' }}>
              {hasCompiler ? `🟩 ${compilerName}` : '🟥 Undetected'}
            </div>
          </div>
          {appVersion && (
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '8px' }}>
              <div>System Version:</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: '600', marginTop: '2px' }}>
                v{appVersion}
              </div>
            </div>
          )}
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
                          <span>📍 {job.location || 'Remote'}</span>
                          <span>📅 {job.created_at.split('T')[0]}</span>
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
                                💡 Transferable: {report.transferable_skills[0].missing} bridged by {report.transferable_skills[0].transferable}
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'flex-end' }}>
                        {job.confidence_score !== null && (
                          <div style={{ fontSize: '20px', fontWeight: '700', color: job.confidence_score > 70 ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                            {job.confidence_score.toFixed(0)}% Match
                          </div>
                        )}
                        
                        <button 
                          className="button"
                          onClick={() => startTailorApplyWizard(job)}
                        >
                          ✨ Tailor & Apply
                        </button>
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
                              📄 <a href={`${API_BASE}/output/${app.tailored_cv_path.split('/').pop()}`} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-blue)', textDecoration: 'none' }}>Tailored CV</a>
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

        {/* Tab 4: System Settings */}
        {activeTab === 'onboard' && (
          <div>
            <div className="panel-header">
              <h1 className="panel-title">System Settings</h1>
              <p className="panel-subtitle">Manage your job search preferences, recruitment culture, and baseline CV document</p>
            </div>

            <div className="split-view">
              {/* Left Column: Job Monitors Manager */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                
                {/* AI preference extraction */}
                <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '8px' }}>AI Preferences Extractor</h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '12px', margin: '0 0 16px 0' }}>
                    Type your search preference in natural language to automatically extract filter criteria.
                  </p>
                  <div className="form-group">
                    <textarea 
                      className="form-input" 
                      style={{ minHeight: '80px' }}
                      value={aiExtractorText}
                      onChange={(e) => setAiExtractorText(e.target.value)}
                      placeholder="e.g., I want to look for React developer jobs in Sweden or Norway, and remote is fine."
                    />
                  </div>
                  <button type="button" className="button" onClick={handleExtractPreferences} disabled={loading}>
                    ✨ Extract Search Config
                  </button>
                </div>

                {/* Monitor editing/creation form */}
                <div 
                  id="monitor-form-container"
                  style={{ 
                    background: 'var(--bg-secondary)', 
                    padding: '24px', 
                    borderRadius: '12px', 
                    border: editingMonitorId ? '2px solid var(--accent-blue)' : '1px solid var(--border-color)',
                    transition: 'border 0.2s ease-in-out'
                  }}
                >
                  <h3 style={{ marginTop: 0, marginBottom: '20px' }}>
                    {editingMonitorId ? '✏️ Edit Job Monitor' : '➕ Create Job Monitor'}
                  </h3>
                  <form onSubmit={handleSaveMonitor}>
                    <div className="form-group">
                      <label>Monitor Name</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={monitorForm.name}
                        onChange={(e) => setMonitorForm({ ...monitorForm, name: e.target.value })}
                        placeholder="e.g., Python Stockholm Remote"
                        required
                      />
                    </div>
                    
                    <div className="form-group">
                      <label>Keywords (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={monitorForm.keywords}
                        onChange={(e) => setMonitorForm({ ...monitorForm, keywords: e.target.value })}
                        placeholder="e.g., Python, FastAPI, Django"
                      />
                    </div>

                    <div className="form-group">
                      <label>Locations (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={monitorForm.locations}
                        onChange={(e) => setMonitorForm({ ...monitorForm, locations: e.target.value })}
                        placeholder="e.g., Stockholm, Sweden"
                      />
                    </div>

                    <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <input 
                        type="checkbox" 
                        id="monitor_remote"
                        checked={monitorForm.remote}
                        onChange={(e) => setMonitorForm({ ...monitorForm, remote: e.target.checked })}
                      />
                      <label htmlFor="monitor_remote" style={{ marginBottom: 0, cursor: 'pointer' }}>Allow Remote Positions</label>
                    </div>

                    <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <input 
                        type="checkbox" 
                        id="monitor_active"
                        checked={monitorForm.active}
                        onChange={(e) => setMonitorForm({ ...monitorForm, active: e.target.checked })}
                      />
                      <label htmlFor="monitor_active" style={{ marginBottom: 0, cursor: 'pointer' }}>Active (Runs 24/7)</label>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                      <button type="submit" className="button">
                        {editingMonitorId ? 'Save Changes' : 'Create Monitor'}
                      </button>
                      {editingMonitorId && (
                        <button 
                          type="button" 
                          className="button secondary" 
                          onClick={() => {
                            setEditingMonitorId(null);
                            setMonitorForm({ name: '', keywords: '', locations: '', remote: true, active: true });
                          }}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </form>
                </div>

                {/* Active/configured monitors list */}
                <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Configured Monitors ({monitors.length})</h3>
                  {monitors.length === 0 ? (
                    <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>No monitors configured yet. Add one above to start monitoring 24/7.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {monitors.map(m => (
                        <div key={m.id} className="monitor-card" style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <strong style={{ fontSize: '15px' }}>{m.name}</strong>
                              <span className={`status-badge ${m.active ? 'applied' : 'discovered'}`} style={{ fontSize: '10px' }}>
                                {m.active ? 'Active' : 'Inactive'}
                              </span>
                            </div>
                            
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                              {(m.keywords || []).map(kw => (
                                <span key={kw} className="monitor-tag" style={{ background: 'var(--bg-tertiary)', fontSize: '11px', padding: '2px 6px', borderRadius: '4px' }}>
                                  {kw}
                                </span>
                              ))}
                              {(m.locations || []).map(loc => (
                                <span key={loc} className="monitor-tag" style={{ background: 'var(--bg-tertiary)', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--accent-blue)' }}>
                                  📍 {loc}
                                </span>
                              ))}
                              {m.remote && (
                                <span className="monitor-tag" style={{ background: 'var(--bg-tertiary)', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--accent-green)' }}>
                                  🌐 Remote
                                </span>
                              )}
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: '8px' }}>
                            <button 
                              className="button secondary" 
                              style={{ padding: '6px 12px', fontSize: '11px' }}
                              onClick={() => handleToggleMonitorActive(m)}
                            >
                              {m.active ? 'Pause' : 'Activate'}
                            </button>
                            <button 
                              className="button secondary" 
                              style={{ padding: '6px 12px', fontSize: '11px' }}
                              onClick={() => {
                                setEditingMonitorId(m.id);
                                setMonitorForm({
                                  name: m.name,
                                  keywords: (m.keywords || []).join(', '),
                                  locations: (m.locations || []).join(', '),
                                  remote: m.remote,
                                  active: m.active
                                });
                                setTimeout(() => {
                                  document.getElementById('monitor-form-container')?.scrollIntoView({ behavior: 'smooth' });
                                }, 50);
                              }}
                            >
                              Edit
                            </button>
                            <button 
                              className="button secondary" 
                              style={{ padding: '6px 12px', fontSize: '11px', borderColor: 'var(--accent-red)', color: 'var(--accent-red)' }}
                              onClick={() => handleDeleteMonitor(m.id)}
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

              </div>

              {/* Right Column: CV Baseline & Culture */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* CV Baseline Card */}
                <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border-color)', height: 'fit-content' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Baseline CV Document</h3>
                  <form onSubmit={handleCVUpload}>
                    <div className="dropzone" onClick={() => document.getElementById('latex_file_update').click()}>
                      <input 
                        type="file" 
                        id="latex_file_update" 
                        accept=".tex,.pdf" 
                        style={{ display: 'none' }} 
                        onChange={(e) => setCvFile(e.target.files[0])} 
                      />
                      {cvFile ? `📄 ${cvFile.name}` : 'Click to select a new .tex or .pdf file'}
                    </div>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button type="submit" className="button" disabled={!cvFile || loading}>Update CV Source</button>
                      {cvFile && <button type="button" className="button secondary" onClick={() => setCvFile(null)}>Clear</button>}
                    </div>
                  </form>
                </div>

                {/* Culture & System Settings Card */}
                <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                  <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Global System Preferences</h3>
                  <form onSubmit={handleSaveConfig}>
                    <div className="form-group">
                      <label>Job Search Keywords (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={searchConfig.keywords}
                        onChange={(e) => setSearchConfig({ ...searchConfig, keywords: e.target.value })}
                        placeholder="e.g., Python Engineer, AI Engineer, Software Developer"
                      />
                    </div>
                    
                    <div className="form-group">
                      <label>Target Countries (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={searchConfig.countries}
                        onChange={(e) => setSearchConfig({ ...searchConfig, countries: e.target.value })}
                        placeholder="e.g., Sweden, Norway, Denmark"
                      />
                    </div>

                    <div className="form-group">
                      <label>Target Cities (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={searchConfig.cities}
                        onChange={(e) => setSearchConfig({ ...searchConfig, cities: e.target.value })}
                        placeholder="e.g., Gothenburg, Stockholm"
                      />
                    </div>

                    <div className="form-group">
                      <label>Preferred Languages (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={searchConfig.languages}
                        onChange={(e) => setSearchConfig({ ...searchConfig, languages: e.target.value })}
                        placeholder="e.g., English, Swedish"
                      />
                    </div>

                    <div className="form-group">
                      <label>Citizenship/Visa Restrictions (comma separated)</label>
                      <input 
                        type="text" 
                        className="form-input"
                        value={searchConfig.citizenship_restrictions}
                        onChange={(e) => setSearchConfig({ ...searchConfig, citizenship_restrictions: e.target.value })}
                        placeholder="e.g., EU Citizen, Visa Sponsorship"
                      />
                    </div>

                    <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <input 
                        type="checkbox" 
                        id="global_remote"
                        checked={searchConfig.remote}
                        onChange={(e) => setSearchConfig({ ...searchConfig, remote: e.target.checked })}
                      />
                      <label htmlFor="global_remote" style={{ marginBottom: 0, cursor: 'pointer' }}>Allow Remote Positions</label>
                    </div>

                    <div className="form-group" style={{ marginTop: '20px' }}>
                      <label>Target Recruitment Culture</label>
                      <select 
                        className="form-input"
                        value={searchConfig.target_culture}
                        onChange={(e) => setSearchConfig({ ...searchConfig, target_culture: e.target.value })}
                      >
                        <option value="Nordic">Nordic (Focus on collaboration & soft skills)</option>
                        <option value="US">US (Focus on ownership & explicit metrics)</option>
                        <option value="Central Europe">Central Europe (Focus on structure & certifications)</option>
                      </select>
                    </div>

                    <button type="submit" className="button" style={{ marginTop: '16px', width: '100%' }}>
                      💾 Save System Preferences
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Unified Tailor & Apply Wizard Modal */}
      {wizardStep !== null && activeJob && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '800px', width: '90%' }}>
            <button 
              className="close-modal" 
              onClick={() => {
                setWizardStep(null);
                setActiveJob(null);
              }}
            >
              ✕
            </button>
            
            <h2 style={{ marginBottom: '8px' }}>Tailor & Apply Wizard</h2>
            <p style={{ color: 'var(--text-secondary)', margin: '0 0 24px 0' }}>{activeJob.company} — {activeJob.title}</p>

            {/* STEP: LOADING */}
            {wizardStep === 'loading' && (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <div style={{ fontSize: '32px', marginBottom: '16px', animation: 'spin 2s linear infinite' }}>⚙️</div>
                <h3>{wizardStatusText}</h3>
                <p style={{ color: 'var(--text-secondary)' }}>This may take up to a minute. Please stand by.</p>
              </div>
            )}

            {/* STEP: OPTIONS (Analysis & Decisions) */}
            {wizardStep === 'options' && activeJobAnalysis && (
              <div>
                <div className="split-view" style={{ marginBottom: '24px' }}>
                  <div>
                    <h3>Match Analysis</h3>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '16px' }}>
                      <span style={{ fontSize: '36px', fontWeight: '800', color: activeJob.confidence_score > 70 ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                        {activeJob.confidence_score ? activeJob.confidence_score.toFixed(0) : '0'}%
                      </span>
                      <span style={{ color: 'var(--text-secondary)' }}>Match Score</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div>
                        <strong style={{ display: 'block', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Matched Skills</strong>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {(activeJobAnalysis.skills_matched || []).length === 0 ? (
                            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>None identified</span>
                          ) : (
                            (activeJobAnalysis.skills_matched || []).map(s => (
                              <span key={s} className="status-badge applied" style={{ fontSize: '11px' }}>{s}</span>
                            ))
                          )}
                        </div>
                      </div>

                      <div>
                        <strong style={{ display: 'block', marginBottom: '4px', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Missing Skills</strong>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {(activeJobAnalysis.skills_missing || []).length === 0 ? (
                            <span style={{ fontSize: '13px', color: 'var(--accent-green)' }}>None! You match all required skills.</span>
                          ) : (
                            (activeJobAnalysis.skills_missing || []).map(s => (
                              <span key={s} className="status-badge rejected" style={{ fontSize: '11px' }}>{s}</span>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div>
                    {activeJobAnalysis.transferable_skills && activeJobAnalysis.transferable_skills.length > 0 && (
                      <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '16px' }}>
                        <h4 style={{ marginTop: 0, marginBottom: '8px', color: 'var(--accent-blue)' }}>💡 Transferable Skill Bridging</h4>
                        {activeJobAnalysis.transferable_skills.map((t, idx) => (
                          <div key={idx} style={{ fontSize: '12px', marginBottom: '8px', lineHeight: '1.4' }}>
                            <strong>{t.missing}</strong> can be bridged by your experience in <strong>{t.transferable}</strong>.
                            <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>{t.rationale}</div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <h4 style={{ marginTop: 0, marginBottom: '8px' }}>Choose Recruitment Action</h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '0 0 16px 0', lineHeight: '1.4' }}>
                        To personalize your CV, you can either conduct a targeted interview to explain your experiences, or skip directly to compile a tailored resume.
                      </p>
                      
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <button className="button" onClick={startWizardGrilling}>
                          🎤 Bridge Gaps (Start Interview)
                        </button>
                        <button className="button secondary" onClick={triggerWizardTailoring}>
                          ⚡ Skip & Tailor Directly
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
                  <button 
                    className="button secondary" 
                    onClick={() => {
                      setWizardStep(null);
                      setActiveJob(null);
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* STEP: GRILLING */}
            {wizardStep === 'grilling' && grillQuestions.length > 0 && (
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
                    placeholder="Type your answer, or press Enter/click Skip..."
                    className="chat-input"
                    id="wizard_grill_answer"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleWizardGrillAnswerSubmit(e.target.value || 'skip');
                        e.target.value = '';
                      }
                    }}
                  />
                  <button 
                    className="button"
                    onClick={() => {
                      const inp = document.getElementById('wizard_grill_answer');
                      handleWizardGrillAnswerSubmit(inp.value || 'skip');
                      inp.value = '';
                    }}
                  >
                    Submit
                  </button>
                  <button 
                    className="button secondary"
                    onClick={() => {
                      handleWizardGrillAnswerSubmit('skip');
                      document.getElementById('wizard_grill_answer').value = '';
                    }}
                  >
                    Skip
                  </button>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '16px', marginTop: '24px' }}>
                  <button 
                    className="button secondary" 
                    onClick={() => setWizardStep('options')}
                  >
                    Exit Interview
                  </button>
                </div>
              </div>
            )}

            {/* STEP: COMPLETED */}
            {wizardStep === 'completed' && tailorResult && (
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
                          📥 Download Tailored PDF
                        </a>
                      ) : (
                        <div style={{ color: 'var(--accent-red)', fontWeight: '600', fontSize: '12px' }}>
                          PDF compilation warning: Playwright/LaTeX compiler not found. You can compile the LaTeX file yourself.
                        </div>
                      )}
                      
                      <a 
                        href={`${API_BASE}${tailorResult.tex_file}`} 
                        download 
                        className="button secondary"
                        style={{ textDecoration: 'none', textAlign: 'center' }}
                      >
                        📥 Download LaTeX Source
                      </a>
                    </div>
                  </div>

                  <div className="preview-box">
                    <div style={{ fontSize: '48px', marginBottom: '12px' }}>📄</div>
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
                      id="wizard_app_notes" 
                    />
                  </div>
                  
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                    <button 
                      className="button secondary" 
                      onClick={() => {
                        setWizardStep(null);
                        setActiveJob(null);
                      }}
                    >
                      Close Wizard
                    </button>
                    <button 
                      className="button" 
                      onClick={() => {
                        const notesVal = document.getElementById('wizard_app_notes').value;
                        confirmWizardApplication(notesVal);
                      }}
                    >
                      Confirm Applied
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </React.Fragment>
  );
}

export default App;
