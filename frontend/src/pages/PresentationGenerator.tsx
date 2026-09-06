import React, { useState } from 'react';
import {
  generatePresentation,
  getGeneratorDownloadUrl,
  PresentationGenResponse,
  SlideOutline
} from '../services/presentationGeneratorApi';
import './PresentationGenerator.css';

const SLIDE_COUNTS = [5, 8, 10, 12];
const TONES = [
  { id: 'Professional', label: '🎯 Professional' },
  { id: 'Educational', label: '🎓 Educational' },
  { id: 'Persuasive', label: '🚀 Persuasive' },
  { id: 'Inspirational', label: '💡 Inspirational' }
];

const THEMES = [
  { id: 'modern_dark', name: 'Modern Dark', color: '#38bdf8', bg: '#0f172a', desc: 'Sleek Navy & Sky Blue' },
  { id: 'corporate_clean', name: 'Corporate Clean', color: '#0284c7', bg: '#ffffff', desc: 'Minimalist Slate & Teal' },
  { id: 'creative_neon', name: 'Creative Neon', color: '#f43f5e', bg: '#18181b', desc: 'Vibrant Rose & Charcoal' },
  { id: 'academic_elegant', name: 'Academic Gold', color: '#f59e0b', bg: '#1e293b', desc: 'Elegant Gold & Dark Navy' }
];

