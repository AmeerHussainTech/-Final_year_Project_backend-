import React from 'react';
import './Download.css';

interface DownloadOption {
  id: string;
  os: string;
  title: string;
  badge: string;
  version: string;
  fileSize: string;
  format: string;
  icon: string;
  downloadUrl: string;
  features: string[];
  instructions?: string;
  primaryColor: string;
}

const downloadOptions: DownloadOption[] = [
  {
    id: 'windows',
    os: 'Windows',
    title: 'Presenova for Windows',
    badge: 'Desktop App',
    version: 'v1.1.0',
    fileSize: '84.5 MB',
    format: '.exe (Installer)',
    icon: '🪟',
    downloadUrl: 'https://fyp-integration-c620f.web.app/downloads/Presenova-Setup-1.1.0.exe',
    features: [
      'Native Windows setup with desktop & start menu shortcuts',
      'Offline Classical ML & RAG vector search processing',
      'System tray quick navigation & automatic status checks',
      'Full MediaPipe webcam & Groq Whisper voice integration'
    ],
    primaryColor: 'from-blue-600 to-cyan-500'
  },
  {
    id: 'mac',
    os: 'macOS',
    title: 'Presenova for Mac',
    badge: 'Desktop App',
    version: 'v1.1.0',
    fileSize: '89.2 MB',
    format: '.dmg (Apple Silicon & Intel)',
    icon: '🍎',
    downloadUrl: 'https://fyp-integration-c620f.web.app/downloads/Presenova-1.1.0.dmg',
    features: [
      'Universal build supporting M1/M2/M3 & Intel Macs',
      'Seamless macOS menu bar & hiddenInset titlebar design',
      'Hardware-accelerated iris tracking & EAR blink detection',
      'Multi-turn AI Coach practice mode with Dr. Vance persona'
    ],
    instructions: 'Note for macOS: Right-click (or Control-click) the downloaded DMG and select "Open" if prompted by Apple Gatekeeper for unsigned developer builds.',
    primaryColor: 'from-purple-600 to-indigo-500'
  },
  {
    id: 'android',
    os: 'Android',
    title: 'Presenova Mobile APK',
    badge: 'Mobile App',
    version: 'v1.1.0',
    fileSize: '41.8 MB',
    format: '.apk (Package)',
    icon: '🤖',
    downloadUrl: 'https://fyp-integration-c620f.web.app/downloads/app-release.apk',
    features: [
      'On-the-go mobile presentation rehearsal & camera tracking',
      'Real-time WebSocket audio streaming & WPM pace monitor',
      'Interactive 7Cs presentation feedback & viva prep',
      'Firebase Authentication & cloud report synchronization'
    ],
    instructions: "Note for Android: Enable 'Install from unknown sources' in your device Security Settings if prompted during APK installation.",
    primaryColor: 'from-emerald-600 to-teal-500'
  }
];

const Download: React.FC = () => {
  return (
    <div className="download-container">
      <div className="download-header text-center max-w-3xl mx-auto mb-12">
        <span className="download-badge inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 mb-4">
          Cross-Platform Availability
        </span>
        <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-4 tracking-tight">
          Download <span className="bg-gradient-to-r from-cyan-400 via-sky-400 to-indigo-400 bg-clip-text text-transparent">Presenova</span>
        </h1>
        <p className="text-slate-300 text-lg">
          Practice presentations anywhere. Choose your platform below to download native desktop installers or mobile packages.
        </p>
      </div>

      <div className="download-grid grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
        {downloadOptions.map((opt) => (
          <div
            key={opt.id}
            className="download-card relative flex flex-col bg-slate-900/90 border border-slate-800 rounded-2xl p-6 hover:border-slate-700 transition-all duration-300 shadow-xl overflow-hidden group"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="text-4xl p-3 bg-slate-800/80 rounded-xl border border-slate-700">
                {opt.icon}
              </div>
              <div className="text-right">
                <span className="text-xs font-medium text-slate-400 block">{opt.format}</span>
                <span className="text-sm font-bold text-slate-200">{opt.fileSize}</span>
              </div>
            </div>

            <h3 className="text-2xl font-bold text-white mb-2">{opt.title}</h3>
            <div className="flex items-center gap-2 mb-6">
              <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-800 text-cyan-400 border border-slate-700">
                {opt.version}
              </span>
              <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                {opt.badge}
              </span>
            </div>

            <div className="flex-1 mb-6">
              <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold mb-3">Key Capabilities</h4>
              <ul className="space-y-2.5">
                {opt.features.map((feat, idx) => (
                  <li key={idx} className="flex items-start text-sm text-slate-300">
                    <svg className="w-4 h-4 text-cyan-400 mr-2 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                    </svg>
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            {opt.instructions && (
              <div className="mb-6 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300/90 leading-relaxed">
                💡 {opt.instructions}
              </div>
            )}

            <a
              href={opt.downloadUrl}
              download
              className={`download-btn w-full py-3.5 px-6 rounded-xl font-bold text-white text-center transition-all duration-200 bg-gradient-to-r ${opt.primaryColor} hover:opacity-95 shadow-lg flex items-center justify-center gap-2`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Download for {opt.os}</span>
            </a>
          </div>
        ))}
      </div>

      <div className="download-footer mt-16 text-center text-sm text-slate-400 max-w-2xl mx-auto border-t border-slate-800/80 pt-8">
        <p className="mb-2">
          Looking to run the web application directly in your browser without installing?
        </p>
        <a href="/analytics" className="text-cyan-400 font-semibold hover:underline">
          Launch Web Dashboard &rarr;
        </a>
      </div>
    </div>
  );
};

export default Download;
