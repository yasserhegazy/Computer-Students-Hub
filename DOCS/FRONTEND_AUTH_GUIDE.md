# 🔐 Frontend Authentication Integration Guide

## Overview

This guide explains how to integrate Supabase authentication with the Computer Students Hub Django backend from your Next.js/React frontend.

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Next.js App    │  1. User registers/logs in
│  (Frontend)     │     using Supabase JS SDK
└────────┬────────┘
         │
         │ Supabase JS SDK
         ▼
┌─────────────────┐
│  Supabase Auth  │  2. Returns JWT access token
│  (Authentication│     + user data
│   Service)      │
└────────┬────────┘
         │
         │ JWT Token
         ▼
┌─────────────────┐
│  Django Backend │  3. Call /api/auth/sync/
│                 │     Django verifies JWT
│                 │     Creates/updates user
│                 │     Assigns Student role
└─────────────────┘
```

---

## 📋 Step-by-Step Integration

### Step 1: Install Supabase JS SDK

```bash
npm install @supabase/supabase-js
# or
yarn add @supabase/supabase-js
```

### Step 2: Create Supabase Client

Create `lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

### Step 3: Environment Variables

Create `.env.local`:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Django API
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
```

### Step 4: Create Authentication Service

Create `lib/auth.ts`:

```typescript
import { supabase } from './supabase';
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export interface RegisterData {
  email: string;
  password: string;
  displayName: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface DjangoUser {
  id: string;
  supabase_id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
}

/**
 * Register a new user
 * 
 * Flow:
 * 1. Create user in Supabase Auth
 * 2. Sync user to Django database
 * 3. Return combined result
 */
export async function registerUser(data: RegisterData) {
  try {
    // Step 1: Register with Supabase
    const { data: authData, error: authError } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
      options: {
        data: {
          display_name: data.displayName,
        },
      },
    });

    if (authError) throw authError;
    if (!authData.session) {
      throw new Error('Email confirmation required. Please check your inbox.');
    }

    // Step 2: Sync user to Django
    const djangoUser = await syncUserToDjango(authData.session.access_token);

    return {
      session: authData.session,
      user: authData.user,
      djangoUser,
    };
  } catch (error: any) {
    console.error('Registration error:', error);
    throw new Error(error.message || 'Registration failed');
  }
}

/**
 * Login existing user
 * 
 * Flow:
 * 1. Authenticate with Supabase
 * 2. Sync user to Django (updates last_login)
 * 3. Return combined result
 */
export async function loginUser(data: LoginData) {
  try {
    // Step 1: Login with Supabase
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email: data.email,
      password: data.password,
    });

    if (authError) throw authError;
    if (!authData.session) {
      throw new Error('Login failed. No session created.');
    }

    // Step 2: Sync user to Django
    const djangoUser = await syncUserToDjango(authData.session.access_token);

    return {
      session: authData.session,
      user: authData.user,
      djangoUser,
    };
  } catch (error: any) {
    console.error('Login error:', error);
    throw new Error(error.message || 'Login failed');
  }
}

/**
 * Sync user from Supabase to Django
 * 
 * This is called after every login/register to ensure:
 * - User exists in Django database
 * - User has correct roles assigned
 * - User data is up to date
 */
async function syncUserToDjango(accessToken: string): Promise<DjangoUser> {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/sync/`,
      {},
      {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.data.success) {
      throw new Error(response.data.error || 'Sync failed');
    }

    return response.data.user;
  } catch (error: any) {
    console.error('Django sync error:', error.response?.data || error.message);
    throw new Error('Failed to sync user to backend');
  }
}

/**
 * Logout user
 */
export async function logoutUser() {
  const { error } = await supabase.auth.signOut();
  if (error) throw error;
}

/**
 * Get current session
 */
export async function getSession() {
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error) throw error;
  return session;
}
```

### Step 5: Create Authentication Context

Create `contexts/AuthContext.tsx`:

```typescript
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';
import { registerUser, loginUser, logoutUser, getSession, DjangoUser } from '@/lib/auth';
import type { RegisterData, LoginData } from '@/lib/auth';

interface AuthContextType {
  session: Session | null;
  user: User | null;
  djangoUser: DjangoUser | null;
  loading: boolean;
  error: string | null;
  register: (data: RegisterData) => Promise<void>;
  login: (data: LoginData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [djangoUser, setDjangoUser] = useState<DjangoUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Get initial session
    getSession().then((session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const register = async (data: RegisterData) => {
    try {
      setLoading(true);
      setError(null);

      const result = await registerUser(data);
      
      setSession(result.session);
      setUser(result.user);
      setDjangoUser(result.djangoUser);
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const login = async (data: LoginData) => {
    try {
      setLoading(true);
      setError(null);

      const result = await loginUser(data);
      
      setSession(result.session);
      setUser(result.user);
      setDjangoUser(result.djangoUser);
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      await logoutUser();
      setSession(null);
      setUser(null);
      setDjangoUser(null);
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const value: AuthContextType = {
    session,
    user,
    djangoUser,
    loading,
    error,
    register,
    login,
    logout,
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

### Step 6: Wrap App with AuthProvider

Update `app/layout.tsx`:

```typescript
import { AuthProvider } from '@/contexts/AuthContext';

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

### Step 7: Create Login Component

Create `components/LoginForm.tsx`:

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
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      
      <input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        required
      />
      
      <input
        type="password"
        placeholder="Password"
        value={formData.password}
        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
        required
      />
      
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  );
}
```

### Step 8: Create Register Component

Create `components/RegisterForm.tsx`:

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
    displayName: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await register(formData);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      
      <input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        required
      />
      
      <input
        type="text"
        placeholder="Display Name"
        value={formData.displayName}
        onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
        required
      />
      
      <input
        type="password"
        placeholder="Password"
        value={formData.password}
        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
        required
        minLength={6}
      />
      
      <button type="submit" disabled={loading}>
        {loading ? 'Creating account...' : 'Register'}
      </button>
    </form>
  );
}
```

