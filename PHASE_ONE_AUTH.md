# Phase 1: Database and Authentication Implementation Guide

## Overview

Phase 1 implements user authentication and database management for the FYP Final Project using:
- **Backend**: Flask + SQLAlchemy ORM + Flask-JWT-Extended
- **Frontend**: React + TypeScript + Context API
- **Database**: SQLite (development) / PostgreSQL (production)

---

## Backend Setup

### 1. Database Models (`models.py`)

Three core models define the data structure:

#### User Model
```python
class User:
    id: str (Firebase UID)
    uid: str (Firebase UID)
    name: str
    email: str (unique)
    photo_url: str (optional)
    provider: str ("google" or "password")
    created_at: datetime
    updated_at: datetime
```

**Relationships**:
- One-to-many with `Upload`
- One-to-many with `Report`

#### Upload Model
```python
class Upload(db.Model):
    id: str (UUID)
    filename: str
    mime_type: str
    file_path: str (optional)
    user_id: str (FK to User)
    created_at: datetime
```

**Purpose**: Tracks files uploaded by users for analysis

#### Report Model
```python
class Report(db.Model):
    id: str (UUID)
    report_json: dict (JSON field)
    report_type: str
    user_id: str (FK to User)
    upload_id: str (FK to Upload, nullable)
    created_at: datetime
    updated_at: datetime
```

**Purpose**: Stores analysis results from Phase 2, 4, and 5

### 2. Authentication Routes (`auth.py`)

#### POST `/api/auth/signup`
Creates a new user account.

**Request**:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "message": "User created successfully",
  "user": {
    "id": "uuid-here",
    "name": "John Doe",
    "email": "john@example.com",
    "created_at": "2026-05-24T..."
  },
  "access_token": "eyJhbGc..."
}
```

**Key Features**:
- Email uniqueness validation
- Password hashing with werkzeug.security
- Automatic JWT token generation

#### POST `/api/auth/login`
Authenticates user and returns JWT token.

**Request**:
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Login successful",
  "user": { ... },
  "access_token": "eyJhbGc..."
}
```

#### GET `/api/auth/me`
Requires: `Authorization: Bearer <token>`

Retrieves current user profile.

**Response** (200 OK):
```json
{
  "status": "success",
  "user": { ... }
}
```

### 3. Main App Integration (`main.py`)

```python
# Initialize SQLAlchemy
db.init_app(app)

# Initialize JWT
jwt = JWTManager(app)

# Create database tables
with app.app_context():
    db.create_all()

# Register blueprints
app.register_blueprint(auth_bp)
```

### 4. Environment Configuration (`.env`)

```bash
DATABASE_URL=sqlite:///app.db
JWT_SECRET_KEY=your-super-secret-key-change-in-production
GEMINI_API_KEY=your-api-key
FLASK_ENV=development
FLASK_DEBUG=1
```

**CRITICAL**: In production:
- Change `JWT_SECRET_KEY` to a strong random string
- Use PostgreSQL instead of SQLite
- Set `FLASK_ENV=production`

---

## Frontend Setup

### 1. Authentication Context (`src/context/AuthContext.tsx`)

Global state management for auth using React Context API.

```typescript
interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login(user: User, token: string): void;
  logout(): void;
}
```

**Key Features**:
- Automatic token recovery from localStorage on app load
- Token verification by fetching current user
- Global login/logout handlers
- Auto-logout on token expiry

**Usage**:
```typescript
const { user, isAuthenticated, login, logout } = useAuth();
```

### 2. API Interceptor (`src/services/api.ts`)

JWT token injection on every API request.

```typescript
async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('auth_token');
  
  headers['Authorization'] = `Bearer ${token}`;
  
  // Handle 401 Unauthorized
  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    window.dispatchEvent(new Event('auth-token-expired'));
  }
}
```

**Available Functions**:
- `signup(name, email, password)`
- `login(email, password)`
- `getCurrentUser()`

### 3. Login Page (`src/pages/Login.tsx`)

User-friendly authentication interface with:
- Tab-based form switching (Login / Sign Up)
- Real-time validation
- Error handling
- Automatic redirect on success

### 4. App Integration (`src/App.tsx`)

Wrap app with `AuthProvider` for global auth state:

```typescript
<AuthProvider>
  <Router>
    {/* Routes here */}
  </Router>
</AuthProvider>
```

---

## Security Best Practices

### Backend

1. **Password Hashing**
   ```python
   from werkzeug.security import generate_password_hash, check_password_hash
   
   # During signup
   password_hash = generate_password_hash(password)
   
   # During login
   if check_password_hash(user.password_hash, password):
       # Correct password
   ```

