/**
 * App Component
 * Main routing configuration using react-router-dom
 * All routes are wrapped inside the Layout component for consistent navigation
 *
 * Key Features:
 * - AuthProvider for global authentication state
 * - Protected routes based on authentication status
 * - Centralized routing configuration
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import DocumentAnalyzer from './pages/DocumentAnalyzer';
import SpeechAnalyzer from './pages/SpeechAnalyzer';
import PracticeMode from './pages/PracticeMode';
import Analytics from './pages/Analytics';
import LiveCoach from './pages/LiveCoach';
import Login from './pages/Login';
import PresentationRewriter from './pages/PresentationRewriter';
import PresentationGenerator from './pages/PresentationGenerator';
import Download from './pages/Download';
import './App.css';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>

          {/* Public Login Route */}
          <Route path="/login" element={<Login />} />

          {/* Protected Routes */}
          <Route element={<Layout />}>

            {/* Default Route */}
            <Route path="/" element={<Navigate to="/analytics" replace />} />

            {/* Document Analyzer */}
            <Route path="/analyzer" element={<DocumentAnalyzer />} />

            {/* Speech Analyzer */}
            <Route path="/speech" element={<SpeechAnalyzer />} />

            {/* Live Coach */}
            <Route path="/live-coach" element={<LiveCoach />} />

            {/* AI Coach */}
            <Route path="/practice" element={<PracticeMode />} />

            {/* Presentation Rewriter */}
            <Route
              path="/presentation-rewriter"
              element={<PresentationRewriter />}
            />

            {/* Presentation Generator */}
            <Route
              path="/presentation-generator"
              element={<PresentationGenerator />}
            />

            {/* Download App */}
            <Route path="/download" element={<Download />} />

            {/* Analytics */}
            <Route path="/analytics" element={<Analytics />} />

          </Route>

        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;