/**
 * SpeechAnalyzer Page (Phase 3 Presentation Coach)
 * Real-time speech recording and analysis using MediaRecorder API and backend Whisper/Gemini integration.
 * Standardized 3-step revision comparison wizard (V1 -> V2 -> Progress Report).
 *
 * NOTE: V2 comparison flow is temporarily commented out.
 * Search "COMPARISON_DISABLED" to re-enable all sections at once.
 */

import React, { useState, useEffect, useRef } from 'react';
import Button from '../components/Button';
import { analyzeAudio, analyzeSpeech } from '../services/api';
// compareDocuments removed - no longer used
import { SpeechMetrics } from '../types';
// ComparisonReport removed - no longer used
import { downloadProgressReportPDF } from '../services/pdfGenerator';
// COMPARISON_DISABLED: import ReactDiffViewer from 'react-diff-viewer-continued';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import './SpeechAnalyzer.css';

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
    '#4f46e5',
    '#10b981',
    '#f43f5e',
    '#f59e0b',
    '#8b5cf6',
    '#ec4899',
    '#06b6d4',
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

const SpeechAnalyzer: React.FC = () => {

  // ===== WIZARD STATE =====
  const [_step, _setStep] = useState(1);

  /* COMPARISON_DISABLED — uncomment to re-enable tab switching in step 3
  const [activeReportTab, setActiveReportTab] = useState<'comparison' | 'v1' | 'v2'>('comparison');
  */

  /* COMPARISON_DISABLED — uncomment to re-enable practice with coach navigation
  const handlePracticeWithCoach = () => {
    if (!v2Analysis) return;
    navigate('/practice', {
      state: {
        phase: 'speech',
        analysis: v2Analysis,
        session_id: 'speech-' + Date.now(),
        v1Analysis: v1Analysis,
        v2Analysis: v2Analysis,
        v1Text: v1Transcript,
        v2Text: v2Transcript,
        comparison: comparison
      }
    });
  };
  */

  // Version 1 State
  const [v1Transcript, setV1Transcript] = useState('');
  const [v1Duration, setV1Duration] = useState(0);
  const [v1Analysis, setV1Analysis] = useState<SpeechMetrics | null>(null);

  /* COMPARISON_DISABLED — uncomment to re-enable Version 2 states
  const [v2Transcript, setV2Transcript] = useState('');
  const [v2Duration, setV2Duration] = useState(0);
  const [v2Analysis, setV2Analysis] = useState<SpeechMetrics | null>(null);
  */

  /* COMPARISON_DISABLED — uncomment to re-enable comparison state
  const [comparison, setComparison] = useState<any | null>(null);
  */

  // Common UI / Temp Recording State
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRecordedAudio, setHasRecordedAudio] = useState(false);

  // ===== REFS FOR AUDIO RECORDING =====
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerIntervalRef = useRef<any | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // ===== CLEANUP ON COMPONENT UNMOUNT =====
  useEffect(() => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError('Web Audio Recording is not supported in this browser. Please use Chrome, Firefox, or Edge.');
    }
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // ===== TIMER EFFECT =====
  useEffect(() => {
    if (isRecording) {
      timerIntervalRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    }
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [isRecording]);

  // ===== START/STOP RECORDING =====
  const handleToggleRecording = async () => {
    setError(null);
    if (isRecording) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    } else {
      setError(null);
      setDuration(0);
      audioChunksRef.current = [];
      setHasRecordedAudio(false);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
          setHasRecordedAudio(audioChunksRef.current.length > 0);
        };
        mediaRecorder.onstop = () => {
          if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
          }
        };
        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error('Microphone error:', err);
        setError('Microphone access denied or unavailable. Please connect a microphone and check permissions.');
      }
    }
  };

  // ===== ANALYZE SPEECH =====
  const handleAnalyze = async () => {
    if (audioChunksRef.current.length === 0) {
      setError('Please record some speech audio first');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
      const fileExt = mimeType.includes('webm') ? 'webm'
      : mimeType.includes('ogg') ? 'ogg'
      : mimeType.includes('mp4') ? 'm4a'
      : 'wav';
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
      const audioFile = new File([audioBlob], `speech.${fileExt}`, { type: mimeType });
      const result = await analyzeAudio(audioFile, duration);
      // Always set V1 (comparison disabled)
      setV1Analysis(result);
      setV1Transcript(result.transcript || '');
      setV1Duration(duration);

      /* COMPARISON_DISABLED — uncomment else block to re-enable V2 analysis
      } else {
        setV2Analysis(result);
        setV2Transcript(result.transcript || '');
        setV2Duration(duration);
      }
      */

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze speech audio');
    } finally {
      setLoading(false);
    }
  };

  /* COMPARISON_DISABLED — uncomment to re-enable comparison generation
  const handleCompare = async () => {
    if (!v1Analysis || !v2Analysis) {
      setError('Both versions must be analyzed before comparison');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const v1Score = v1Analysis.overall_score !== undefined ? v1Analysis.overall_score : v1Analysis.clarity_score;
      const v2Score = v2Analysis.overall_score !== undefined ? v2Analysis.overall_score : v2Analysis.clarity_score;
      const localResult = {
        score_difference: v2Score - v1Score,
        key_improvements: [
          `Speech pacing improved from ${v1Analysis.speech_speed_wpm} WPM to ${v2Analysis.speech_speed_wpm} WPM`,
          `Filler words reduced from ${v1Analysis.filler_words_count} to ${v2Analysis.filler_words_count}`,
          `Overall score increased by ${v2Score - v1Score} points`,
        ],
        remaining_issues: ['Continue practicing to reduce filler words', 'Work on speech pacing consistency'],
        synthesis_summary: `Your speech improved from ${v1Score}/100 to ${v2Score}/100.`,
      };
      setComparison(localResult);
      setStep(3);
      setActiveReportTab('comparison');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate comparison report');
    } finally {
      setLoading(false);
    }
  };
  */

  // ===== CLEAR =====
  const handleClear = () => {
    if (isRecording && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setDuration(0);
    setError(null);
    setIsRecording(false);
    setHasRecordedAudio(false);
    audioChunksRef.current = [];

    // Always clear V1 (comparison disabled)
    setV1Transcript('');
    setV1Duration(0);
    setV1Analysis(null);

    /* COMPARISON_DISABLED — uncomment to re-enable step-based clearing
    } else if (step === 2) {
      setV2Transcript('');
      setV2Duration(0);
      setV2Analysis(null);
    }
    */
  };

  // ===== RESET ALL STATE =====
  const handleReset = () => {
    handleClear();
    setV1Transcript('');
    setV1Duration(0);
    setV1Analysis(null);
    setHasRecordedAudio(false);

    /* COMPARISON_DISABLED — uncomment to re-enable full reset
    setV2Transcript('');
    setV2Duration(0);
    setV2Analysis(null);
    setComparison(null);
    */

    _setStep(1);
  };

  const handleUseDemoSpeech = async () => {
    setLoading(true);
    setError(null);
    try {
      const demoV1Text = "Hello everyone, today I want to talk about, you know, blockchain technology. Basically, blockchain is like a distributed ledger, and actually, it is very secure. Um, we can use it for smart contracts, and kind of, you know, supply chain tracking. But the main problem is scalability. Um, we need to find, you know, better consensus mechanisms. So, basically, that is my presentation. Any questions?";

      /* COMPARISON_DISABLED — uncomment to re-enable V2 demo text
      const demoV2Text = "Good morning, everyone. Today, we will explore blockchain technology and its security benefits. Blockchain acts as a decentralized ledger, ensuring data integrity and tamper-proof records. While smart contracts and supply chain tracking are highly viable applications, scalability remains a critical challenge. To resolve this, we must develop more efficient consensus mechanisms. Thank you for your time, and I welcome any questions.";
      const textToAnalyze = step === 1 ? demoV1Text : demoV2Text;
      const durationSecs = step === 1 ? 30 : 25;
      */

      // Always use V1 demo (comparison disabled)
      const textToAnalyze = demoV1Text;
      const durationSecs = 30;

      const result = await analyzeSpeech(textToAnalyze, durationSecs);
      setV1Analysis(result);
      setV1Transcript(result.transcript || demoV1Text);
      setV1Duration(durationSecs);

      /* COMPARISON_DISABLED — uncomment to re-enable step-based demo result setting
      } else {
        setV2Analysis(result);
        setV2Transcript(result.transcript || demoV2Text);
        setV2Duration(durationSecs);
      }
      */

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze demo speech');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = () => {
    if (!v1Analysis) return;
    const v1Score = v1Analysis.overall_score !== undefined ? v1Analysis.overall_score : v1Analysis.clarity_score;

    const categoryScores = [
      { name: 'Structure', v1: v1Analysis.category_scores?.Structure || 0, v2: v1Analysis.category_scores?.Structure || 0 },
      { name: 'Clarity', v1: v1Analysis.category_scores?.Clarity || 0, v2: v1Analysis.category_scores?.Clarity || 0 },
      { name: 'Persuasion', v1: v1Analysis.category_scores?.Persuasion || 0, v2: v1Analysis.category_scores?.Persuasion || 0 },
      { name: 'Content Quality', v1: v1Analysis.category_scores?.Content_Quality || 0, v2: v1Analysis.category_scores?.Content_Quality || 0 },
      { name: 'Call to Action', v1: v1Analysis.category_scores?.Call_to_Action || 0, v2: v1Analysis.category_scores?.Call_to_Action || 0 },
    ];

    downloadProgressReportPDF({
      title: 'Speech Analysis Report',
      documentName: 'Speech Practice Session',
      v1Score,
      v2Score: v1Score,
      gain: 0,
      categoryScores,
      synthesis: v1Analysis.detailed_feedback || 'Your speech analysis is complete.',
      improvements: v1Analysis.recommendations || [],
      remaining: v1Analysis.actionable_feedback || [],

      /* COMPARISON_DISABLED — uncomment to re-enable comparison data in report
      v2Score: v2Score,
      gain: v2Score - v1Score,
      synthesis: comparison?.synthesis_summary || 'Speech revised and compared successfully.',
      improvements: comparison?.key_improvements || [],
      remaining: comparison?.remaining_issues || [],
      additionalMetrics: [
        { label: 'Word Count', v1: `${v1Analysis.word_count} words`, v2: `${v2Analysis.word_count} words`, change: '' },
        { label: 'Speaking Pace (WPM)', v1: `${v1Analysis.speech_speed_wpm} WPM`, v2: `${v2Analysis.speech_speed_wpm} WPM`, change: '' },
        { label: 'Filler Words Count', v1: `${v1Analysis.filler_words_count}`, v2: `${v2Analysis.filler_words_count}`, change: '' },
        { label: 'Word Repetitions', v1: `${v1Analysis.repetition_count || 0}`, v2: `${v2Analysis.repetition_count || 0}`, change: '' },
      ],
      */

    }, 'Speech_Analysis_Report.pdf');
  };

  /* COMPARISON_DISABLED — uncomment to re-enable V1/V2 chart data
  const getChartData = () => {
    if (!v1Analysis || !v2Analysis) return [];
    const keys = ['Structure', 'Clarity', 'Persuasion', 'Content_Quality', 'Call_to_Action'] as const;
    return keys.map(key => ({
      name: key.replace(/_/g, ' '),
      'Version 1': v1Analysis.category_scores?.[key] || 0,
      'Version 2': v2Analysis.category_scores?.[key] || 0,
    }));
  };
  */

  // ===== FORMAT DURATION TO MM:SS =====
  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // ===== RENDER SINGLE REPORT (unchanged) =====
  const renderSingleReport = (report: SpeechMetrics, elapsedSecs: number) => {
    return (
      <div className="report-container fadeIn">
        <div className="score-summary-row">
          <div className="score-widget">
            <h3>Overall Score</h3>
            <div className="score-circle">
              {report.overall_score !== undefined ? report.overall_score : report.clarity_score}
            </div>
          </div>
          <div className="feedback-widget">
            <h3>Speech Coach Summary</h3>
            <p>
              {report.detailed_feedback || 
               `Your speech analysis is complete. You spoke a total of ${report.word_count} words over ${report.duration_seconds || elapsedSecs} seconds, achieving an average pacing rate of ${report.speech_speed_wpm} WPM. Clarity was evaluated at ${report.clarity_score}/100 based on filler word density and repetition rates.`}
            </p>
          </div>
        </div>

        {report.category_scores && (
          <div className="category-scores-section mt-4">
            <h3>Pacing & Quality Categories</h3>
            <div className="category-scores-grid">
              {Object.entries(report.category_scores).map(([cat, score]) => (
                <div key={cat} className="category-score-card">
                  <div className="category-score-header">
                    <span className="category-score-name">{cat.replace('_', ' ')}</span>
                    <span className="category-score-num">{score}/100</span>
                  </div>
                  <div className="category-score-bar">
                    <div className="category-score-fill" style={{ width: `${score}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="metrics-section mt-4">
          <h3>Speaking Delivery Metrics</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-icon">Stats</div>
              <div className="metric-label">Word Count</div>
              <div className="metric-value">{report.word_count}</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">Pace</div>
              <div className="metric-label">Pacing Speed (WPM)</div>
              <div className="metric-value">{report.speech_speed_wpm}</div>
              <div className="metric-subtext">
                {report.speech_speed_wpm > 160 ? 'Speaking Fast' : report.speech_speed_wpm < 100 ? 'Speaking Slow' : 'Optimal Pace (120-160 WPM)'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">Fillers</div>
              <div className="metric-label">Filler Words</div>
              <div className="metric-value">{report.filler_words_count}</div>
              <div className="metric-subtext">{report.filler_words_percentage?.toFixed(1)}% of total speech</div>
            </div>
            <div className="metric-card">
              <div className="metric-icon">Repeats</div>
              <div className="metric-label">Word Repetitions</div>
              <div className="metric-value">{report.repetition_count || 0}</div>
              <div className="metric-subtext">Consecutive repeated words</div>
            </div>
          </div>
        </div>

        {report.seven_cs_evaluation && (
          <div className="report-card seven-cs-card-container mt-4">
            <h3>7Cs Speech Evaluation</h3>
            <div className="seven-cs-content-split">
              <div className="checklist-grid">
                {Object.entries(report.seven_cs_evaluation).map(([cs, val]) => {
                  const isObj = typeof val === 'object' && val !== null;
                  const status = isObj ? (val as any).status : null;
                  const feedback = isObj ? (val as any).feedback : String(val);
                  return (
                    <div key={cs} className="c-item">
                      <strong>{cs}:</strong>{' '}
                      {status && <span className={`status-badge ${status.toLowerCase().replace(/ /g, '-')}`}>{status}</span>}{' '}
                      {feedback}
                    </div>
                  );
                })}
              </div>
              <SevenCsPieChart scores={report.seven_cs_scores} overallScore={report.overall_score || report.clarity_score} />
            </div>
          </div>
        )}

        <div className="report-sections-grid mt-4">
          {report.strengths && report.strengths.length > 0 && (
            <div className="strengths-list-section">
              <h4 className="strengths-list-title">Key Strengths Identified</h4>
              <ul className="strengths-list">
                {report.strengths.map((str, idx) => <li key={idx}>{str}</li>)}
              </ul>
            </div>
          )}
          <div className="report-card">
            <h3>Actionable Improvement Tips</h3>
            {report.recommendations && report.recommendations.length > 0 ? (
              <ul className="rec-list">
                {report.recommendations.map((rec, index) => <li key={index}>{rec}</li>)}
              </ul>
            ) : report.actionable_feedback && report.actionable_feedback.length > 0 ? (
              <ul className="rec-list">
                {report.actionable_feedback.map((feedback, index) => <li key={index}>{feedback}</li>)}
              </ul>
            ) : (
              <p className="no-feedback">Excellent speech delivery! No pacing or filler word improvements recommended.</p>
            )}
          </div>
        </div>

        {report.improved_text && (
          <div className="rewrite-section mt-4">
            <h3>AI Cleaned Transcript (Rewrite Suggestion)</h3>
            <p className="subtitle" style={{ fontSize: '0.85rem', marginBottom: '0.8rem', textAlign: 'left' }}>
              Here is a polished, grammatically correct version of your speech transcript with filler words and repetitions removed:
            </p>
            <div className="rewrite-text-display">{report.improved_text}</div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="speech-analyzer">
      <h1>Presentation Coach</h1>
      <p className="subtitle">
        Record your speech to get instant AI feedback with 7 C's scoring, delivery metrics, and improvement suggestions.
      </p>

      {/* COMPARISON_DISABLED — uncomment to re-enable 3-step wizard
      <div className="step-wizard-indicator">
        <button
          className={`step-tab ${step === 1 ? 'active' : ''} ${v1Analysis ? 'completed' : ''}`}
          onClick={() => setStep(1)}
        >
          <span className="step-num">1</span>
          <span className="step-label">V1: Initial Speech</span>
        </button>
        <div className="step-line"></div>
        <button
          className={`step-tab ${step === 2 ? 'active' : ''} ${v2Analysis ? 'completed' : ''}`}
          disabled={!v1Analysis}
          onClick={() => setStep(2)}
        >
          <span className="step-num">2</span>
          <span className="step-label">V2: Improved Version</span>
        </button>
        <div className="step-line"></div>
        <button
          className={`step-tab ${step === 3 ? 'active' : ''}`}
          disabled={!v1Analysis || !v2Analysis}
          onClick={() => { if (comparison) { setStep(3); } else { handleCompare(); } }}
        >
          <span className="step-num">3</span>
          <span className="step-label">Progress Report</span>
        </button>
      </div>
      */}

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* ===== STEP 1 — RECORD & ANALYZE ===== */}
      <div className="step-container fadeIn">
        <h2>Record Your Speech</h2>
        <p className="step-description">Click Start Recording to begin. We will analyze your pacing, clarity, and 7 C's score.</p>

        <section className="recording-section">
          <div className={`recording-indicator ${isRecording ? 'active' : ''}`}>
            {isRecording && <div className="recording-pulse"></div>}
            <span>{isRecording ? 'Recording...' : 'Ready to Record'}</span>
          </div>

          <div className="duration-display">
            <span className="duration-label">Duration:</span>
            <span className="duration-value">{formatDuration(isRecording ? duration : v1Duration)}</span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap' }}>
            <Button
              label={isRecording ? 'Stop Recording' : 'Start Recording'}
              onClick={handleToggleRecording}
              disabled={loading}
            />
            {hasRecordedAudio && !isRecording && (
              <>
                <Button label="Analyze Speech" onClick={handleAnalyze} loading={loading} />
                <Button label="Clear" onClick={handleClear} variant="secondary" disabled={loading} />
              </>
            )}
            {!isRecording && !hasRecordedAudio && (
              <Button label="Load Demo Speech" onClick={handleUseDemoSpeech} variant="secondary" disabled={loading} />
            )}
          </div>
        </section>

        {v1Transcript && !v1Analysis && (
          <section className="transcript-section mt-4">
            <label className="transcript-label">Current Speech Transcript</label>
            <div className="transcript-display">
              <p className="transcript-text">{v1Transcript}</p>
            </div>
          </section>
        )}

        {v1Analysis && (
          <>
            {/* Download button */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', margin: '1rem 0' }}>
              <Button label="Download Report" onClick={handleDownloadReport} variant="primary" />
            </div>

            {renderSingleReport(v1Analysis, v1Duration)}

            {/* COMPARISON_DISABLED — uncomment to re-enable "Proceed to V2" button
            <div className="proceed-action-row mt-4" style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
              <Button
                label="Proceed to Step 2: Record Revised Speech"
                onClick={() => { setStep(2); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
              />
            </div>
            */}

            <div className="proceed-action-row mt-4" style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
              <Button label="Analyze New Speech" onClick={handleReset} variant="secondary" />
            </div>
          </>
        )}
      </div>

      {/* COMPARISON_DISABLED — entire Step 2 block. Uncomment to re-enable V2 recording.
      {step === 2 && (
        <div className="step-container fadeIn">
          <h2>Step 2: Record Your Revised Speech (Version 2)</h2>
          <p className="step-description">Practice speaking again. Try to avoid filler words, keep an even pace, and address Version 1 feedback.</p>
          {v1Analysis && (
            <div className="baseline-banner" style={{ display: 'flex', justifyContent: 'space-between', padding: '1rem 1.5rem', backgroundColor: '#fffaf0', borderLeft: '5px solid #dd6b20', borderRadius: '6px', color: '#c05621', fontWeight: 500 }}>
              <span><strong>V1 Score Baseline:</strong> {v1Analysis.overall_score !== undefined ? v1Analysis.overall_score : v1Analysis.clarity_score}/100</span>
              <span>Pacing Rate: {v1Analysis.speech_speed_wpm} WPM</span>
              <span>Fillers Detected: {v1Analysis.filler_words_count}</span>
            </div>
          )}
          <section className="recording-section mt-4">
            <div className={`recording-indicator ${isRecording ? 'active' : ''}`}>
              {isRecording && <div className="recording-pulse"></div>}
              <span>{isRecording ? 'Recording V2 Speech...' : 'Ready to Record V2'}</span>
            </div>
            <div className="duration-display">
              <span className="duration-label">Revised Duration:</span>
              <span className="duration-value">{formatDuration(isRecording ? duration : v2Duration)}</span>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap' }}>
              <Button label={isRecording ? 'Stop V2 Recording' : 'Start V2 Recording'} onClick={handleToggleRecording} disabled={loading} />
              {audioChunksRef.current.length > 0 && !isRecording && (
                <>
                  <Button label="Analyze V2 Speech" onClick={handleAnalyze} loading={loading} />
                  <Button label="Clear" onClick={handleClear} variant="secondary" disabled={loading} />
                </>
              )}
              {!isRecording && audioChunksRef.current.length === 0 && (
                <Button label="Load Demo Speech" onClick={handleUseDemoSpeech} variant="secondary" disabled={loading} />
              )}
            </div>
          </section>
          {v2Transcript && !v2Analysis && (
            <section className="transcript-section mt-4">
              <label className="transcript-label">V2 Speech Transcript</label>
              <div className="transcript-display"><p className="transcript-text">{v2Transcript}</p></div>
            </section>
          )}
          {v2Analysis && (
            <>
              {renderSingleReport(v2Analysis, v2Duration)}
              <div className="proceed-action-row mt-4" style={{ display: 'flex', justifyContent: 'center', margin: '2rem 0' }}>
                <Button label="Proceed to Step 3: Compare Versions" onClick={handleCompare} />
              </div>
            </>
          )}
        </div>
      )}
      */}

      {/* COMPARISON_DISABLED — entire Step 3 block. Uncomment to re-enable comparison view.
      {step === 3 && v1Analysis && v2Analysis && (
        <div className="step-container fadeIn">
          ... (full step 3 JSX was here — restore from git history or original file)
        </div>
      )}
      */}

    </div>
  );
};

export default SpeechAnalyzer;