2. **JWT Token Management**
   - Tokens expire in 24 hours (configurable)
   - Secret key should be strong and rotated
   - Never expose token in logs or error messages

3. **Input Validation**
   - Email format validation
   - Password strength requirements (min 6 characters)
   - SQL injection prevention (SQLAlchemy ORM handles this)

### Frontend

1. **Token Storage**
   - Tokens stored in `localStorage` (not ideal for very sensitive data)
   - Cleared on logout or token expiry
   - Never stored in cookies (CSRF vulnerable)

2. **Secure Requests**
   - Token automatically injected via `fetchWithAuth()`
   - HTTPS required in production
   - No credentials in URL parameters

3. **Error Handling**
   - Generic error messages to users (no sensitive details)
   - Console logging disabled in production
   - Token expiry triggers automatic logout

---

## Database Schema

### SQLite (Development)

```sql
-- Users table
CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- Uploads table
CREATE TABLE uploads (
  id VARCHAR(36) PRIMARY KEY,
  filename VARCHAR(255) NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  file_path VARCHAR(500),
  user_id VARCHAR(36) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_uploads_user_id ON uploads(user_id);

-- Reports table
CREATE TABLE reports (
  id VARCHAR(36) PRIMARY KEY,
  report_json JSON NOT NULL,
  report_type VARCHAR(50) DEFAULT 'document_analysis',
  user_id VARCHAR(36) NOT NULL,
  upload_id VARCHAR(36),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE SET NULL
);

CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_reports_upload_id ON reports(upload_id);
CREATE INDEX idx_reports_type ON reports(report_type);
```

---

## API Flow Diagrams

### Signup Flow

```
Frontend (Login.tsx)
    ↓ POST /api/auth/signup
Backend (auth.py)
    ├─ Validate input
    ├─ Hash password
    ├─ Save to database
    └─ Generate JWT token
    ↓
Frontend (AuthContext)
    ├─ Save token to localStorage
    ├─ Set user state
    └─ Redirect to dashboard
```

### Authenticated Request Flow

```
Frontend (any page)
    ↓ API call via fetchWithAuth()
API Interceptor
    ├─ Get token from localStorage
    ├─ Inject: Authorization: Bearer <token>
    └─ Send request
    ↓
Backend (any @jwt_required route)
    ├─ Validate token signature
    ├─ Check expiration
    └─ Extract user_id from token
    ↓
Response
    ├─ 200 OK: Process normally
    ├─ 401 Unauthorized: Token invalid/expired
    └─ 422 Unprocessable: Token malformed
    ↓
Frontend
    ├─ On 401: Clear token & logout
    └─ Redirect to login
```

---

## Testing the Implementation

### Backend Testing

1. **Test Signup**:
```bash
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

2. **Test Login**:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

3. **Test Authenticated Request**:
```bash
curl -X GET http://localhost:5000/api/auth/me \
  -H "Authorization: Bearer <token_from_login>"
```

### Frontend Testing

1. Go to `/login` page
2. Fill signup form and submit
3. Verify redirect to dashboard
4. Verify user info displayed
5. Test logout function
6. Verify redirect to login

---

## Deployment Checklist

- [ ] Update `JWT_SECRET_KEY` in production
- [ ] Switch database to PostgreSQL
- [ ] Enable HTTPS
- [ ] Set `FLASK_ENV=production`
- [ ] Disable debug mode
- [ ] Configure CORS properly (specific domains)
- [ ] Add rate limiting to auth endpoints
- [ ] Implement password reset flow
- [ ] Add email verification for signup
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy for database

---

## Troubleshooting

### "Invalid JWT token" errors

1. Check `JWT_SECRET_KEY` is same on backend
2. Verify token isn't expired
3. Check Authorization header format: `Bearer <token>`

### Database not creating

1. Ensure `sqlite:///app.db` path is writable
2. Check SQLAlchemy is initialized: `db.init_app(app)`
3. Run `db.create_all()` in app context

### Tokens not persisting

1. Check browser localStorage not disabled
2. Verify CORS allows credentials
3. Check token saved on login

### CORS errors

1. Verify `CORS(app, ...)` is called
2. Check frontend URL is in `CORS_ORIGINS`
3. Ensure `Authorization` header is allowed

---

## Next Steps

Phase 1 provides the foundation for:
- **Phase 2**: Document upload and analysis with user ownership
- **Phase 4**: Speech analysis with user session tracking
- **Phase 5**: Practice history storage and progress tracking

All subsequent phases will use the User model to associate analysis results with authenticated users.
