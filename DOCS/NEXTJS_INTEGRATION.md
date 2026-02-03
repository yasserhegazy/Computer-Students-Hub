# ⚡ Next.js Integration Guide

Complete guide for integrating Computer Students Hub authentication with your Next.js frontend.

---

## 📋 Table of Contents

1. [Setup & Installation](#setup--installation)
2. [Environment Configuration](#environment-configuration)
3. [Authentication Context](#authentication-context)
4. [API Client Setup](#api-client-setup)
5. [Login/Register Components](#loginregister-components)
6. [Protected Routes](#protected-routes)
7. [Token Management](#token-management)
8. [Error Handling](#error-handling)
9. [Complete Examples](#complete-examples)

---

## 🚀 Setup & Installation

### 1. Create Next.js Project (if new)

```bash
npx create-next-app@latest computer-students-hub-frontend
cd computer-students-hub-frontend
```

### 2. Install Required Dependencies

```bash
npm install axios
# or
yarn add axios
# or
pnpm add axios
```

### 3. Project Structure

```
src/
├── app/
│   ├── login/
│   │   └── page.tsx
│   ├── register/
│   │   └── page.tsx
│   ├── dashboard/
│   │   └── page.tsx
│   └── layout.tsx
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── RegisterForm.tsx
│   │   └── ProtectedRoute.tsx
│   └── ui/
│       └── Button.tsx
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   └── types.ts
├── contexts/
│   └── AuthContext.tsx
└── hooks/
    └── useAuth.ts
```

---

## 🔧 Environment Configuration

Create `.env.local` file in your Next.js root:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api

# Optional: Analytics, etc.
NEXT_PUBLIC_APP_NAME=Computer Students Hub
```

**Production `.env.production`:**
```env
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com/api
```

---

## 🎯 TypeScript Types

Create `src/lib/types.ts`:

```typescript
// Authentication Types
export interface User {
  id: string;
  email: string;
  user_metadata: {
    display_name?: string;
  };
  created_at: string;
  last_sign_in_at?: string;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export interface DjangoUser {
  id: string;
  supabase_id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user: User;
  session: Session;
  django_user: DjangoUser;
}

export interface AuthError {
  success: false;
  error: string;
  details?: string;
}

export interface RegisterData {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginData {
  email: string;
  password: string;
}
```

---

## 🔌 API Client Setup

Create `src/lib/api.ts`:

```typescript
import axios, { AxiosError, AxiosInstance } from 'axios';
import type { AuthResponse, AuthError, RegisterData, LoginData } from './types';

// Create axios instance with base configuration
const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 seconds
});

// Request interceptor - Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle token expiration
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('user');
      
      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Authentication API Functions
export const authAPI = {
  /**
   * Register a new user
   */
  register: async (data: RegisterData): Promise<AuthResponse> => {
    try {
      const response = await apiClient.post<AuthResponse>(
        '/auth/test-register/',
        data
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        throw error.response.data as AuthError;
      }
      throw { success: false, error: 'Network error' } as AuthError;
    }
  },

  /**
   * Login existing user
   */
  login: async (data: LoginData): Promise<AuthResponse> => {
    try {
      const response = await apiClient.post<AuthResponse>(
        '/auth/test-login/',
        data
      );
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        throw error.response.data as AuthError;
      }
      throw { success: false, error: 'Network error' } as AuthError;
    }
  },

  /**
   * Check server status
   */
  checkStatus: async (): Promise<{ status: string; message: string }> => {
    const response = await apiClient.get('/auth/test-status/');
    return response.data;
  },

  /**
   * Logout (client-side only for now)
   */
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};

export default apiClient;
```

---

## 🎭 Authentication Context

Create `src/contexts/AuthContext.tsx`:

```typescript
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI } from '@/lib/api';
import type { User, DjangoUser, RegisterData, LoginData } from '@/lib/types';

interface AuthContextType {
  user: DjangoUser | null;
  supabaseUser: User | null;
  loading: boolean;
  error: string | null;
  login: (data: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DjangoUser | null>(null);
  const [supabaseUser, setSupabaseUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load user from localStorage on mount
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedSupabaseUser = localStorage.getItem('supabase_user');
    
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    if (storedSupabaseUser) {
      setSupabaseUser(JSON.parse(storedSupabaseUser));
    }
    
    setLoading(false);
  }, []);

  const login = async (data: LoginData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authAPI.login(data);

      // Store tokens and user data
      localStorage.setItem('access_token', response.session.access_token);
      localStorage.setItem('refresh_token', response.session.refresh_token);
      localStorage.setItem('user', JSON.stringify(response.django_user));
      localStorage.setItem('supabase_user', JSON.stringify(response.user));

      setUser(response.django_user);
      setSupabaseUser(response.user);
    } catch (err: any) {
      setError(err.error || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (data: RegisterData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authAPI.register(data);

      // Store tokens and user data
      localStorage.setItem('access_token', response.session.access_token);
      localStorage.setItem('refresh_token', response.session.refresh_token);
      localStorage.setItem('user', JSON.stringify(response.django_user));
      localStorage.setItem('supabase_user', JSON.stringify(response.user));

      setUser(response.django_user);
      setSupabaseUser(response.user);
    } catch (err: any) {
      setError(err.error || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
    setSupabaseUser(null);
  };

  const value: AuthContextType = {
    user,
    supabaseUser,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

---

## 🔐 Login Component

Create `src/components/auth/LoginForm.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(formData);
      router.push('/dashboard'); // Redirect after successful login
    } catch (err: any) {
      setError(err.error || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Login</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-gray-700 mb-2" htmlFor="email">
            Email
          </label>
          <input
            type="email"
            id="email"
            required
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />
        </div>

        <div className="mb-6">
          <label className="block text-gray-700 mb-2" htmlFor="password">
            Password
          </label>
          <input
            type="password"
            id="password"
            required
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <p className="mt-4 text-center text-gray-600">
        Don't have an account?{' '}
        <a href="/register" className="text-blue-600 hover:underline">
          Register
        </a>
      </p>
    </div>
  );
}
```

---

## 📝 Register Component

Create `src/components/auth/RegisterForm.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function RegisterForm() {
  const router = useRouter();
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    display_name: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await register(formData);
      router.push('/dashboard'); // Redirect after successful registration
    } catch (err: any) {
      setError(err.error || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Register</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-gray-700 mb-2" htmlFor="email">
            Email
          </label>
          <input
            type="email"
            id="email"
            required
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />
        </div>

        <div className="mb-4">
          <label className="block text-gray-700 mb-2" htmlFor="display_name">
            Display Name
          </label>
          <input
            type="text"
            id="display_name"
            required
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            value={formData.display_name}
            onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
          />
        </div>

        <div className="mb-6">
          <label className="block text-gray-700 mb-2" htmlFor="password">
            Password
          </label>
          <input
            type="password"
            id="password"
            required
            minLength={6}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          />
          <p className="text-sm text-gray-500 mt-1">Minimum 6 characters</p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
        >
          {loading ? 'Creating account...' : 'Register'}
        </button>
      </form>

      <p className="mt-4 text-center text-gray-600">
        Already have an account?{' '}
        <a href="/login" className="text-blue-600 hover:underline">
          Login
        </a>
      </p>
    </div>
  );
}
```

---

## 🛡️ Protected Routes

Create `src/components/auth/ProtectedRoute.tsx`:

```typescript
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

---

## 📄 Page Examples

### Login Page (`src/app/login/page.tsx`)

```typescript
import LoginForm from '@/components/auth/LoginForm';

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <LoginForm />
    </main>
  );
}
```

### Register Page (`src/app/register/page.tsx`)

```typescript
import RegisterForm from '@/components/auth/RegisterForm';

export default function RegisterPage() {
  return (
    <main className="min-h-screen bg-gray-50 py-12">
      <RegisterForm />
    </main>
  );
}
```

### Protected Dashboard (`src/app/dashboard/page.tsx`)

```typescript
'use client';

import ProtectedRoute from '@/components/auth/ProtectedRoute';
import { useAuth } from '@/contexts/AuthContext';

export default function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-gray-50 py-12">
        <div className="max-w-4xl mx-auto px-4">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-6">
              <h1 className="text-3xl font-bold">Dashboard</h1>
              <button
                onClick={logout}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-semibold mb-2">Welcome, {user?.display_name}!</h2>
                <p className="text-gray-600">Email: {user?.email}</p>
                <p className="text-gray-600">Roles: {user?.roles.join(', ')}</p>
              </div>

              <div className="border-t pt-4">
                <h3 className="font-semibold mb-2">User Details</h3>
                <pre className="bg-gray-100 p-4 rounded overflow-auto">
                  {JSON.stringify(user, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </main>
    </ProtectedRoute>
  );
}
```

### Root Layout (`src/app/layout.tsx`)

```typescript
import { AuthProvider } from '@/contexts/AuthContext';
import './globals.css';

export const metadata = {
  title: 'Computer Students Hub',
  description: 'Student management platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
```

---

## 🔄 Token Refresh (Advanced)

Create `src/lib/auth.ts` for token management:

```typescript
import apiClient from './api';

export async function refreshAccessToken(refreshToken: string): Promise<string | null> {
  try {
    // This endpoint would need to be implemented on backend
    const response = await apiClient.post('/auth/refresh/', {
      refresh_token: refreshToken,
    });

    const newAccessToken = response.data.access_token;
    localStorage.setItem('access_token', newAccessToken);
    return newAccessToken;
  } catch (error) {
    console.error('Failed to refresh token:', error);
    return null;
  }
}

// Auto-refresh token before expiration
export function setupTokenRefresh() {
  const expiresIn = 3600; // 1 hour in seconds
  const refreshTime = (expiresIn - 300) * 1000; // Refresh 5 minutes before expiry

  setInterval(async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      await refreshAccessToken(refreshToken);
    }
  }, refreshTime);
}
```

---

## ✅ Complete Checklist

- [ ] Install dependencies (`axios`)
- [ ] Create `.env.local` with API URL
- [ ] Set up TypeScript types
- [ ] Create API client with interceptors
- [ ] Create Auth Context Provider
- [ ] Build Login component
- [ ] Build Register component
- [ ] Create Protected Route wrapper
- [ ] Add AuthProvider to root layout
- [ ] Create login/register pages
- [ ] Create protected dashboard
- [ ] Test registration flow
- [ ] Test login flow
- [ ] Test protected routes
- [ ] Test logout functionality

---

## 🚀 Running Your App

```bash
# Development
npm run dev

# Production build
npm run build
npm start
```

Visit:
- **Login**: http://localhost:3000/login
- **Register**: http://localhost:3000/register
- **Dashboard**: http://localhost:3000/dashboard (protected)

---

## 🐛 Troubleshooting

### CORS Errors
Ensure Django `CORS_ALLOWED_ORIGINS` includes `http://localhost:3000`:

```python
# Django settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

### 401 Unauthorized on Authenticated Requests
Check that:
1. Token is stored in localStorage
2. Authorization header is added in interceptor
3. Token hasn't expired (1 hour lifetime)

### User not persisting on page refresh
Verify AuthContext loads user from localStorage on mount

---

## 📚 Next Steps

1. Implement password reset flow
2. Add email verification
3. Create user profile page
4. Add role-based UI rendering
5. Implement token refresh mechanism
6. Add loading states and skeletons
7. Create custom error boundaries

---

**Last Updated**: February 2, 2026  
**Next.js Version**: 14+  
**Author**: Computer Students Hub Team
