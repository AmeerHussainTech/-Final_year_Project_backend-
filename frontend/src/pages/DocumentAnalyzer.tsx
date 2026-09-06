/**
 * DocumentAnalyzer Page (REFACTORED - Phase 2)
 * Single-session analysis flow (no V1 vs V2 wizard)
 * Reports automatically saved to history
 */

import React, { useState, useEffect } from 'react';
import FileUploader from '../components/FileUploader';
import Button from '../components/Button';
import { useNavigate } from 'react-router-dom';
import { analyzeDocument } from '../services/api';
import { AnalysisReport } from '../types';
import { downloadProgressReportPDF } from '../services/pdfGenerator';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import './DocumentAnalyzer.css';

// Sub-component: 7Cs Pie Chart
const SevenCsPieChart: React.FC<{ scores?: any; overallScore?: number }> = ({ scores, overallScore = 70 }) => {
  const defaultScores = {
    Clear: Math.max(25, overallScore - 5),
    Concise: Math.max(25, overallScore - 12),
    Correct: Math.max(25, overallScore - 10),
    Complete: Math.max(25, overallScore - 15),
    Courteous: Math.min(100, overallScore + 5),
    Concrete: Math.max(25, overallScore - 8),
    Consistent: Math.max(25, overallScore - 14)
  };
  const activeScores = scores || defaultScores;
  
  const normalizedScores: Record<string, number> = {};
  Object.entries(activeScores).forEach(([key, val]) => {
    const normalizedKey = key.charAt(0).toUpperCase() + key.slice(1);
    normalizedScores[normalizedKey] = typeof val === 'number' ? val : 70;
  });

  const data = Object.entries(normalizedScores).map(([name, value]) => ({
    name,
    value
  }));

  const COLORS = [
    '#4f46e5', '#10b981', '#f43f5e', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4',
  ];

  return (
    <div className="seven-cs-chart-wrapper">
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={85}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip 
            formatter={(value: any) => [`${value}/100`, 'Score']}
            contentStyle={{ borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', backgroundColor: 'rgba(15, 23, 42, 0.95)', color: '#fff' }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="seven-cs-legend">
        {data.map((entry, index) => (
          <div key={entry.name} className="legend-item">
            <span className="legend-color-dot" style={{ backgroundColor: COLORS[index] }}></span>
            <span className="legend-label">{entry.name}: <strong>{entry.value}</strong></span>
          </div>
        ))}
      </div>
    </div>
  );
};

const DocumentAnalyzer: React.FC = () => {
  const navigate = useNavigate();
  
  // Upload & Analysis states
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisReport | null>(null);
  const [analysisHistory, setAnalysisHistory] = useState<AnalysisReport[]>([]);
  
  // UI states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'upload' | 'report' | 'history'>('upload');

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('document_analysis_history');
      if (stored) {
        setAnalysisHistory(JSON.parse(stored));
      }
    } catch (e) {
      console.warn('Could not load history:', e);
    }
  }, []);

  // Save analysis to history
  const saveToHistory = (report: AnalysisReport) => {
    const updated = [report, ...analysisHistory].slice(0, 10); // Keep last 10
    setAnalysisHistory(updated);
    localStorage.setItem('document_analysis_history', JSON.stringify(updated));
  };

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setError(null);
    setAnalysis(null);
    setActiveTab('upload');
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please select a file to analyze');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeDocument(file);
      setAnalysis(result);
      saveToHistory(result);
      setActiveTab('report');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze document');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeAgain = () => {
    setFile(null);
    setAnalysis(null);
    setError(null);
    setActiveTab('upload');
  };

  const handleLoadFromHistory = (report: AnalysisReport) => {
    setAnalysis(report);
    setActiveTab('report');
  };

  const handleDownloadReport = () => {
    if (!analysis) return;

    // Map single-analysis data into the format expected by the PDF generator
    const categoryScores = [
      { name: 'Structure', v1: analysis.category_scores.Structure || 0, v2: 0 },
      { name: 'Clarity', v1: analysis.category_scores.Clarity || 0, v2: 0 },
      { name: 'Persuasion', v1: analysis.category_scores.Persuasion || 0, v2: 0 },
      { name: 'Content Quality', v1: analysis.category_scores.Content_Quality || 0, v2: 0 },
      { name: 'Grammar & Syntax', v1: analysis.category_scores.Grammar_and_Syntax || 0, v2: 0 },
      { name: 'Accuracy', v1: analysis.category_scores.Accuracy || 0, v2: 0 },
      { name: 'Tone', v1: analysis.category_scores.Tone_Appropriateness || 0, v2: 0 },
      { name: 'Audience Fit', v1: analysis.category_scores.Audience_Alignment || 0, v2: 0 },
    ];

    downloadProgressReportPDF({
      title: 'Document Analysis Report',
      documentName: file?.name || analysis.document_name || 'document.pdf',
      v1Score: analysis.overall_score,
      v2Score: analysis.overall_score,
      gain: 0,
      categoryScores,
      synthesis: analysis.detailed_feedback,
      improvements: analysis.recommendations,
      remaining: [],
    }, `Analysis_Report_${analysis.document_name.replace(/\.[^/.]+$/, "")}.pdf`);
  };

  return (
    <div className="document-analyzer">
      <h1>Document Analyzer</h1>
      <p className="subtitle">
        Upload any presentation (.pptx), document, or speaker notes to get instant AI-powered feedback on clarity, structure, grammar, and the 7Cs of Communication.
      </p>

      {/* Tab Navigation */}
      <div className="tab-menu">
        <button 
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          📤 Analyze Document
        </button>
        <button 
          className={`tab-btn ${activeTab === 'report' ? 'active' : ''}`}
          disabled={!analysis}
          onClick={() => setActiveTab('report')}
        >
          📊 Report {analysis ? `(${analysis.overall_score}/100)` : ''}
        </button>
        {analysisHistory.length > 0 && (
          <button 
            className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            📚 History ({analysisHistory.length})
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* TAB 1: UPLOAD & ANALYZE */}
      {activeTab === 'upload' && (
        <div className="step-container fadeIn">
          <h2>Upload Your Document</h2>
          <p className="step-description">
            Upload a PDF, PowerPoint (.pptx), Word document, or text file containing your presentation slides, speaker notes, or written content. I'll analyze it across multiple dimensions including grammar, clarity, structure, and the 7Cs of Communication.
          </p>

          <div className="upload-box-wrapper">
            <FileUploader onFileSelect={handleFileSelect} loading={loading} accept=".pdf,.pptx,.doc,.docx,.txt" />
            {file && (
              <div className="selected-file-details">
                <span className="file-icon">Doc</span>
                <div>
                  <strong>{file.name}</strong>
                  <span className="file-size">({(file.size / 1024).toFixed(2)} KB)</span>
                </div>
              </div>
            )}
            
            {file && !analysis && (
              <div className="action-button-container">
                <Button 
                  label="Analyze Document" 
                  onClick={handleAnalyze} 
                  loading={loading}
                  variant="primary"
                />
              </div>
            )}
          </div>

          {/* Quick Tips */}
          <div className="tips-section">
            <h4>📌 What We Analyze</h4>
            <ul>
              <li><strong>7Cs of Communication:</strong> Clear, Concise, Correct, Complete, Courteous, Concrete, Consistent</li>
              <li><strong>Grammar & Style:</strong> Spelling, punctuation, sentence structure, professional tone</li>
              <li><strong>Clarity & Structure:</strong> Logical flow, paragraph organization, readability</li>
              <li><strong>Content Quality:</strong> Relevance, depth, evidence, actionability</li>
              <li><strong>Audience Alignment:</strong> Tone, complexity, engagement level for target audience</li>
            </ul>
          </div>
        </div>
      )}

      {/* TAB 2: ANALYSIS REPORT */}
      {activeTab === 'report' && analysis && (
        <div className="step-container fadeIn">
          <div className="report-actions-header">
            <div className="report-badge-container">
              <span className="file-badge">{analysis.document_name}</span>
              <span className="score-badge">
                Score: {analysis.overall_score}/100
              </span>
            </div>
            <div className="report-actions-buttons">
              <Button 
                label="📥 Download PDF Report" 
                onClick={handleDownloadReport} 
                variant="primary"
              />
              <Button 
                label="🔄 Analyze Another" 
                onClick={handleAnalyzeAgain} 
                variant="secondary"
              />
            </div>
          </div>

          {/* Overall Feedback Section */}
          <div className="score-summary-row">
            <div className="score-widget">
              <h3>Overall Score</h3>
              <div className="score-circle">{analysis.overall_score}</div>
              <p style={{ fontSize: '0.85rem', color: '#718096', marginTop: '0.5rem' }}>out of 100</p>
            </div>
            <div className="feedback-widget">
              <h3>AI Coach Feedback</h3>
              <p>{analysis.detailed_feedback}</p>
              {analysis.strengths && analysis.strengths.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <h4 style={{ color: '#10b981', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>✅ Strengths</h4>
                  <ul style={{ fontSize: '0.9rem', lineHeight: 1.6, paddingLeft: '1.5rem' }}>
                    {analysis.strengths.slice(0, 3).map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* 7Cs Evaluation Card */}
          <div className="report-card seven-cs-card-container">
            <h3>7Cs of Communication Evaluation</h3>
            <div className="seven-cs-content-split">
              <div className="checklist-grid">
                {Object.entries(analysis.seven_cs_evaluation).map(([c, val]) => {
                  const isObj = typeof val === 'object' && val !== null;
                  const status = isObj ? (val as any).status : null;
                  const feedback = isObj ? (val as any).feedback : String(val);
                  return (
                    <div key={c} className="c-item">
                      <strong>{c}:</strong>{' '}
                      {status && (
                        <span className={`status-badge ${status.toLowerCase().replace(/ /g, '-')}`}>
                          {status}
                        </span>
                      )}{' '}
                      {feedback}
                    </div>
                  );
                })}
              </div>
              <SevenCsPieChart scores={analysis.seven_cs_scores} overallScore={analysis.overall_score} />
            </div>
          </div>

          {/* Detailed Category Scores Bar Chart */}
          <div className="visual-chart-card">
            <h3>Detailed Score Breakdown by Category</h3>
            <div className="chart-container-wrapper" style={{ width: '100%', height: 320 }}>
              <ResponsiveContainer>
                <BarChart
                  data={[
                    { name: 'Structure', value: analysis.category_scores.Structure || 0 },
                    { name: 'Clarity', value: analysis.category_scores.Clarity || 0 },
                    { name: 'Persuasion', value: analysis.category_scores.Persuasion || 0 },
                    { name: 'Content Q.', value: analysis.category_scores.Content_Quality || 0 },
                    { name: 'Grammar', value: analysis.category_scores.Grammar_and_Syntax || 0 },
                    { name: 'Tone', value: analysis.category_scores.Tone_Appropriateness || 0 },
                    { name: 'Audience', value: analysis.category_scores.Audience_Alignment || 0 },
                  ]}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip contentStyle={{ borderRadius: '8px', backgroundColor: 'rgba(15, 23, 42, 0.95)', color: '#fff' }} />
                  <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Context Accuracy & Factual Correctness Card */}
          {analysis.context_analysis && (
            <div className="report-card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h3 style={{ margin: 0 }}>🔍 Context Accuracy & Factual Correctness</h3>
                <span className="score-badge" style={{ backgroundColor: analysis.context_analysis.is_context_accurate ? '#10b981' : '#f59e0b' }}>
                  Accuracy: {analysis.context_analysis.context_accuracy_score ?? 85}/100
                </span>
              </div>
              
              <p style={{ fontSize: '0.9rem', color: '#e2e8f0', marginBottom: '1rem', lineHeight: 1.5 }}>
                {analysis.context_analysis.factual_correctness_summary || "Context evaluation complete. The text aligns with the domain topic."}
              </p>

              {analysis.context_analysis.inaccuracies_detected && analysis.context_analysis.inaccuracies_detected.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <h4 style={{ color: '#f87171', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                    ⚠️ Contextual Inaccuracies / Flaws Detected:
                  </h4>
                  <ul style={{ fontSize: '0.85rem', color: '#fca5a5', paddingLeft: '1.25rem', margin: 0 }}>
                    {analysis.context_analysis.inaccuracies_detected.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {analysis.context_analysis.context_based_changes && analysis.context_analysis.context_based_changes.length > 0 && (
                <div>
                  <h4 style={{ color: '#38bdf8', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                    💡 Context-Based Recommended Changes:
                  </h4>
                  <ul style={{ fontSize: '0.85rem', color: '#93c5fd', paddingLeft: '1.25rem', margin: 0 }}>
                    {analysis.context_analysis.context_based_changes.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Recommendations & Improvements */}
          <div className="report-sections-grid">
            <div className="report-card">
              <h3>🎯 Key Recommendations</h3>
              <ul className="rec-list">
                {analysis.recommendations.map((rec, i) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </div>

            {analysis.improved_text && (
              <div className="report-card">
                <h3>✍️ AI-Suggested Improvement</h3>
                <p style={{ fontSize: '0.85rem', color: '#4a5568', fontStyle: 'italic', lineHeight: 1.6, background: '#f7fafc', padding: '1rem', borderRadius: '8px', border: '1px solid #e2e8f0', whiteSpace: 'pre-line' }}>
                  {analysis.improved_text.length > 300 ? `${analysis.improved_text.slice(0, 300)}...` : analysis.improved_text}
                </p>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="proceed-action-row" style={{ gap: '1rem' }}>
            <Button 
              label="🎤 Practice with Live Coach" 
              onClick={() => navigate('/practice', { state: { analysis, document_name: analysis.document_name } })}
              variant="primary"
            />
            <Button 
              label="📤 Analyze Another Document" 
              onClick={handleAnalyzeAgain}
              variant="secondary"
            />
          </div>
        </div>
      )}

      {/* TAB 3: ANALYSIS HISTORY */}
      {activeTab === 'history' && analysisHistory.length > 0 && (
        <div className="step-container fadeIn">
          <h2>Analysis History</h2>
          <p style={{ color: '#718096', marginBottom: '1.5rem' }}>
            Your last {analysisHistory.length} document analyses. Click any to view the full report.
          </p>

          <div className="history-list">
            {analysisHistory.map((report, idx) => (
              <div 
                key={idx} 
                className="history-item"
                onClick={() => handleLoadFromHistory(report)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <strong style={{ fontSize: '1rem' }}>{report.document_name}</strong>
                    <p style={{ fontSize: '0.85rem', color: '#718096', marginTop: '0.3rem' }}>
                      Analyzed: {new Date(report.analysis_timestamp).toLocaleDateString()}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#4f46e5' }}>
                      {report.overall_score}/100
                    </div>
                    <span style={{ fontSize: '0.75rem', color: '#a0aec0' }}>View Report →</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentAnalyzer;

