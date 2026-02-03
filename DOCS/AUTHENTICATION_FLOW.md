# 🔄 Authentication Flow Documentation

Complete visual guide to the authentication flow in Computer Students Hub.

---

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATION                          │
│                    (Next.js / React / Mobile)                       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            │ HTTPS/REST API
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                         DJANGO BACKEND                              │
│                                                                     │
│  ┌──────────────────┐      ┌─────────────────┐                    │
│  │  API Endpoints   │      │  Middleware     │                    │
│  │  - Register      │◄────►│  - JWT Verify   │                    │
│  │  - Login         │      │  - CORS         │                    │
│  │  - Profile       │      │  - CSRF         │                    │
│  └────────┬─────────┘      └─────────────────┘                    │
│           │                                                         │
│           │                                                         │
│  ┌────────▼─────────────────────────────────────────┐             │
│  │          USER SERVICE (Business Logic)           │             │
│  │  - Create/Update users in Django                 │             │
│  │  - Assign roles (Student, Teacher, Admin)        │             │
│  │  - Sync with Supabase                            │             │
│  └────────┬─────────────────────────────────────────┘             │
│           │                                                         │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            │ Python Client SDK
            │
┌───────────▼─────────────────────────────────────────────────────────┐
│                        SUPABASE BACKEND                             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │                    AUTH SERVICE                          │      │
│  │  - User registration                                     │      │
│  │  - Password authentication                               │      │
│  │  - JWT token generation                                  │      │
│  │  - Session management                                    │      │
│  └──────────────────────────┬───────────────────────────────┘      │
│                             │                                       │
│  ┌──────────────────────────▼──────────────────────────────┐      │
│  │                  POSTGRESQL DATABASE                     │      │
│  │                                                          │      │
│  │  - auth.users (Supabase managed)                        │      │
│  │  - public.users_user (Django synced)                    │      │
│  │  - public.users_userprofile                             │      │
│  │  - public.users_role                                    │      │
│  │  - public.users_roleassignment                          │      │
│  └──────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Registration Flow (Step-by-Step)

### Visual Diagram

```
USER                    FRONTEND              DJANGO API           SUPABASE         DATABASE
 │                         │                      │                   │                │
 │  Fill Form             │                      │                   │                │
 │  - Email               │                      │                   │                │
 │  - Password            │                      │                   │                │
 │  - Display Name        │                      │                   │                │
 │─────────────────────►  │                      │                   │                │
 │                        │                      │                   │                │
 │                        │  POST /api/auth/     │                   │                │
 │                        │  test-register/      │                   │                │
 │                        │  {email, pwd, name}  │                   │                │
 │                        │──────────────────────►                   │                │
 │                        │                      │                   │                │
 │                        │                      │  auth.sign_up()   │                │
 │                        │                      │  {email, pwd,     │                │
 │                        │                      │   metadata}       │                │
 │                        │                      │───────────────────►                │
 │                        │                      │                   │                │
 │                        │                      │                   │  INSERT INTO   │
 │                        │                      │                   │  auth.users    │
 │                        │                      │                   │  VALUES(...)   │
 │                        │                      │                   │────────────────►
 │                        │                      │                   │                │
 │                        │                      │                   │◄───────────────┤
 │                        │                      │                   │  user_id,      │
 │                        │                      │                   │  created_at    │
 │                        │                      │                   │                │
 │                        │                      │  Generate JWT     │                │
 │                        │                      │  access_token     │                │
 │                        │                      │◄──────────────────┤                │
 │                        │                      │  {user, session}  │                │
 │                        │                      │                   │                │
 │                        │                      │  Sync to Django   │                │
 │                        │                      │  UserService.     │                │
 │                        │                      │  sync_from_       │                │
 │                        │                      │  supabase()       │                │
 │                        │                      │                   │                │
 │                        │                      │                   │  INSERT/UPDATE │
 │                        │                      │                   │  users_user    │
 │                        │                      │  ─────────────────┼────────────────►
 │                        │                      │                   │                │
 │                        │                      │                   │  INSERT        │
 │                        │                      │                   │  users_        │
 │                        │                      │                   │  userprofile   │
 │                        │                      │  ─────────────────┼────────────────►
 │                        │                      │                   │                │
 │                        │                      │  Assign "Student" │  INSERT        │
 │                        │                      │  role             │  users_role    │
 │                        │                      │                   │  assignment    │
 │                        │                      │  ─────────────────┼────────────────►
 │                        │                      │                   │                │
 │                        │  200 OK              │                   │                │
 │                        │  {success: true,     │                   │                │
 │                        │   user: {...},       │                   │                │
 │                        │   session: {...},    │                   │                │
 │                        │   django_user: {...}}│                   │                │
 │                        │◄─────────────────────┤                   │                │
 │                        │                      │                   │                │
 │  Store tokens          │                      │                   │                │
 │  - access_token        │                      │                   │                │
 │  - refresh_token       │                      │                   │                │
 │◄───────────────────────┤                      │                   │                │
 │                        │                      │                   │                │
 │  Redirect to Dashboard │                      │                   │                │
 │◄───────────────────────┤                      │                   │                │
 │                        │                      │                   │                │
```

