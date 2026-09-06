/**
 * User Dashboard Page (Phase 4 / Phase 5 Conversion)
 * Visualizes user progress, score trends, and saved analysis history.
 * Adds Light/Dark theme toggles and session logout options.
 */

import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getUserHistory, ReportItem } from '../services/api';
import './Analytics.css';

interface ChartDataPoint {
  date: string;
  score: number;
  type: string;
}

interface SpeechDataPoint {
  date: string;
  wpm: number;
  fillerWords: number;
}

const Analytics: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  // ===== STATE MANAGEMENT =====
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Dashboard navigation tabs: 'overview' (charts) vs 'history' (list of past reports)
  const [activeTab, setActiveTab] = useState<'overview' | 'history'>('overview');
  
  // Global theme toggle: 'dark' (default) vs 'light'
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark';
  });
  
  // Historical report overlay details modal state
  const [activeReport, setActiveReport] = useState<ReportItem | null>(null);

  // ===== THEME EFFECTS =====
  useEffect(() => {
    if (theme === 'light') {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // ===== HISTORY DATA FETCH =====
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getUserHistory();
        setReports(data.reports);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load progress analytics');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (loading) {
    return (
      <div className="analytics-loading">
        <div className="spinner"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analytics-error">
        <p>Error loading dashboard: {error}</p>
      </div>
    );
  }

  // ===== DATA TRANSFORMATIONS =====
  
  // Sort reports chronologically for trends
  const sortedReports = [...reports].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  // Sort reports newest-first for the Saved History list
  const historyReports = [...reports].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const documentReports = sortedReports.filter(
    (r) => r.report_type === 'document_analysis' || r.report_type === 'presentation_analysis' || r.report_type === 'presentation_rewrite'
  );
  const speechReports = sortedReports.filter(
    (r) => r.report_type === 'speech_analysis' || r.report_type === 'live_coaching'
  );

  // 1. Overall Score History Data
  const scoreHistoryData: ChartDataPoint[] = sortedReports.map((r) => {
    const dateStr = new Date(r.created_at).toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
    });
    
    // Check if score exists in document or speech report json
    const isDoc = r.report_type === 'document_analysis' || r.report_type === 'presentation_analysis' || r.report_type === 'presentation_rewrite';
    const score = isDoc
      ? r.report_json.overall_score || 75
      : r.report_json.overall_score || r.report_json.clarity_score || 70;

    return {
      date: dateStr,
      score: score || 0,
      type: isDoc ? 'Presentation / Document' : 'Speech',
    };
  });

  // 2. Speech Pacing & Filler Word Data
  const speechPacingData: SpeechDataPoint[] = speechReports.map((r) => {
    const dateStr = new Date(r.created_at).toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
    });
    
    // Support speech analyzer or live coach metrics formats
    const wpm = r.report_json.speech_speed_wpm || r.report_json.session_metrics?.avg_wpm || 0;
    const fillers = r.report_json.filler_words_count || r.report_json.session_metrics?.total_fillers || 0;

    return {
      date: dateStr,
      wpm: wpm,
      fillerWords: fillers,
    };
  });

  // 3. Category Average Scores (for latest document)
  const latestDoc = documentReports[documentReports.length - 1];
  const categoryScoresData = latestDoc && latestDoc.report_json.category_scores
    ? Object.entries(latestDoc.report_json.category_scores).map(([category, score]) => ({
        category: category.replace(/_/g, ' '),
        score: score as number,
      }))
    : [
        { category: 'Structure', score: 0 },
        { category: 'Clarity', score: 0 },
        { category: 'Persuasion', score: 0 },
        { category: 'Content Quality', score: 0 },
        { category: 'Call to Action', score: 0 },
      ];

  // ===== STATS CALCULATIONS =====
  const totalDocs = documentReports.length;
  const totalSpeeches = speechReports.length;

  const avgDocScore = totalDocs > 0
    ? Math.round(documentReports.reduce((sum, r) => sum + (r.report_json.overall_score || 0), 0) / totalDocs)
    : 0;

  const avgSpeechScore = totalSpeeches > 0
    ? Math.round(speechReports.reduce((sum, r) => {
        const score = r.report_json.overall_score || r.report_json.clarity_score || 70;
        return sum + score;
      }, 0) / totalSpeeches)
    : 0;

  const avgWpm = totalSpeeches > 0
    ? Math.round(speechReports.reduce((sum, r) => {
        const wpm = r.report_json.speech_speed_wpm || r.report_json.session_metrics?.avg_wpm || 0;
        return sum + wpm;
      }, 0) / totalSpeeches)
    : 0;

  return (
    <div className="analytics-page">
      
      {/* Premium Dashboard Header actions */}
      <div className="analytics-header">
        <div className="header-meta">
          <h1>User Dashboard</h1>
          <p className="subtitle">Welcome back, <strong>{user?.name || 'User'}</strong>! Track your progress and manage saved sessions.</p>
        </div>
        
        <div className="header-actions">
          {/* Theme Switcher Toggle */}
          <button onClick={toggleTheme} className="theme-toggle-btn" title="Toggle Light/Dark Theme">
            {theme === 'dark' ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="4"></circle>
                <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>
              </svg>
            )}
          </button>
          
          {/* Logout Button */}
          <button onClick={handleLogout} className="logout-btn" title="Sign Out">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"></path>
            </svg>
            <span>Logout</span>
          </button>
        </div>
      </div>

      {/* Tabs Navigation Selectors */}
      <div className="dashboard-tabs">
        <button 
          className={`dash-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="9"></rect>
            <rect x="14" y="3" width="7" height="5"></rect>
            <rect x="14" y="12" width="7" height="9"></rect>
            <rect x="3" y="16" width="7" height="5"></rect>
          </svg>
          <span>Progress Overview</span>
        </button>
        <button 
          className={`dash-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 8v4l3 3M21 12a9 9 0 1 1-9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"></path>
            <polyline points="21 3 21 8 16 8"></polyline>
          </svg>
          <span>Saved History</span>
        </button>
      </div>

      {/* TAB 1: OVERVIEW & PROGRESS CHARTS */}
      {activeTab === 'overview' && (
        <div className="overview-tab-content fadeIn">
          {/* Stats Overview Grid */}
          <section className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
              </div>
              <div className="stat-content">
                <h4>Presentations & Documents</h4>
                <div className="stat-value">{totalDocs}</div>
                <p className="stat-subtext">Avg Score: {avgDocScore}/100</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="22"></line>
                </svg>
              </div>
              <div className="stat-content">
                <h4>Speeches Coached</h4>
                <div className="stat-value">{totalSpeeches}</div>
                <p className="stat-subtext">Avg Score: {avgSpeechScore}/100</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <div className="stat-content">
                <h4>Average Speaking Pace</h4>
                <div className="stat-value">{avgWpm} <span className="stat-unit">WPM</span></div>
                <p className="stat-subtext">
                  {avgWpm > 160 ? 'Too Fast' : avgWpm < 100 ? 'Too Slow' : 'Optimal Pace'}
                </p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m22 7-8.5 8.5-5-5L2 17"></path>
                  <polyline points="16 7 22 7 22 13"></polyline>
                </svg>
              </div>
              <div className="stat-content">
                <h4>Overall Progress</h4>
                <div className="stat-value">
                  {totalDocs + totalSpeeches > 1 ? 'Growing' : 'Starter'}
                </div>
                <p className="stat-subtext">Keep practicing to build your history!</p>
              </div>
            </div>
          </section>

          {/* Chart Section Grid */}
          <div className="charts-grid" style={{ marginTop: '2rem' }}>
            
            {/* 1. Score Progress Line Chart */}
            <section className="chart-container-card">
              <h3>Score Improvement Trend</h3>
              <p className="chart-subtitle">History of overall scores for documents and speech recordings</p>
              {scoreHistoryData.length > 0 ? (
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={scoreHistoryData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--card-bg)', color: 'var(--text-main)' }} />
                      <Legend wrapperStyle={{ fontSize: '12px', marginTop: '10px' }} />
                      <Line
                        name="Analysis Score"
                        type="monotone"
                        dataKey="score"
                        stroke="#667eea"
                        strokeWidth={3}
                        activeDot={{ r: 8 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="no-data-placeholder">
                  No history data found. Submit a document or speech to view scores.
                </div>
              )}
            </section>

            {/* 2. Pacing (WPM) Line Chart */}
            <section className="chart-container-card">
              <h3>Speaking Pace Trend (WPM)</h3>
              <p className="chart-subtitle">Speaking speed across practice sessions (Target: 120-160 WPM)</p>
              {speechPacingData.length > 0 ? (
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={speechPacingData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <YAxis domain={[40, 200]} stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--card-bg)', color: 'var(--text-main)' }} />
                      <Line
                        name="Pacing (WPM)"
                        type="monotone"
                        dataKey="wpm"
                        stroke="#10b981"
                        strokeWidth={3}
                        activeDot={{ r: 8 }}
                      />
                      {/* Reference boundaries */}
                      <Line
                        name="Optimal Min (120)"
                        type="monotone"
                        dataKey={() => 120}
                        stroke="var(--text-muted)"
                        strokeDasharray="4 4"
                        strokeWidth={1}
                        dot={false}
                      />
                      <Line
                        name="Optimal Max (160)"
                        type="monotone"
                        dataKey={() => 160}
                        stroke="var(--text-muted)"
                        strokeDasharray="4 4"
                        strokeWidth={1}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="no-data-placeholder">
                  No speech history found. Record a speech to view pacing charts.
                </div>
              )}
            </section>

            {/* 3. Latest Document Categories Bar Chart */}
            <section className="chart-container-card">
              <h3>Latest Document Evaluation</h3>
              <p className="chart-subtitle">Score breakdown per analysis category for your most recent document</p>
              {latestDoc ? (
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={categoryScoresData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                      <XAxis dataKey="category" stroke="var(--text-muted)" fontSize={11} tickLine={false} interval={0} />
                      <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--card-bg)', color: 'var(--text-main)' }} />
                      <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                        {categoryScoresData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={entry.score >= 80 ? '#10b981' : entry.score >= 60 ? '#fbbf24' : '#ef4444'}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="no-data-placeholder">
                  No document history found. Upload a document to view category details.
                </div>
              )}
            </section>

            {/* 4. Filler Words count Bar Chart */}
            <section className="chart-container-card">
              <h3>Filler Words Count</h3>
              <p className="chart-subtitle">Occurrences of "um", "ah", "like", etc. per speech session</p>
              {speechPacingData.length > 0 ? (
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={speechPacingData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                      <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--card-bg)', color: 'var(--text-main)' }} />
                      <Bar dataKey="fillerWords" fill="#ef4444" name="Filler Words" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="no-data-placeholder">
                  No speech data found. Record speech audio to view filler word history.
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      {/* TAB 2: SAVED HISTORY LIST */}
      {activeTab === 'history' && (
        <div className="history-tab-content fadeIn">
          <h2>Your Presentation Analysis History</h2>
          <p className="section-desc">Look up previous document rewrites, recorded speech reports, or live sessions to see detailed scores and recommendations.</p>
          
          {historyReports.length > 0 ? (
            <div className="history-table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Topic / Filename</th>
                    <th>Date & Time</th>
                    <th>Score</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {historyReports.map((report) => {
                    const isDoc = report.report_type === 'document_analysis' || report.report_type === 'presentation_analysis' || report.report_type === 'presentation_rewrite';
                    const isLive = report.report_type === 'live_coaching';
                    const score = isDoc 
                      ? report.report_json.overall_score || 75
                      : report.report_json.overall_score || report.report_json.clarity_score || 70;
                      
                    const displayName = report.report_json.presentation_title || report.report_json.document_name || report.report_json.topic || 'Presentation Analysis';

                    const typeBadge = isDoc 
                      ? { label: report.report_type === 'presentation_analysis' ? 'Presentation' : 'Document', class: 'badge-doc' }
                      : isLive 
                        ? { label: 'Live Coach', class: 'badge-live' }
                        : { label: 'Speech Practice', class: 'badge-speech' };

                    return (
                      <tr key={report.id} className="history-row">
                        <td>
                          <span className={`badge-pill ${typeBadge.class}`}>{typeBadge.label}</span>
                        </td>
                        <td className="history-name-cell">
                          <strong>{displayName}</strong>
                        </td>
                        <td className="history-date-cell">
                          {new Date(report.created_at).toLocaleString([], {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </td>
                        <td>
                          <span className={`history-score ${score >= 80 ? 'score-high' : score >= 60 ? 'score-med' : 'score-low'}`}>
                            {score}/100
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button 
                            className="view-summary-btn"
                            onClick={() => setActiveReport(report)}
                          >
                            View Summary
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="no-history-box">
              <div className="placeholder-icon">📋</div>
              <h3>No past history records found</h3>
              <p>Upload slides or complete a speech recording session to start tracking your runs!</p>
            </div>
          )}
        </div>
      )}

      {/* OVERLAY DETAIL MODAL FOR HISTORICAL RUNS */}
      {activeReport && (
        <div className="report-modal-overlay" onClick={() => setActiveReport(null)}>
          <div className="report-modal-content fadeIn" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className={`modal-badge ${activeReport.report_type === 'document_analysis' ? 'badge-doc' : activeReport.report_type === 'live_coaching' ? 'badge-live' : 'badge-speech'}`}>
                {activeReport.report_type === 'document_analysis' ? 'Document Analysis' : activeReport.report_type === 'live_coaching' ? 'Live Practice' : 'Speech Practice'}
              </span>
              <button className="modal-close-btn" onClick={() => setActiveReport(null)}>✕</button>
            </div>
            
            <h2 className="modal-title">{activeReport.report_json.document_name || activeReport.report_json.topic || 'Presentation Session'}</h2>
            <p className="modal-date">Analyzed on: {new Date(activeReport.created_at).toLocaleString()}</p>
            
            <div className="modal-score-section">
              <div className="modal-score-circle">
                <span className="score-num">
                  {activeReport.report_type === 'document_analysis' 
                    ? activeReport.report_json.overall_score 
                    : activeReport.report_json.overall_score || activeReport.report_json.clarity_score || 70}
                </span>
                <span className="score-lbl">Score</span>
              </div>
              <div className="modal-feedback-box">
                <h3>Detailed Feedback Summary</h3>
                <p>
                  {activeReport.report_json.detailed_feedback || 
                   (activeReport.report_json.actionable_feedback && activeReport.report_json.actionable_feedback.join('. ')) || 
                   'Detailed analysis successfully compiled for this practice session. Review category scores and suggestions below.'}
                </p>
              </div>
            </div>
            
            {/* Category breakdown rendering */}
            {activeReport.report_json.category_scores && (
              <div className="modal-scores-grid">
                <h3>Category Score Breakdown</h3>
                <div className="modal-bar-list">
                  {Object.entries(activeReport.report_json.category_scores).map(([cat, val]) => {
                    const numVal = typeof val === 'number' ? val : 0;
                    return (
                      <div key={cat} className="bar-row">
                        <span className="bar-label">{cat.replace(/_/g, ' ')}</span>
                        <div className="bar-bg">
                          <div className="bar-fill" style={{ width: `${numVal}%`, background: numVal >= 80 ? '#10b981' : numVal >= 60 ? '#fbbf24' : '#ef4444' }}></div>
                        </div>
                        <span className="bar-value">{numVal}/100</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            {/* Telemetry data for audio/speech recordings */}
            {(activeReport.report_json.speech_speed_wpm || activeReport.report_json.session_metrics) && (
              <div className="speech-telemetry-box">
                <h3>Speech Delivery Metrics</h3>
                <div className="telemetry-grid">
                  <div className="telemetry-card">
                    <span className="tel-title">Speaking Pace</span>
                    <span className="tel-val">
                      {activeReport.report_json.speech_speed_wpm || activeReport.report_json.session_metrics?.avg_wpm || 0} WPM
                    </span>
                  </div>
                  <div className="telemetry-card">
                    <span className="tel-title">Filler Word Occurrences</span>
                    <span className="tel-val">
                      {activeReport.report_json.filler_words_count !== undefined 
                        ? activeReport.report_json.filler_words_count 
                        : activeReport.report_json.session_metrics?.total_fillers || 0}
                    </span>
                  </div>
                  <div className="telemetry-card">
                    <span className="tel-title">Clarity Metric</span>
                    <span className="tel-val">
                      {activeReport.report_json.clarity_score || activeReport.report_json.overall_score || 70}/100
                    </span>
                  </div>
                  {activeReport.report_json.session_metrics?.avg_eye_contact !== undefined && (
                    <div className="telemetry-card">
                      <span className="tel-title">Eye Contact Accuracy</span>
                      <span className="tel-val">
                        {activeReport.report_json.session_metrics?.avg_eye_contact}%
                      </span>
                    </div>
                  )}
                  {activeReport.report_json.session_metrics?.avg_posture !== undefined && (
                    <div className="telemetry-card">
                      <span className="tel-title">Body Posture Accuracy</span>
                      <span className="tel-val">
                        {activeReport.report_json.session_metrics?.avg_posture}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Recommendations list */}
            {activeReport.report_json.recommendations && activeReport.report_json.recommendations.length > 0 && (
              <div className="modal-recommendations">
                <h3>Key Recommendations</h3>
                <ul className="modal-rec-list">
                  {activeReport.report_json.recommendations.map((rec: string, index: number) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Professional Rewrites */}
            {activeReport.report_json.improved_text && (
              <div className="modal-rewrite">
                <h3>AI Professional Rewrite Suggestion</h3>
                <p className="rewrite-text">{activeReport.report_json.improved_text}</p>
              </div>
            )}
            
            <div style={{ marginTop: '2rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button className="modal-done-btn" onClick={() => setActiveReport(null)}>
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
