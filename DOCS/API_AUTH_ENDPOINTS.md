# 🔐 Authentication API Endpoints

## Overview

The Computer Students Hub uses **Supabase Authentication** with JWT tokens for secure user authentication. This document provides complete API documentation for authentication endpoints.

**Authentication Architecture:**
- Frontend authenticates users directly with Supabase (using Supabase JS SDK)
- Frontend receives JWT access token from Supabase
- Frontend syncs user to Django by calling `/api/auth/sync/` endpoint
- Django verifies JWT, creates/updates user in database, and assigns roles
- Frontend uses JWT token for all subsequent authenticated requests

---

## 📍 Base URL

```
Local Development: http://127.0.0.1:8000
Production: https://your-domain.com
```

---

## 🎯 Available Endpoints

### 1. Sync User from Supabase to Django
**POST** `/api/auth/sync/`

Synchronizes a user from Supabase Auth to Django database after successful authentication.
This endpoint should be called immediately after Supabase authentication (register or login).

#### Request Headers
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

#### Request Example (cURL)
```bash
curl -X POST http://127.0.0.1:8000/api/auth/sync/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

#### Success Response (200 OK)
```json
{
  "success": true,
  "message": "User synced successfully",
  "user": {
    "id": "abc123-def456-ghi789",
    "supabase_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "student@university.edu",
    "display_name": "Jane Smith",
    "is_active": true,
    "roles": ["student"]
  }
}
```

#### Error Response (401 Unauthorized)
```json
{
  "error": "Authentication required",
  "details": "No valid JWT token provided"
}
```

#### Error Response (500 Internal Server Error)
```json
{
  "error": "Sync failed",
  "details": "Error message details"
}
```

---

### 2. Get Current User Profile
**GET** `/api/users/me/`

Returns the profile and roles of the currently authenticated user.

#### Request Headers
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Request Example (cURL)
```bash
curl -X GET http://127.0.0.1:8000/api/users/me/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Success Response (200 OK)
```json
{
  "id": "abc123-def456-ghi789",
  "email": "student@university.edu",
  "display_name": "Jane Smith",
  "is_active": true,
  "roles": ["student"],
  "profile": {
    "bio": "Computer Science student",
    "avatar_url": null
  }
}
```

---

## 🔑 Using Access Tokens

After successful login/registration, use the `access_token` for authenticated API requests:

### Request Header Format
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Example Authenticated Request
```bash
curl -X GET http://127.0.0.1:8000/api/users/me/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Details
- **Type**: JWT (JSON Web Token)
- **Lifetime**: 3600 seconds (1 hour)
- **Storage**: Store securely (localStorage for web, secure storage for mobile)
- **Refresh**: Use `refresh_token` to get new access token before expiry

---

## 🔄 Authentication Flow Diagram

```
┌─────────────┐
│   Client    │
│ (Next.js)   │
└──────┬──────┘
       │
       │ 1. POST /api/auth/test-register/
       │    {email, password, display_name}
       ▼
┌─────────────────────┐
│  Django Backend     │
│  (API Server)       │
└──────┬──────────────┘
       │
       │ 2. Create user in Supabase Auth
       ▼
┌─────────────────────┐
│  Supabase Auth      │
│  (Authentication)   │
└──────┬──────────────┘
       │
       │ 3. Return user + JWT tokens
       ▼
┌─────────────────────┐
│  Django Backend     │
│  - Sync to Django DB│
│  - Assign Student   │
│    role             │
│  - Create profile   │
└──────┬──────────────┘
       │
       │ 4. Return complete response
       │    {user, session, django_user}
       ▼
┌─────────────┐
│   Client    │
│ - Store     │
│   token     │
│ - Update UI │
└─────────────┘
```

---

## 📊 Database Changes

### On Registration/Login

#### Supabase Tables
1. **auth.users** - Main authentication table
   - `id` (UUID)
   - `email`
   - `encrypted_password`
   - `email_confirmed_at`
   - `created_at`
   - `user_metadata` (JSON with display_name)

#### Django Tables
1. **users_user** - Django user record
   - `id` (Django UUID)
   - `supabase_id` (maps to auth.users.id)
   - `email`
   - `display_name`
   - `is_active`
   - `created_at`

2. **users_userprofile** - Extended user information
   - `user_id` (FK to users_user)
   - `bio`
   - `avatar_url`
   - Additional profile fields

3. **users_roleassignment** - User role mapping
   - `user_id` (FK to users_user)
   - `role_id` (FK to users_role)
   - Auto-assigns "Student" role on registration

---

## 🛡️ Security Features

### Password Requirements
- Minimum 6 characters (configurable in Supabase)
- Stored as bcrypt hash in Supabase
- Never transmitted in plain text

### JWT Token Security
- Signed with Supabase JWT secret
- Contains user claims (id, email, role)
- Verified on every authenticated request
- Automatic expiration after 1 hour

### HTTPS/TLS
- **Production**: Always use HTTPS
- **Development**: HTTP acceptable for localhost

### CORS Configuration
- Configured to accept requests from frontend domain
- Credentials allowed for cookie-based sessions

---

## ⚠️ Error Codes

| Status Code | Error | Description |
|-------------|-------|-------------|
| 400 | Bad Request | Missing or invalid fields |
| 401 | Unauthorized | Invalid credentials |
| 403 | Forbidden | Account disabled or insufficient permissions |
| 409 | Conflict | Email already registered |
| 500 | Internal Server Error | Server-side error |

---

## 🧪 Testing Endpoints

### Interactive Testing
- **HTML Interface**: http://127.0.0.1:8000/api/auth/test/
- **Swagger UI**: http://127.0.0.1:8000/api/docs/
- **OpenAPI Schema**: http://127.0.0.1:8000/api/schema/

### Automated Testing
```bash
# Run integration tests
pytest users/tests/test_integration_supabase_auth.py -v

# Run Python test script
python test_auth_endpoints.py
```

---

## 📝 Rate Limiting

**Current**: No rate limiting (development)

**Recommended for Production**:
- Registration: 5 attempts per hour per IP
- Login: 10 attempts per hour per IP
- Failed login lockout: 5 failed attempts = 15-minute lockout

---

## 🔗 Related Documentation

- [Supabase Auth Flow](../SUPABASE_AUTH_FLOW.md)
- [Next.js Integration Guide](./NEXTJS_INTEGRATION.md)
- [Testing Guide](./TESTING_AUTH.md)
- [Quick Start Guide](../QUICKSTART_HTML_TESTING.md)

---

## 💡 Best Practices

1. **Always use HTTPS in production**
2. **Store tokens securely** (not in localStorage for sensitive apps)
3. **Implement token refresh logic** before expiration
4. **Handle 401 errors** by redirecting to login
5. **Validate input** on client-side before API call
6. **Log authentication events** for security monitoring
7. **Use environment variables** for API URLs
8. **Implement CSRF protection** for state-changing operations

---

**Last Updated**: February 2, 2026  
**API Version**: 1.0.0  
**Contact**: [Your Team Email]