### Detailed Steps

#### Step 1: User Input
```
User fills registration form:
├── Email: student@university.edu
├── Password: SecurePass123!
└── Display Name: Jane Smith
```

#### Step 2: Frontend Validation
```javascript
// Client-side validation
- Email format check
- Password length (min 6 chars)
- Display name not empty
```

#### Step 3: API Request
```http
POST /api/auth/test-register/ HTTP/1.1
Content-Type: application/json

{
  "email": "student@university.edu",
  "password": "SecurePass123!",
  "display_name": "Jane Smith"
}
```

#### Step 4: Django Processing
```python
# users/test_auth_views.py

def test_register(request):
    # 1. Parse request data
    data = json.loads(request.body)
    email = data['email']
    password = data['password']
    display_name = data['display_name']
    
    # 2. Call Supabase Auth
    supabase = get_supabase_client()
    result = supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {
                "display_name": display_name
            }
        }
    })
    
    # 3. Sync to Django database
    django_user = UserService.sync_from_supabase(
        supabase_user=result.user
    )
    
    # 4. Return response with tokens
    return JsonResponse({
        "success": True,
        "user": result.user,
        "session": result.session,
        "django_user": django_user
    })
```

#### Step 5: Supabase Processing
```sql
-- Supabase automatically executes:

-- 1. Create auth user
INSERT INTO auth.users (
    id,
    email,
    encrypted_password,
    email_confirmed_at,
    user_metadata,
    created_at
) VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'student@university.edu',
    '$2a$10$hashed_password...',
    NULL,  -- Email not confirmed yet
    '{"display_name": "Jane Smith"}',
    NOW()
);

-- 2. Generate JWT token
-- Supabase signs a JWT with user claims
```

#### Step 6: Django Database Sync
```python
# users/services/user_service.py

@staticmethod
def sync_from_supabase(supabase_user):
    # 1. Create/update Django user
    user, created = User.objects.update_or_create(
        supabase_id=supabase_user.id,
        defaults={
            'email': supabase_user.email,
            'display_name': supabase_user.user_metadata.get('display_name'),
            'is_active': True,
        }
    )
    
    # 2. Create user profile
    UserProfile.objects.get_or_create(user=user)
    
    # 3. Assign Student role
    student_role = Role.objects.get(name='Student')
    RoleAssignment.objects.get_or_create(
        user=user,
        role=student_role
    )
    
    return user
```

#### Step 7: Database State
```sql
-- After registration, database contains:

-- Table: auth.users (Supabase managed)
id: 550e8400-e29b-41d4-a716-446655440000
email: student@university.edu
encrypted_password: $2a$10$...
user_metadata: {"display_name": "Jane Smith"}

-- Table: public.users_user (Django)
id: abc123...
supabase_id: 550e8400-e29b-41d4-a716-446655440000
email: student@university.edu
display_name: Jane Smith
is_active: true

-- Table: public.users_userprofile
user_id: abc123...
bio: null
avatar_url: null

-- Table: public.users_roleassignment
user_id: abc123...
role_id: <Student role ID>
```

#### Step 8: Response to Client
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "student@university.edu",
    "user_metadata": {
      "display_name": "Jane Smith"
    }
  },
  "session": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "v1.MRXXX...",
    "expires_in": 3600,
    "token_type": "bearer"
  },
  "django_user": {
    "id": "abc123...",
    "supabase_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "student@university.edu",
    "display_name": "Jane Smith",
    "roles": ["student"]
  }
}
```

#### Step 9: Client-Side Token Storage
```javascript
// Frontend stores tokens
localStorage.setItem('access_token', response.session.access_token);
localStorage.setItem('refresh_token', response.session.refresh_token);
localStorage.setItem('user', JSON.stringify(response.django_user));

