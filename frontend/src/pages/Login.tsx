/**
 * Login Page (Phase 1 / Firebase Identity Provider Integration)
 * Unified Firebase Authentication (Email/Password + Google Sign-In)
 *
 * Flow:
 * 1. User signs in with Google or Email/Password via Firebase SDK.
 * 2. Client extracts Firebase ID Token (user.getIdToken()).
 * 3. Client sends ID Token to Flask backend (/api/auth/firebase-login).
 * 4. Backend verifies token, creates/syncs Firestore user, and issues a Flask JWT.
 * 5. Client stores the Flask JWT for all subsequent API authorization.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { firebaseLogin, login as flaskLogin, signup as flaskSignup } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  auth, 
  googleProvider, 
  getFirebaseErrorMessage, 
  isElectron,
  isFirebaseConfigured
} from '../services/firebase';
import { 
  signInWithPopup, 
  signInWithRedirect 
} from 'firebase/auth';
import './Login.css';

type FormTab = 'login' | 'signup';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login: loginContext, isAuthenticated } = useAuth();

  // Redirect to Dashboard if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/analytics');
    }
  }, [isAuthenticated, navigate]);

  // ===== UI STATE MANAGEMENT =====
  const [activeTab, setActiveTab] = useState<FormTab>('login');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // ===== LOGIN FORM STATE =====
  const [loginForm, setLoginForm] = useState({
    email: '',
    password: '',
  });

  // ===== SIGNUP FORM STATE =====
  const [signupForm, setSignupForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  /**
   * Helper: Sends Firebase ID token to Flask backend to complete authentication
   */
  const handleFirebaseTokenExchange = async (firebaseUser: any) => {
    try {
      setMessage('Verifying session with Presenova server...');
      const idToken = await firebaseUser.getIdToken(true);
      const response = await firebaseLogin(idToken);

      // Save Flask JWT in AuthContext
      loginContext(response.user, response.access_token);
      setMessage('Login successful! Redirecting to Dashboard...');

      setTimeout(() => {
        navigate('/analytics');
      }, 1000);
    } catch (err: any) {
      console.error('Firebase token exchange failed:', err);
      const errMsg = err?.message || 'Server verification failed. Please try again.';
      setError(errMsg);
    }
  };

  /**
   * Handle Google Sign-In
   * Uses popup for Web browser and redirect fallback for Electron runtime
   */
  const handleGoogleSignIn = async () => {
    setError(null);
    setMessage(null);
    setIsLoading(true);

    if (!isFirebaseConfigured()) {
      setError('Google Sign-In requires VITE_FIREBASE_API_KEY in frontend/.env. Please log in using Email & Password.');
      setIsLoading(false);
      return;
    }

    try {
      let userCredential;
      if (isElectron()) {
        await signInWithRedirect(auth, googleProvider);
        return;
      } else {
        userCredential = await signInWithPopup(auth, googleProvider);
      }

      if (userCredential?.user) {
        await handleFirebaseTokenExchange(userCredential.user);
      }
    } catch (err: any) {
      console.error('Google sign-in error:', err);
      setError(getFirebaseErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle Email/Password Login
   */
  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setIsLoading(true);

    if (!loginForm.email || !loginForm.password) {
      setError('Please fill in both email and password');
      setIsLoading(false);
      return;
    }

    try {
      const response = await flaskLogin(loginForm.email.trim(), loginForm.password);
      loginContext(response.user, response.access_token);
      setMessage('Login successful! Redirecting to Dashboard...');
      setTimeout(() => navigate('/analytics'), 800);
    } catch (flaskErr: any) {
      console.error('Flask backend login error:', flaskErr);
      setError(flaskErr?.message || 'Login failed. Incorrect email or password, or account not registered yet.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handle Email/Password Registration
   */
  const handleEmailSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setIsLoading(true);

    if (!signupForm.name || !signupForm.email || !signupForm.password) {
      setError('Please fill in all required fields');
      setIsLoading(false);
      return;
    }

    if (signupForm.password !== signupForm.confirmPassword) {
      setError('Passwords do not match');
      setIsLoading(false);
      return;
    }

    if (signupForm.password.length < 6) {
      setError('Password must be at least 6 characters');
      setIsLoading(false);
      return;
    }

    try {
      const response = await flaskSignup(signupForm.name.trim(), signupForm.email.trim(), signupForm.password);
      loginContext(response.user, response.access_token);
      setMessage('Account created successfully! Redirecting to Dashboard...');
      setTimeout(() => navigate('/analytics'), 800);
    } catch (flaskErr: any) {
      console.error('Flask backend signup error:', flaskErr);
      setError(flaskErr?.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-card">
          {/* Header */}
          <div className="login-header">
            <h1>Presenova</h1>
            <p>AI Presentation Coaching & Analysis Ecosystem</p>
          </div>

          {/* Tabs */}
          <div className="login-tabs">
            <button
              className={`tab-button ${activeTab === 'login' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('login');
                setError(null);
                setMessage(null);
              }}
              disabled={isLoading}
            >
              Log In
            </button>
            <button
              className={`tab-button ${activeTab === 'signup' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('signup');
                setError(null);
                setMessage(null);
              }}
              disabled={isLoading}
            >
              Sign Up
            </button>
          </div>

          {/* Feedback Messages */}
          {error && <div className="message message-error">{error}</div>}
          {message && <div className="message message-success">{message}</div>}

          <div className="login-form">
            {/* Google One-Click Sign In */}
            <button
              type="button"
              className="google-auth-btn"
              onClick={handleGoogleSignIn}
              disabled={isLoading}
            >
              <svg className="google-icon" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Continue with Google</span>
            </button>

            <div className="auth-divider">
              <span>Or with Email</span>
            </div>

            {/* Email/Password Login Form */}
            {activeTab === 'login' && (
              <form onSubmit={handleEmailLogin}>
                <div className="form-group">
                  <label htmlFor="login-email">Email Address</label>
                  <input
                    id="login-email"
                    type="email"
                    placeholder="your@email.com"
                    value={loginForm.email}
                    onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                    disabled={isLoading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="login-password">Password</label>
                  <input
                    id="login-password"
                    type="password"
                    placeholder="Enter your password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                    disabled={isLoading}
                    required
                  />
                </div>

                <button type="submit" className="login-button" disabled={isLoading}>
                  {isLoading ? 'Signing in...' : 'Log In'}
                </button>
              </form>
            )}

            {/* Email/Password Signup Form */}
            {activeTab === 'signup' && (
              <form onSubmit={handleEmailSignup}>
                <div className="form-group">
                  <label htmlFor="signup-name">Full Name</label>
                  <input
                    id="signup-name"
                    type="text"
                    placeholder="John Doe"
                    value={signupForm.name}
                    onChange={(e) => setSignupForm({ ...signupForm, name: e.target.value })}
                    disabled={isLoading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="signup-email">Email Address</label>
                  <input
                    id="signup-email"
                    type="email"
                    placeholder="your@email.com"
                    value={signupForm.email}
                    onChange={(e) => setSignupForm({ ...signupForm, email: e.target.value })}
                    disabled={isLoading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="signup-password">Password</label>
                  <input
                    id="signup-password"
                    type="password"
                    placeholder="Min 6 characters"
                    value={signupForm.password}
                    onChange={(e) => setSignupForm({ ...signupForm, password: e.target.value })}
                    disabled={isLoading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="signup-confirm">Confirm Password</label>
                  <input
                    id="signup-confirm"
                    type="password"
                    placeholder="Confirm your password"
                    value={signupForm.confirmPassword}
                    onChange={(e) => setSignupForm({ ...signupForm, confirmPassword: e.target.value })}
                    disabled={isLoading}
                    required
                  />
                </div>

                <button type="submit" className="login-button" disabled={isLoading}>
                  {isLoading ? 'Creating account...' : 'Create Account'}
                </button>
              </form>
            )}
          </div>

          {/* Footer */}
          <div className="login-footer">
            <p>Protected by Firebase Identity & Flask JWT authorization</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