### Step 9: Make Authenticated API Calls

Create `lib/api.ts` for other API calls:

```typescript
import axios from 'axios';
import { supabase } from './supabase';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to every request
apiClient.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  
  return config;
});

// Handle token expiration
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired, redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// Example API calls
export const api = {
  // Get current user
  getCurrentUser: () => apiClient.get('/users/me/'),
  
  // Get courses
  getCourses: () => apiClient.get('/courses/'),
  
  // Other endpoints...
};
```

---

## 🔄 Complete Authentication Flow

```
USER ACTION          FRONTEND                  SUPABASE              DJANGO
    │                    │                         │                     │
    │  Click Register    │                         │                     │
    ├────────────────────►                         │                     │
    │                    │                         │                     │
    │                    │  supabase.auth.signUp() │                     │
    │                    ├─────────────────────────►                     │
    │                    │                         │                     │
    │                    │  ◄ JWT Token + User     │                     │
    │                    │◄────────────────────────┤                     │
    │                    │                         │                     │
    │                    │  POST /api/auth/sync/    │                    │
    │                    │  (with JWT token)       │                     │
    │                    ├─────────────────────────┼─────────────────────►
    │                    │                         │                     │
    │                    │                         │  Verify JWT         │
    │                    │                         │  Create Django User │
    │                    │                         │  Assign Student Role│
    │                    │                         │                     │
    │                    │  ◄ Django User + Roles  │                     │
    │                    │◄────────────────────────┼─────────────────────┤
    │                    │                         │                     │
    │  ◄ Success!        │                         │                     │
    │◄───────────────────┤                         │                     │
    │                    │                         │                     │
    │  Navigate to       │                         │                     │
    │  Dashboard         │                         │                     │
    ├────────────────────►                         │                     │
    │                    │                         │                     │
    │                    │  GET /api/users/me/     │                     │
    │                    │  (with JWT token)       │                     │
    │                    ├─────────────────────────┼─────────────────────►
    │                    │                         │                     │
    │                    │  ◄ User Profile         │                     │
    │                    │◄────────────────────────┼─────────────────────┤
    │                    │                         │                     │
    │  ◄ Show Profile    │                         │                     │
    │◄───────────────────┤                         │                     │
```

---

## ✅ Checklist

- [ ] Install `@supabase/supabase-js`
- [ ] Create Supabase client (`lib/supabase.ts`)
- [ ] Add environment variables (`.env.local`)
- [ ] Create auth service (`lib/auth.ts`)
- [ ] Create Auth Context (`contexts/AuthContext.tsx`)
- [ ] Wrap app with AuthProvider
- [ ] Create Login component
- [ ] Create Register component
- [ ] Set up API client with auto-token injection
- [ ] Test registration flow
- [ ] Test login flow
- [ ] Test authenticated API calls

---

## 🐛 Common Issues

### Issue: "Email confirmation required"

**Cause**: Supabase email confirmation is enabled

**Solution**: Either:
1. Disable email confirmation in Supabase dashboard (for development)
2. Handle confirmation flow in your app

### Issue: "Sync failed"

**Cause**: Django backend not running or wrong URL

**Solution**: 
- Verify Django server is running: `python manage.py runserver`
- Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`

### Issue: "CORS error"

**Cause**: Django not configured to accept requests from frontend

**Solution**: Add to Django `settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
```

---

## 📚 Next Steps

1. Implement password reset flow
2. Add email verification handling
3. Create protected route wrapper
4. Add loading states
5. Implement token refresh logic
6. Add error boundaries

---

**Need Help?**
- Check [Next.js Integration Guide](./NEXTJS_INTEGRATION.md) for more details
- Review [API Endpoints Documentation](./API_AUTH_ENDPOINTS.md)
- See [Authentication Flow](./AUTHENTICATION_FLOW.md) for architecture details