// Redirect to dashboard
router.push('/dashboard');
```

---

## 🔑 Login Flow (Step-by-Step)

### Visual Diagram

```
USER            FRONTEND          DJANGO API         SUPABASE       DATABASE
 │                 │                   │                 │              │
 │  Enter          │                   │                 │              │
 │  Credentials    │                   │                 │              │
 │─────────────►   │                   │                 │              │
 │                 │                   │                 │              │
 │                 │  POST /api/auth/  │                 │              │
 │                 │  test-login/      │                 │              │
 │                 │  {email, pwd}     │                 │              │
 │                 │───────────────────►                 │              │
 │                 │                   │                 │              │
 │                 │                   │  auth.sign_in_  │              │
 │                 │                   │  with_password()│              │
 │                 │                   │─────────────────►              │
 │                 │                   │                 │              │
 │                 │                   │                 │  SELECT *    │
 │                 │                   │                 │  FROM        │
 │                 │                   │                 │  auth.users  │
 │                 │                   │                 │  WHERE email │
 │                 │                   │                 │──────────────►
 │                 │                   │                 │              │
 │                 │                   │                 │  Verify pwd  │
 │                 │                   │                 │◄─────────────┤
 │                 │                   │                 │              │
 │                 │                   │  Generate new   │              │
 │                 │                   │  JWT token      │              │
 │                 │                   │◄────────────────┤              │
 │                 │                   │                 │              │
 │                 │                   │  Update Django  │  UPDATE      │
 │                 │                   │  user           │  users_user  │
 │                 │                   │  last_login     │  SET...      │
 │                 │                   │─────────────────┼──────────────►
 │                 │                   │                 │              │
 │                 │  200 OK           │                 │              │
 │                 │  {user, session}  │                 │              │
 │                 │◄──────────────────┤                 │              │
 │                 │                   │                 │              │
 │  Store tokens   │                   │                 │              │
 │◄────────────────┤                   │                 │              │
 │                 │                   │                 │              │
 │  Access         │                   │                 │              │
 │  Dashboard      │                   │                 │              │
 │◄────────────────┤                   │                 │              │
```

---

## 🛡️ Authenticated Request Flow

### Making Authenticated API Calls

```
CLIENT           DJANGO API         MIDDLEWARE        DATABASE
  │                  │                   │                │
  │  GET /api/      │                   │                │
  │  courses/       │                   │                │
  │  Authorization: │                   │                │
  │  Bearer eyJ...  │                   │                │
  │─────────────────►                   │                │
  │                 │                   │                │
  │                 │  Extract JWT      │                │
  │                 │  from header      │                │
  │                 │───────────────────►                │
  │                 │                   │                │
  │                 │                   │  Verify JWT    │
  │                 │                   │  signature     │
  │                 │                   │  with secret   │
  │                 │                   │                │
  │                 │                   │  Decode claims │
  │                 │                   │  {user_id,     │
  │                 │                   │   email, exp}  │
  │                 │                   │                │
  │                 │                   │  SELECT user   │
  │                 │                   │  FROM Django   │
  │                 │                   │  by supabase_id│
  │                 │                   │────────────────►
  │                 │                   │                │
  │                 │                   │◄───────────────┤
  │                 │                   │  User object   │
  │                 │                   │                │
  │                 │  request.user =   │                │
  │                 │  <User object>    │                │
  │                 │◄──────────────────┤                │
  │                 │                   │                │
  │                 │  Execute view     │                │
  │                 │  with auth user   │                │
  │                 │                   │                │
  │  200 OK         │                   │                │
  │  {courses: []}  │                   │                │
  │◄────────────────┤                   │                │
```

---

## 🔄 Token Lifecycle

```
Registration/Login
      │
      ▼
┌─────────────────────┐
│ Generate JWT Token  │
│ - Expires in 1 hour │
│ - Contains user ID  │
│ - Signed by secret  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Client stores token │
│ - localStorage      │
│ - sessionStorage    │
│ - Memory (secure)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Include in requests │
│ Authorization:      │
│ Bearer <token>      │
└──────────┬──────────┘
           │
           ▼
      ┌────────┐
      │ Valid? │
      └────┬───┘
           │
      ┌────┴────┐
      │         │
      ▼         ▼
    YES        NO
     │          │
     │          ▼
     │    ┌─────────────┐
     │    │ Return 401  │
     │    │ Unauthorized│
     │    └──────┬──────┘
     │           │
     │           ▼
     │    ┌──────────────┐
     │    │ Clear tokens │
     │    │ Redirect to  │
     │    │ login        │
     │    └──────────────┘
     │
     ▼