const PresentationGenerator: React.FC = () => {
  const [topic, setTopic] = useState('');
  const [slideCount, setSlideCount] = useState(5);
  const [tone, setTone] = useState('Professional');
  const [theme, setTheme] = useState('modern_dark');
  const [audience, setAudience] = useState('General Audience');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PresentationGenResponse | null>(null);
  const [expandedSlide, setExpandedSlide] = useState<number | null>(1);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setError('Please enter a presentation topic or prompt.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await generatePresentation({
        topic: topic.trim(),
        slide_count: slideCount,
        tone,
        theme,
        target_audience: audience.trim() || 'General Audience'
      });

      setResult(response);
    } catch (err: any) {
      setError(err.message || 'An error occurred while generating presentation.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setResult(null);
    setError(null);
    setTopic('');
  };

  return (
    <div className="pg-page">
      <div className="pg-hero">
        <div className="pg-hero-badge">✨ AI Complete Generator</div>
        <h1 className="pg-hero-title">AI Presentation Creator</h1>
        <p className="pg-hero-subtitle">
          Transform any topic into a complete, professionally designed PowerPoint (.pptx) presentation 
          in seconds — with AI-crafted slide titles, structured content, speaker notes, and custom themes!
        </p>
      </div>

      <div className="pg-container">
        {/* LEFT COLUMN: CONTROL FORM */}
        <div className="pg-card pg-form-card">
          <h2 className="pg-card-title">📝 Presentation Options</h2>
          
          <form onSubmit={handleGenerate} className="pg-form">
            {/* Topic Input */}
            <div className="pg-field">
              <label className="pg-label">Topic or Prompt <span className="req">*</span></label>
              <textarea
                className="pg-textarea"
                rows={3}
                placeholder="e.g. Artificial Intelligence in Modern Healthcare, Renewable Energy Future, or Startup Pitch Deck"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={loading}
              />
            </div>

            {/* Slide Count Selection */}
            <div className="pg-field">
              <label className="pg-label">Number of Slides</label>
              <div className="pg-count-group">
                {SLIDE_COUNTS.map((count) => (
                  <button
                    key={count}
                    type="button"
                    className={`pg-count-btn ${slideCount === count ? 'active' : ''}`}
                    onClick={() => setSlideCount(count)}
                    disabled={loading}
                  >
                    {count} Slides
                  </button>
                ))}
              </div>
            </div>

            {/* Theme Selector */}
            <div className="pg-field">
              <label className="pg-label">Visual Theme</label>
              <div className="pg-theme-grid">
                {THEMES.map((t) => (
                  <div
                    key={t.id}
                    className={`pg-theme-card ${theme === t.id ? 'active' : ''}`}
                    onClick={() => !loading && setTheme(t.id)}
                    style={{ borderColor: theme === t.id ? t.color : 'transparent' }}
                  >
                    <div className="pg-theme-swatch" style={{ background: t.bg, border: `2px solid ${t.color}` }}>
                      <span style={{ color: t.color }}>Aa</span>
                    </div>
                    <div className="pg-theme-info">
                      <span className="pg-theme-name">{t.name}</span>
                      <span className="pg-theme-desc">{t.desc}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Tone & Audience */}
            <div className="pg-row">
              <div className="pg-field pg-col">
                <label className="pg-label">Writing Tone</label>
                <select
                  className="pg-select"
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  disabled={loading}
                >
                  {TONES.map((t) => (
                    <option key={t.id} value={t.id}>{t.label}</option>
                  ))}
                </select>
              </div>

              <div className="pg-field pg-col">
                <label className="pg-label">Target Audience</label>
                <input
                  type="text"
                  className="pg-input"
                  placeholder="e.g. Executives, Students"
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            {/* 7 Cs Communication Standards Banner */}
            <div className="pg-field pg-seven-cs-card">
              <div className="pg-seven-cs-header">
                <span className="pg-seven-cs-icon">🛡️</span>
                <div>
                  <span className="pg-seven-cs-title">7 Cs Communication & Analysis Rules Applied</span>
                  <span className="pg-seven-cs-subtitle">Clarity · Conciseness · Completeness · Concreteness · Consideration · Correctness · Courtesy</span>
                </div>
              </div>
              <div className="pg-seven-cs-pills">
                <span className="pg-7c-tag">⚡ Max 15 Words/Bullet</span>
                <span className="pg-7c-tag">🎯 Audience Tailored</span>
                <span className="pg-7c-tag">✍️ Grammar & Correctness</span>
                <span className="pg-7c-tag">💡 Key Takeaways</span>
                <span className="pg-7c-tag">🎙️ Speaker Script</span>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="pg-btn pg-btn-primary"
              disabled={loading || !topic.trim()}
            >
              {loading ? (
                <>
                  <span className="pg-spinner" /> Evaluating 7 Cs & Building PPTX…
                </>
              ) : (
                <>✨ Generate Complete Presentation (7 Cs Verified)</>
              )}
            </button>
          </form>

          {error && (
            <div className="pg-error">
              <span>⚠️</span> <span>{error}</span>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: GENERATION RESULT & SLIDE PREVIEW */}
        <div className="pg-card pg-result-card">
          {result ? (
            <div className="pg-success-box">
              <div className="pg-success-header">
                <span className="pg-success-icon">🎉</span>
                <div>
                  <h3 className="pg-success-title">Presentation Generated Successfully!</h3>
                  <p className="pg-success-meta">
                    {result.slides_generated} slides created · Theme: {result.theme.replace('_', ' ')}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="pg-actions">
                <a
                  className="pg-btn pg-btn-download"
                  href={getGeneratorDownloadUrl(result.output_filename)}
                  target="_blank"
                  rel="noreferrer"
                  download
                >
                  ⬇️ Download PPTX Presentation
                </a>
                <button className="pg-btn pg-btn-secondary" onClick={reset}>
                  🔄 Create Another Presentation
                </button>
              </div>

              {/* Slide Outline Preview */}
              <div className="pg-outline-header">
                <h3>📋 Generated Slide Outline ({result.outline.slides.length} Slides)</h3>
                <p>Click any slide to inspect its generated content and speaker notes</p>
              </div>

              <div className="pg-slides-list">
                {result.outline.slides.map((slide: SlideOutline) => {
                  const isExpanded = expandedSlide === slide.slide_number;
                  return (
                    <div
                      key={slide.slide_number}
                      className={`pg-slide-card ${slide.type === 'title' ? 'is-title-slide' : ''} ${isExpanded ? 'open' : ''}`}
                    >
                      <div
                        className="pg-slide-header"
                        onClick={() => setExpandedSlide(isExpanded ? null : slide.slide_number)}
                      >
                        <div className="pg-slide-title-wrap">
                          <span className="pg-slide-num">Slide {slide.slide_number}</span>
                          <span className="pg-slide-title-text">{slide.title}</span>
                        </div>
                        <span className="pg-slide-badge">{slide.type === 'title' ? '📌 Title Slide' : '📄 Content'}</span>
                      </div>

                      {isExpanded && (
                        <div className="pg-slide-body">
                          {slide.subtitle && (
                            <p className="pg-slide-subtitle"><strong>Subtitle:</strong> {slide.subtitle}</p>
                          )}
                          {slide.key_takeaway && (
                            <div className="pg-slide-takeaway">💡 <strong>Takeaway:</strong> {slide.key_takeaway}</div>
                          )}

                          {slide.cards && slide.cards.length > 0 && (
                            <div className="pg-slide-cards-grid">
                              {slide.cards.map((c, ci) => (
                                <div key={ci} className="pg-slide-preview-card">
                                  <div className="pg-preview-card-title">{c.title}</div>
                                  <div className="pg-preview-card-desc">{c.description}</div>
                                </div>
                              ))}
                            </div>
                          )}

                          {(!slide.cards || slide.cards.length === 0) && slide.bullets && slide.bullets.length > 0 && (
                            <ul className="pg-slide-bullets">
                              {slide.bullets.map((bullet, bi) => (
                                <li key={bi}>{bullet}</li>
                              ))}
                            </ul>
                          )}

                          {slide.speaker_notes && (
                            <div className="pg-slide-notes">
                              <span>🎙️ <strong>Speaker Notes:</strong></span>
                              <p>{slide.speaker_notes}</p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="pg-placeholder">
              <div className="pg-placeholder-icon">🎨</div>
              <h3>AI PowerPoint Deck Builder</h3>
              <p>Enter your presentation topic on the left and select your preferred slides count, theme, and tone.</p>
              <div className="pg-placeholder-features">
                {['Automatic Topic Structure', 'Gemini AI Content Engine', 'Programmatic PPTX Builder', 'Formatted Bullet Points', 'Custom Color Themes', 'Speaker Notes Included'].map((f) => (
                  <div key={f} className="pg-placeholder-pill">
                    <span className="pg-dot" /> <span>{f}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PresentationGenerator;
