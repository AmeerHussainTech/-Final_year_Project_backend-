/**
 * AuthContext
 * React Context for managing global authentication state
 *
 * Features:
 * - Global auth state management (user, token, isAuthenticated)
 * - Secure localStorage token storage
 * - Login/Logout functions
 * - Automatic token recovery on app load
 */

import React, { createContext, useContext, useState, useEffect } from 'react';

/**
 * User object structure
 */
export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

/**
 * AuthContext shape
 */
interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
}

/**
 * Create Auth Context with default values
 */
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider Component
 * Wraps the app and provides auth state to all children
 */
export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // ===== STATE MANAGEMENT =====
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ===== INITIALIZE AUTH STATE ON APP LOAD =====
  // Recover token from localStorage if it exists
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // ===== STEP 1: RECOVER TOKEN FROM LOCALSTORAGE =====
        const storedToken = localStorage.getItem('auth_token');

        if (storedToken) {
          setToken(storedToken);

          // ===== STEP 2: VERIFY TOKEN BY FETCHING CURRENT USER =====
          // This ensures the token is still valid
          // Use VITE_API_BASE_URL so this works in both dev and production
          const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
          const response = await fetch(`${apiBase}/auth/me`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${storedToken}`,
              'Content-Type': 'application/json'
            }
          });

          if (response.ok) {
            const data = await response.json();
            setUser(data.user);
          } else {
            // Token is invalid or expired
            localStorage.removeItem('auth_token');
            setToken(null);
          }
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        // Clear invalid token on error
        localStorage.removeItem('auth_token');
        setToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  // ===== LOGIN HANDLER =====
  /**
   * Login function to set user and token
   * Automatically saves token to localStorage
   *
   * @param user - User object from server
   * @param newToken - JWT access token from server
   */
  const login = (user: User, newToken: string) => {
    // ===== CRITICAL: SECURE TOKEN STORAGE =====
    // Save JWT token to localStorage for persistence across page refreshes
    // Token is automatically sent with every API request via interceptor
    localStorage.setItem('auth_token', newToken);

    setUser(user);
    setToken(newToken);

    console.log('User logged in:', user.email);
  };

  // ===== LOGOUT HANDLER =====
  /**
   * Logout function to clear auth state
   * Removes token from localStorage
   */
  const logout = () => {
    // ===== STEP 1: CLEAR LOCALSTORAGE =====
    localStorage.removeItem('auth_token');

    // ===== STEP 2: CLEAR STATE =====
    setUser(null);
    setToken(null);

    console.log('User logged out');
  };

  // ===== CONTEXT VALUE =====
  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    setUser,
    setToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * useAuth Hook
 * Access auth context from any component
 *
 * @returns AuthContextType with user, token, login, logout, etc.
 *
 * Usage:
 * const { user, isAuthenticated, login, logout } = useAuth();
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};