┌──────────────┐
│ Process      │
│ Request      │
└──────────────┘
```

---

## 📋 Data Flow Summary

### Registration Creates:
1. **Supabase auth.users** - Authentication record
2. **Django users_user** - Application user
3. **Django users_userprofile** - Extended profile
4. **Django users_roleassignment** - Role mapping (Student)

### Login Updates:
1. **Supabase session** - New JWT token
2. **Django users_user.last_login** - Timestamp update

### Authentication Verifies:
1. **JWT signature** - Token integrity
2. **Token expiration** - Validity period
3. **User existence** - Django database lookup
4. **User status** - is_active flag

---

## 🎯 Security Flow

```
┌──────────────────────────────────────────────────┐
│              Security Layers                     │
├──────────────────────────────────────────────────┤
│                                                  │
│  1. HTTPS/TLS                                   │
│     └─► Encrypted transport                     │
│                                                  │
│  2. Password Hashing                            │
│     └─► bcrypt in Supabase                      │
│                                                  │
│  3. JWT Signing                                 │
│     └─► HMAC-SHA256 with secret                 │
│                                                  │
│  4. Token Expiration                            │
│     └─► 1-hour lifetime                         │
│                                                  │
│  5. CORS Protection                             │
│     └─► Whitelist frontend domains              │
│                                                  │
│  6. CSRF Protection                             │
│     └─► Django middleware                       │
│                                                  │
│  7. Rate Limiting (Future)                      │
│     └─► Prevent brute force                     │
│                                                  │
│  8. Role-Based Access                           │
│     └─► Permission checks                       │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 🔧 Error Handling Flow

```
API Request
    │
    ▼
┌───────────────┐
│ Validation    │
│ - Email       │
│ - Password    │
│ - Required    │
│   fields      │
└───┬───────────┘
    │
    ▼
  Valid?
    │
    ├── NO ──► 400 Bad Request
    │          {error: "Validation failed"}
    │
    ▼ YES
┌───────────────┐
│ Supabase Auth │
└───┬───────────┘
    │
    ▼
  Success?
    │
    ├── NO ──► 401/409/500
    │          {error: "Auth failed"}
    │
    ▼ YES
┌───────────────┐
│ Django Sync   │
└───┬───────────┘
    │
    ▼
  Success?
    │
    ├── NO ──► 500 Internal Error
    │          {error: "Database sync failed"}
    │
    ▼ YES
┌───────────────┐
│ 200 Success   │
│ Return tokens │
└───────────────┘
```

---

## 📊 Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                             │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Next.js │  │  React   │  │  Mobile  │  │  Desktop │           │
│  │   App    │  │   SPA    │  │   App    │  │   App    │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│       │              │              │             │                 │
└───────┼──────────────┼──────────────┼─────────────┼─────────────────┘
        │              │              │             │
        └──────────────┴──────────────┴─────────────┘
                       │
            REST API (JSON over HTTPS)
                       │
┌──────────────────────▼──────────────────────────────────────────────┐
│                          APPLICATION TIER                            │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │                 Django Backend                          │         │
│  │                                                         │         │
│  │  ├─► Auth Endpoints                                    │         │
│  │  ├─► User Service                                      │         │
│  │  ├─► Course Service                                    │         │
│  │  ├─► Academic Service                                  │         │
│  │  └─► Middleware (JWT, CORS, CSRF)                     │         │
│  └────────────────────────────────────────────────────────┘         │
│                       │                                              │
└───────────────────────┼──────────────────────────────────────────────┘
                        │
              Supabase Python SDK
                        │
┌───────────────────────▼──────────────────────────────────────────────┐
│                           BACKEND TIER                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────┐         │
│  │                    Supabase                             │         │
│  │                                                         │         │
│  │  ├─► Auth Service (JWT generation)                     │         │
│  │  ├─► PostgreSQL Database                               │         │
│  │  ├─► Storage (Future: file uploads)                    │         │
│  │  └─► Realtime (Future: notifications)                  │         │
│  └────────────────────────────────────────────────────────┘         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🎓 Key Takeaways

1. **Two-Database Architecture**:
   - Supabase manages authentication (`auth.users`)
   - Django manages application data (`public.users_user`, etc.)
   - Linked via `supabase_id` field

2. **JWT-Based Auth**:
   - Stateless authentication
   - Token contains user claims
   - Verified on every request

3. **Automatic Role Assignment**:
   - New users get "Student" role by default
   - Can be upgraded to Teacher/Admin later

4. **Idempotent Sync**:
   - Safe to call `sync_from_supabase()` multiple times
   - Uses `update_or_create` for safety

5. **Security First**:
   - Passwords never stored in Django
   - All communication over HTTPS in production
   - Tokens expire automatically

---

**Last Updated**: February 2, 2026  
**Version**: 1.0.0  
**Maintainer**: Computer Students Hub Team
